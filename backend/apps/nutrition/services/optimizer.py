from apps.nutrition.models import NutritionAtom
from apps.nutrition.services.calculator import calculate_plan_totals, nutrients_for_atom


def _iter_ingredients(meal_plan):
    for day in meal_plan.get("days", []):
        for meal in day.get("meals", []):
            for recipe in meal.get("recipes", []):
                for ingredient in recipe.get("ingredients", []):
                    yield ingredient


def assign_nutrients(meal_plan):
    atom_ids = [item.get("atom_id") for item in _iter_ingredients(meal_plan) if item.get("atom_id")]
    atom_map = {atom.id: atom for atom in NutritionAtom.objects.filter(id__in=atom_ids)}
    for item in _iter_ingredients(meal_plan):
        atom = atom_map.get(item.get("atom_id"))
        if atom:
            item["nutrients"] = nutrients_for_atom(atom, item.get("grams"))
    return meal_plan


def optimize_grams(meal_plan, targets, constraints=None, max_iters=200):
    constraints = constraints or {}
    medical_caps = constraints.get("medical_caps") or {}
    calorie_target = float(targets.get("calorie_target_kcal") or 0)
    macros = targets.get("macro_targets_g") or {}
    protein_target = float(macros.get("protein_g") or 0)
    low_carb = bool(medical_caps.get("carbs_g"))

    assign_nutrients(meal_plan)
    for _ in range(max_iters):
        totals = calculate_plan_totals(meal_plan)
        kcal = totals["kcal"]
        protein = totals["protein_g"]
        kcal_ok = calorie_target and abs(kcal - calorie_target) <= calorie_target * 0.10
        protein_ok = protein_target and protein >= protein_target * 0.95
        if kcal_ok and protein_ok:
            break

        ingredients = list(_iter_ingredients(meal_plan))
        if protein < protein_target * 0.95:
            for item in ingredients:
                if item.get("role") == "protein":
                    item["grams"] = round(float(item.get("grams") or 0) * 1.10 + 5, 1)
        elif calorie_target and kcal > calorie_target * 1.10:
            for item in ingredients:
                if item.get("role") in {"fat", "carb"} and float(item.get("grams") or 0) > 20:
                    item["grams"] = round(float(item.get("grams")) * 0.92, 1)
        elif calorie_target and kcal < calorie_target * 0.90:
            preferred_roles = ["fat"] if low_carb else ["carb", "fat"]
            for item in ingredients:
                if item.get("role") in preferred_roles:
                    item["grams"] = round(float(item.get("grams") or 0) * 1.08 + 5, 1)

        assign_nutrients(meal_plan)

    totals = calculate_plan_totals(meal_plan)
    return meal_plan, totals

