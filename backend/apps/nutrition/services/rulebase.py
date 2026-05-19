from apps.common.utils import normalize_text


def _as_float(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _medical_flags(conditions):
    normalized = " ".join(normalize_text(item) for item in conditions or [])
    return {
        "low_sodium": any(token in normalized for token in ["hypertension", "high blood pressure", "cao huyet ap"]),
        "low_sugar": any(token in normalized for token in ["diabetes", "tieu duong", "dai thao duong"]),
        "carb_control": any(token in normalized for token in ["diabetes", "tieu duong", "low carb"]),
        "low_purine": any(token in normalized for token in ["gout", "acid uric"]),
        "low_sat_fat": any(token in normalized for token in ["cholesterol", "triglyceride", "mo mau"]),
        "renal_caution": any(token in normalized for token in ["kidney", "renal", "ckd", "than", "suy than"]),
    }


def _diet_rules(dietary_style):
    hard_bans = []
    soft_avoid = []
    if dietary_style == "vegetarian":
        hard_bans += ["beef", "pork", "chicken", "fish", "shrimp", "seafood"]
    elif dietary_style == "vegan":
        hard_bans += ["beef", "pork", "chicken", "fish", "shrimp", "seafood", "egg", "milk", "yogurt", "cheese", "whey"]
    elif dietary_style == "halal":
        hard_bans += ["pork"]
    elif dietary_style == "keto":
        soft_avoid += ["rice", "oats", "bread", "noodle", "sugar"]
    elif dietary_style == "low_carb":
        soft_avoid += ["sugar", "sweet drink", "white bread"]
    return hard_bans, soft_avoid


def build_rulebase(payload):
    metrics = payload.get("metrics") or {}
    profile = payload.get("profile") or {}
    goal = payload.get("goal") or {}
    preferences = payload.get("preferences") or {}
    medical = payload.get("medical") or {}
    restriction_levels = payload.get("restriction_levels") or {}

    goal_type = goal.get("goal_type") or profile.get("goal_type") or "recomp"
    goal_mode = goal.get("goal_mode") or "standard"
    tdee = _as_float(metrics.get("tdee_kcal"), 2200)
    bmr = _as_float(metrics.get("bmr_kcal"), tdee * 0.7)
    weight_kg = _as_float(profile.get("weight_kg") or metrics.get("weight_kg"), 70)
    bmi = _as_float(metrics.get("bmi"), 0)

    if goal_type == "maintain":
        calorie_target = tdee
    elif goal_type == "cut":
        calorie_target = tdee * (0.80 if goal_mode == "aggressive" else 0.85)
        calorie_target = max(calorie_target, bmr * 1.05)
    elif goal_type == "bulk":
        calorie_target = tdee * 1.10
    elif goal_type == "recomp":
        calorie_target = tdee * 0.95
    else:
        calorie_target = tdee

    conditions = list(preferences.get("medical_conditions") or []) + list(medical.get("conditions") or [])
    flags = _medical_flags(conditions)
    dietary_style = preferences.get("dietary_style") or "none"

    protein_factor = 1.8 if goal_type in {"cut", "recomp"} else 1.6
    if goal_type == "bulk":
        protein_factor = 1.7
    if flags["renal_caution"]:
        protein_factor = min(protein_factor, 1.2)

    protein_level = int(restriction_levels.get("protein_level") or 0)
    carbs_level = int(restriction_levels.get("carbs_level") or 0)
    fat_level = int(restriction_levels.get("fat_level") or 0)
    protein_factor = max(1.0, protein_factor + protein_level * 0.15)

    protein_g = weight_kg * protein_factor
    fat_g = max(weight_kg * 0.6, calorie_target * (0.25 + fat_level * 0.03) / 9)
    remaining_kcal = max(calorie_target - protein_g * 4 - fat_g * 9, calorie_target * 0.25)
    carbs_g = remaining_kcal / 4
    if flags["carb_control"] or dietary_style in {"low_carb", "keto"} or carbs_level < 0:
        carbs_g *= 0.75 if dietary_style != "keto" else 0.35
        fat_g = max(fat_g, (calorie_target - protein_g * 4 - carbs_g * 4) / 9)

    hard_bans, diet_soft_avoid = _diet_rules(dietary_style)
    allergies = preferences.get("allergies") or []
    avoid_ingredients = preferences.get("avoid_ingredients") or []
    hard_bans += allergies + avoid_ingredients

    soft_avoid = list(preferences.get("disliked_foods") or []) + diet_soft_avoid
    soft_prefer = list(preferences.get("favorite_foods") or [])
    medical_caps = {}
    rule_notes = []

    if flags["low_sodium"]:
        soft_avoid += ["processed food", "instant noodle", "sausage", "high salt sauce"]
        medical_caps["sodium_mg"] = 1800
    if flags["low_sugar"]:
        soft_avoid += ["soda", "candy", "sweet drink", "sugar"]
    if flags["low_purine"]:
        soft_avoid += ["organ meat", "red meat", "high purine seafood"]
    if flags["low_sat_fat"]:
        soft_avoid += ["fried food", "butter", "animal fat"]
    if flags["renal_caution"]:
        rule_notes.append("Renal caution present: protein target is capped and professional guidance is recommended.")
    if goal_type == "cut" and (bmi and bmi < 19):
        rule_notes.append("BMI is low; aggressive cutting is not recommended.")

    slots = [
        {"slot": "breakfast", "kcal_ratio": 0.25, "protein_floor_g": 25},
        {"slot": "lunch", "kcal_ratio": 0.35, "protein_floor_g": 40},
        {"slot": "dinner", "kcal_ratio": 0.30, "protein_floor_g": 35},
        {"slot": "snack", "kcal_ratio": 0.10, "protein_floor_g": 15},
    ]

    return {
        "derived_targets": {
            "calorie_target_kcal": round(calorie_target),
            "macro_targets_g": {
                "protein_g": round(protein_g),
                "carbs_g": round(carbs_g),
                "fat_g": round(fat_g),
                "fiber_g": 25,
            },
            "meal_structure": {"meals_per_day": 4, "slots": slots},
        },
        "constraints": {
            "hard_bans": hard_bans,
            "soft_avoid": soft_avoid,
            "soft_prefer": soft_prefer,
            "medical_caps": medical_caps,
        },
        "medical_flags": flags,
        "rule_notes": rule_notes,
    }

