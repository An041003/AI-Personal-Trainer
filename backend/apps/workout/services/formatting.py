from apps.workout.models import Exercise


def enrich_plan(plan):
    ids = [
        item.get("exercise_id")
        for day in plan.get("days", [])
        for item in day.get("exercises", [])
        if item.get("exercise_id")
    ]
    exercise_map = {item.id: item for item in Exercise.objects.filter(id__in=ids)}

    for day in plan.get("days", []):
        for item in day.get("exercises", []):
            exercise = exercise_map.get(item.get("exercise_id"))
            if not exercise:
                continue
            item.update(
                {
                    "title": exercise.title,
                    "muscle_groups": exercise.muscle_groups,
                    "equipment": exercise.equipment,
                    "image_url": exercise.image_url,
                    "image_file": exercise.image_file,
                }
            )
    return plan

