import math


PAL = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "very_active": 1.725,
    "athlete": 1.9,
}


def _to_float(value):
    if value in (None, ""):
        return None
    return float(value)


def calculate_metrics(data):
    sex = data.get("sex")
    age = _to_float(data.get("age"))
    height_cm = _to_float(data.get("height_cm"))
    weight_kg = _to_float(data.get("weight_kg"))
    waist_cm = _to_float(data.get("waist_cm"))
    neck_cm = _to_float(data.get("neck_cm"))
    hip_cm = _to_float(data.get("hip_cm"))
    activity_level = data.get("activity_level") or "moderate"

    notes = {}
    bmi = None
    bmr = None
    tdee = None
    whtr = None
    bodyfat = None
    bodyfat_method = None

    if height_cm and weight_kg:
        bmi = weight_kg / ((height_cm / 100) ** 2)
        whtr = waist_cm / height_cm if waist_cm else None
    else:
        notes["bmi"] = "height_cm and weight_kg are required."

    if sex in {"male", "female"} and age and height_cm and weight_kg:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + (5 if sex == "male" else -161)
        tdee = bmr * PAL.get(activity_level, PAL["moderate"])
    else:
        notes["bmr"] = "sex, age, height_cm, and weight_kg are required."

    if sex == "male" and waist_cm and neck_cm and height_cm and waist_cm > neck_cm:
        bodyfat = 495 / (1.0324 - 0.19077 * math.log10(waist_cm - neck_cm) + 0.15456 * math.log10(height_cm)) - 450
        bodyfat_method = "us_navy"
    elif sex == "female" and waist_cm and neck_cm and hip_cm and height_cm and waist_cm + hip_cm > neck_cm:
        bodyfat = 495 / (
            1.29579
            - 0.35004 * math.log10(waist_cm + hip_cm - neck_cm)
            + 0.22100 * math.log10(height_cm)
        ) - 450
        bodyfat_method = "us_navy"
    else:
        notes["bodyfat"] = "US Navy body fat requires valid waist, neck, height, and hip for female."

    return {
        "bmi": round(bmi, 2) if bmi is not None else None,
        "bmr_kcal": round(bmr) if bmr is not None else None,
        "tdee_kcal": round(tdee) if tdee is not None else None,
        "bodyfat_percent": round(bodyfat, 1) if bodyfat is not None else None,
        "bodyfat_method": bodyfat_method,
        "whtr": round(whtr, 2) if whtr is not None else None,
        "notes": notes,
    }

