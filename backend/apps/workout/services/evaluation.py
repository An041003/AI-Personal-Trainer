from collections import Counter


def evaluate_workout_plan(plan, *, candidate_ids, internal_goal, max_exercises_per_day=6):
    issues = []
    warnings = []
    candidate_ids = set(candidate_ids)
    days = plan.get("days", [])
    expected_days = internal_goal.get("days_per_week") or len(internal_goal.get("training_days") or [])

    if expected_days and len(days) != int(expected_days):
        issues.append(f"Expected {expected_days} training days, got {len(days)}.")

    focus_muscles = set(internal_goal.get("focus_muscles") or [])
    seen_muscles = set()
    seen_ids = []

    for day in days:
        exercises = day.get("exercises") or []
        if not exercises:
            issues.append(f"{day.get('day', 'unknown')} has no exercises.")
        if len(exercises) > max_exercises_per_day:
            issues.append(f"{day.get('day', 'unknown')} exceeds max exercises per day.")
        if len(exercises) < 3:
            warnings.append(f"{day.get('day', 'unknown')} has low exercise count.")

        for item in exercises:
            exercise_id = item.get("exercise_id")
            seen_ids.append(exercise_id)
            if exercise_id not in candidate_ids:
                issues.append(f"Exercise id {exercise_id} is not in candidate IDs.")
            seen_muscles.update(item.get("muscle_groups") or [])

    repeated = [exercise_id for exercise_id, count in Counter(seen_ids).items() if exercise_id and count > 2]
    if repeated:
        warnings.append(f"Exercises repeated more than twice: {repeated}.")

    missing_focus = focus_muscles - seen_muscles
    if missing_focus:
        warnings.append(f"Focus muscles not clearly covered: {sorted(missing_focus)}.")

    return {"issues": issues, "warnings": warnings}

