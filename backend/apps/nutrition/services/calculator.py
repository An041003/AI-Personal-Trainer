from decimal import Decimal


NUTRIENT_FIELDS = {
    "kcal": "kcal_per_100g",
    "protein_g": "protein_g_per_100g",
    "carbs_g": "carb_g_per_100g",
    "fat_g": "fat_g_per_100g",
    "fiber_g": "fiber_g_per_100g",
    "sodium_mg": "sodium_mg_per_100g",
}


def nutrients_for_atom(atom, grams):
    grams = Decimal(str(grams or 0))
    result = {}
    for output_key, model_field in NUTRIENT_FIELDS.items():
        value = Decimal(getattr(atom, model_field) or 0) * grams / Decimal("100")
        result[output_key] = round(float(value), 2)
    return result


def calculate_plan_totals(meal_plan):
    totals = {key: 0.0 for key in NUTRIENT_FIELDS}
    for day in meal_plan.get("days", []):
        day_totals = {key: 0.0 for key in NUTRIENT_FIELDS}
        for meal in day.get("meals", []):
            meal_totals = {key: 0.0 for key in NUTRIENT_FIELDS}
            for recipe in meal.get("recipes", []):
                recipe_totals = {key: 0.0 for key in NUTRIENT_FIELDS}
                for ingredient in recipe.get("ingredients", []):
                    nutrients = ingredient.get("nutrients") or {}
                    for key in NUTRIENT_FIELDS:
                        recipe_totals[key] += float(nutrients.get(key) or 0)
                recipe["totals"] = {key: round(value, 2) for key, value in recipe_totals.items()}
                for key in NUTRIENT_FIELDS:
                    meal_totals[key] += recipe_totals[key]
            meal["totals"] = {key: round(value, 2) for key, value in meal_totals.items()}
            for key in NUTRIENT_FIELDS:
                day_totals[key] += meal_totals[key]
        day["totals"] = {key: round(value, 2) for key, value in day_totals.items()}
        for key in NUTRIENT_FIELDS:
            totals[key] += day_totals[key]
    return {key: round(value, 2) for key, value in totals.items()}

