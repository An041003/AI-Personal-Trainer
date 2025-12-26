from __future__ import annotations

from typing import Any, Dict, Set

from langgraph.graph import START, END, StateGraph

from workout.langgraph.state import WorkoutGraphState, init_graph_state, append_event, append_iteration

from workout.orchestration.state import SharedState
from workout.services.profile_normalizer import normalize_profile
from workout.services.constraints_engine import build_constraints
from workout.services.retrieval_service import build_candidate_pack
from workout.services.evaluator_service import evaluate_plan
from workout.services.formatter_service import enrich_plan
from workout.llms.llm_client import LLMClient
from workout.agents.workout_planning_agent import generate_plan_with_llm
from workout.langchain.retrievers.exercise_retriever import ExerciseRetriever



# Tạo 1 instance dùng lại (đỡ overhead)
_LLM = LLMClient()

_RETRIEVER = ExerciseRetriever(top_k=80)


def node_profile(state: WorkoutGraphState) -> Dict[str, Any]:
    raw_input = state["raw_input"]
    profile = normalize_profile(raw_input)
    audit = append_event(state["audit"], "profile_done", {"profile": profile})
    return {"profile": profile, "audit": audit}


def node_constraints(state: WorkoutGraphState) -> Dict[str, Any]:
    constraints = build_constraints(state["profile"])
    max_iter = int(constraints.get("max_repair_iterations", 2))
    audit = append_event(state["audit"], "constraints_done", {"constraints": constraints})
    return {"constraints": constraints, "max_iter": max_iter, "audit": audit}


def node_retrieval(state: WorkoutGraphState) -> Dict[str, Any]:
    documents = _RETRIEVER.invoke(state["profile"], state["constraints"])

    # Đồng thời giữ candidates list để enrich_plan dùng y như cũ
    # candidates được lấy ngược lại từ documents.metadata để tránh gọi DB lại
    candidates = []
    for d in documents:
        m = dict(d.metadata)
        # chuẩn hoá key về dạng bạn đang dùng
        candidates.append({
            "id": m.get("id"),
            "title": m.get("title"),
            "muscle_groups": m.get("muscle_groups", []),
            "equipment": m.get("equipment", []),
            "level": m.get("level", ""),
        })

    print("[PIPELINE] build_candidate_pack_fn: workout.langchain.retrievers ExerciseRetriever.invoke")
    print("[PIPELINE] candidate_count:", len(candidates))
    print("[PIPELINE] candidate_sample_ids:", [c["id"] for c in candidates[:10]])

    candidate_ids = {c["id"] for c in candidates if c.get("id") is not None}
    audit = append_event(state["audit"], "retrieval_done", {"candidate_count": len(candidates)})

    return {
        "documents": documents,
        "candidates": candidates,
        "candidate_ids": candidate_ids,
        "audit": audit,
    }



def node_plan(state: WorkoutGraphState) -> Dict[str, Any]:
    iteration = int(state.get("iteration", 0))

    audit = append_iteration(state["audit"], iteration)

    print("[PIPELINE] candidates_len_before_llm:", len(state.get("candidates", [])))

    draft = generate_plan_with_llm(
        llm=_LLM,
        profile=state["profile"],
        constraints=state["constraints"],
        candidates=state["candidates"],
        documents=state.get("documents"),  # <-- Phase 3: thêm dòng này
        issues=(state["issues"] if iteration > 0 else None),
        prev_plan=(state["draft_plan"] if iteration > 0 else None),
    )

    audit = append_event(audit, "draft_done", {"iteration": iteration})
    return {"draft_plan": draft, "audit": audit}



def node_evaluate(state: WorkoutGraphState) -> Dict[str, Any]:
    draft = state["draft_plan"] or {}
    candidate_ids = state["candidate_ids"]
    iteration = int(state.get("iteration", 0))
    max_iter = int(state.get("max_iter", 2))

    eval_out = evaluate_plan(draft, candidate_ids, state["profile"], state["constraints"])
    issues = eval_out.get("issues", [])
    warnings = eval_out.get("warnings", [])

    audit = append_event(state["audit"], "evaluate_done", {"iteration": iteration, "issues": len(issues), "warnings": len(warnings)})

    # Nếu còn issues và chưa tới lần cuối, tăng iteration để plan node chạy vòng sửa tiếp
    next_iteration = iteration
    if issues and iteration < max_iter:
        next_iteration = iteration + 1

    return {"issues": issues, "warnings": warnings, "iteration": next_iteration, "audit": audit}


def route_after_eval(state: WorkoutGraphState) -> str:
    """
    Quy tắc dừng đúng như orchestrator cũ:
    - Nếu không còn issues: kết thúc và enrich
    - Nếu còn issues nhưng đã ở attempt cuối (iteration == max_iter): enrich (stop)
    - Nếu còn issues và vẫn còn lượt sửa: quay lại plan
    """
    issues = state.get("issues", [])
    iteration = int(state.get("iteration", 0))
    max_iter = int(state.get("max_iter", 2))

    if not issues:
        return "enrich"
    if iteration >= max_iter:
        return "enrich"
    return "plan"


def node_enrich(state: WorkoutGraphState) -> Dict[str, Any]:
    final_plan = enrich_plan(state["draft_plan"] or {}, state["candidates"])
    audit = append_event(state["audit"], "pipeline_end", {"issues": len(state.get("issues", [])), "warnings": len(state.get("warnings", []))})
    return {"final_plan": final_plan, "audit": audit}


def build_workout_graph():
    builder = StateGraph(WorkoutGraphState)

    builder.add_node("profile", node_profile)
    builder.add_node("constraints", node_constraints)
    builder.add_node("retrieval", node_retrieval)
    builder.add_node("plan", node_plan)
    builder.add_node("evaluate", node_evaluate)
    builder.add_node("enrich", node_enrich)

    builder.add_edge(START, "profile")
    builder.add_edge("profile", "constraints")
    builder.add_edge("constraints", "retrieval")
    builder.add_edge("retrieval", "plan")
    builder.add_edge("plan", "evaluate")

    builder.add_conditional_edges(
        "evaluate",
        route_after_eval,
        {
            "plan": "plan",
            "enrich": "enrich",
        },
    )
    builder.add_edge("enrich", END)

    return builder.compile()


WORKOUT_GRAPH = build_workout_graph()


def run_workout_planning_graph(raw_input: Dict[str, Any]) -> SharedState:
    init_state = init_graph_state(raw_input)
    init_state["audit"] = append_event(init_state["audit"], "pipeline_start", {"raw_input": raw_input})

    out = WORKOUT_GRAPH.invoke(init_state)

    # Map về SharedState để giữ nguyên API bên ngoài
    s = SharedState(request_id=out["request_id"])
    s.profile = out.get("profile", {})
    s.constraints = out.get("constraints", {})
    s.candidates = out.get("candidates", [])
    s.draft_plan = out.get("draft_plan")
    s.final_plan = out.get("final_plan")
    s.issues = out.get("issues", [])
    s.warnings = out.get("warnings", [])
    s.audit = out.get("audit", {"events": [], "iterations": []})
    return s
