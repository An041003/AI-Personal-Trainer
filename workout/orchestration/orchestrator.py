from __future__ import annotations

import uuid
from typing import Any, Dict, Set

from workout.orchestration.state import SharedState
from workout.services.profile_normalizer import normalize_profile
from workout.services.constraints_engine import build_constraints
from workout.services.retrieval_service import build_candidate_pack
from workout.services.evaluator_service import evaluate_plan
from workout.services.formatter_service import enrich_plan
from workout.llms.llm_client import LLMClient
from workout.agents.workout_planning_agent import generate_plan_with_llm


def run_workout_planning_pipeline(raw_input: Dict[str, Any]) -> SharedState:
    state = SharedState(request_id=str(uuid.uuid4()))
    state.log("pipeline_start", {"raw_input": raw_input})

    state.profile = normalize_profile(raw_input)
    state.log("profile_done", {"profile": state.profile})

    state.constraints = build_constraints(state.profile)
    state.log("constraints_done", {"constraints": state.constraints})

    # Build candidate pack (Retrieval)
    state.candidates = build_candidate_pack(state.profile, state.constraints)

    # Log candidate stats (đặt đúng chỗ, sau khi build)
    print("[PIPELINE] build_candidate_pack_fn:", build_candidate_pack.__module__, build_candidate_pack.__name__)
    print("[PIPELINE] candidate_count:", len(state.candidates))
    print("[PIPELINE] candidate_sample_ids:", [c["id"] for c in state.candidates[:10]])

    candidate_ids: Set[int] = {c["id"] for c in state.candidates}
    state.log("retrieval_done", {"candidate_count": len(state.candidates)})

    llm = LLMClient()

    max_iter = int(state.constraints.get("max_repair_iterations", 2))
    prev = None

    for i in range(max_iter + 1):
        state.audit["iterations"].append({"iteration": i})

        # Log ngay trước khi gọi LLM để chắc candidates không bị rỗng
        print("[PIPELINE] candidates_len_before_llm:", len(state.candidates))

        draft = generate_plan_with_llm(
            llm=llm,
            profile=state.profile,
            constraints=state.constraints,
            candidates=state.candidates,
            issues=(state.issues if i > 0 else None),
            prev_plan=prev,
        )
        state.draft_plan = draft
        prev = draft

        eval_out = evaluate_plan(draft, candidate_ids, state.profile, state.constraints)
        state.issues = eval_out["issues"]
        state.warnings = eval_out["warnings"]
        state.log("evaluate_done", {"iteration": i, "issues": len(state.issues), "warnings": len(state.warnings)})

        if not state.issues:
            break

    state.final_plan = enrich_plan(state.draft_plan or {}, state.candidates)
    state.log("pipeline_end", {"issues": len(state.issues), "warnings": len(state.warnings)})

    return state
