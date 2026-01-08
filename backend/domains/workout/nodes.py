from __future__ import annotations

from typing import Any, Dict
from langchain_core.documents import Document

from backend.core.audit import append_event, append_iteration
from backend.domains.workout.state import WorkoutGraphState
from backend.domains.workout.services.profile import normalize_profile
from backend.domains.workout.services.constraints import build_constraints
from backend.domains.workout.services.retrieval import build_candidate_pack, candidate_pack_to_documents
from backend.domains.workout.services.evaluation import evaluate_plan
from backend.domains.workout.services.formatting import enrich_plan
from backend.domains.workout.services.planning import (
    generate_plan_with_llm,
    parse_intent_internal_goal_with_llm,
)

from backend.shared.llm import LLMClient

# Tạo 1 instance dùng lại (đỡ overhead)
_LLM = LLMClient()


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
    candidates = build_candidate_pack(state["profile"], state["constraints"])
    documents = candidate_pack_to_documents(candidates)

    print("[PIPELINE] build_candidate_pack_fn: workout.domains.workout.services.retrieval.build_candidate_pack")
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

def node_intent(state: WorkoutGraphState) -> Dict[str, Any]:
    """
    Intent → Internal Goal:
      - sinh internal_goal (structured)
      - lưu vào state["internal_goal"] và profile["internal_goal"]
      - nếu fail: warning + audit, không block pipeline (retrieval fallback taxonomy)
    """
    profile = state.get("profile") or {}
    if not profile:
        return {}

    # Skip nếu đã có internal_goal (tránh gọi lại)
    if state.get("internal_goal") or profile.get("internal_goal"):
        return {}

    internal_goal = parse_intent_internal_goal_with_llm(_LLM, profile)
    print("[INTENT] goal_style:", internal_goal.get("goal_style"))
    print("[INTENT] priority_muscles:", internal_goal.get("priority_muscles"))
    print("[INTENT] weekly_focus_by_day:", internal_goal.get("weekly_focus_by_day"))


    audit = state.get("audit", {"events": [], "iterations": []})
    warnings = list(state.get("warnings", []))

    # planning.py có thể trả dict chứa error_type khi validate fail
    if isinstance(internal_goal, dict) and internal_goal.get("error_type"):
        audit = append_event(
            audit,
            "intent_failed",
            {
                "message": internal_goal.get("message"),
                "errors": internal_goal.get("errors"),
            },
        )
        warnings.append(
            {
                "type": "intent_failed",
                "detail": internal_goal.get("errors") or internal_goal.get("message") or "unknown",
            }
        )

        p2 = dict(profile)
        p2["internal_goal"] = None
        return {"audit": audit, "warnings": warnings, "internal_goal": None, "profile": p2}

    # Success
    audit = append_event(
        audit,
        "intent_done",
        {
            "goal_style": internal_goal.get("goal_style") if isinstance(internal_goal, dict) else None,
            "priority_muscles": internal_goal.get("priority_muscles") if isinstance(internal_goal, dict) else None,
        },
    )

    p2 = dict(profile)
    p2["internal_goal"] = internal_goal
    return {"audit": audit, "internal_goal": internal_goal, "profile": p2}


def node_plan(state: WorkoutGraphState) -> Dict[str, Any]:
    iteration = int(state.get("iteration", 0))

    audit = append_iteration(state["audit"], iteration)

    print("[PIPELINE] candidates_len_before_llm:", len(state.get("candidates", [])))

    draft = generate_plan_with_llm(
        llm=_LLM,
        profile=state["profile"],
        constraints=state["constraints"],
        candidates=state["candidates"],
        documents=state.get("documents"),
        issues=(state["issues"] if iteration > 0 else None),
        prev_plan=(state["draft_plan"] if iteration > 0 else None),
    )

    audit = append_event(audit, "draft_done", {"iteration": iteration})
    return {"draft_plan": draft, "audit": audit}


def node_evaluate(state: WorkoutGraphState) -> Dict[str, Any]:
    draft = state["draft_plan"] or {}
    # Pass full candidates into evaluation so it can infer primary muscle by exercise_id
    candidates = state.get("candidates", []) or []
    iteration = int(state.get("iteration", 0))
    max_iter = int(state.get("max_iter", 2))

    eval_out = evaluate_plan(draft, candidates, state["profile"], state["constraints"])
    issues = eval_out.get("issues", []) or []
    warnings = eval_out.get("warnings", []) or []

    # Helpful debug logs
    try:
        print("[EVAL] issues_count:", len(issues))
        if issues:
            print("[EVAL] issue_types:", [i.get("type") for i in issues if isinstance(i, dict)])
        print("[EVAL] warnings_count:", len(warnings))
    except Exception:
        pass

    audit = append_event(state["audit"], "evaluate_done", {
        "iteration": iteration,
        "issues": len(issues),
        "warnings": len(warnings),
    })

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
    audit = append_event(state["audit"], "pipeline_end", {
        "issues": len(state.get("issues", [])),
        "warnings": len(state.get("warnings", []))
    })
    return {"final_plan": final_plan, "audit": audit}


