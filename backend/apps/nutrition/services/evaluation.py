from apps.common.utils import normalize_text


def _ingredient_names(meal_plan):
    names = []
    for day in meal_plan.get("days", []):
        for meal in day.get("meals", []):
            for recipe in meal.get("recipes", []):
                for ingredient in recipe.get("ingredients", []):
                    names.append(
                        normalize_text(
                            " ".join(
                                [
                                    str(ingredient.get("name") or ""),
                                    str(ingredient.get("ingredient_name") or ""),
                                    str(ingredient.get("canonical_name") or ""),
                                ]
                            )
                        )
                    )
    return " ".join(names)


def evaluate_meal_plan(meal_plan, totals, targets, constraints, warnings=None):
    warnings = list(warnings or [])
    issues = []
    haystack = _ingredient_names(meal_plan)
    for ban in constraints.get("hard_bans") or []:
        if normalize_text(ban) and normalize_text(ban) in haystack:
            issues.append(f"Hard ban appears in meal plan: {ban}")

    calorie_target = float(targets.get("calorie_target_kcal") or 0)
    protein_target = float((targets.get("macro_targets_g") or {}).get("protein_g") or 0)
    if calorie_target and abs(float(totals.get("kcal") or 0) - calorie_target) > calorie_target * 0.15:
        issues.append("Calories are more than 15% away from target.")
    if protein_target and float(totals.get("protein_g") or 0) < protein_target * 0.90:
        issues.append("Protein is below 90% of target after optimization.")

    caps = constraints.get("medical_caps") or {}
    if caps.get("sodium_mg") and float(totals.get("sodium_mg") or 0) > float(caps["sodium_mg"]):
        warnings.append("Sodium is above the medical cap.")
    fiber_target = float((targets.get("macro_targets_g") or {}).get("fiber_g") or 0)
    if fiber_target and float(totals.get("fiber_g") or 0) < fiber_target * 0.75:
        warnings.append("Fiber is low.")

    return {"issues": issues, "warnings": warnings}
