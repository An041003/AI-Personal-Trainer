import json

from apps.common.openai_client import generate_json
from apps.common.prompt import WORKOUT_INTENT_RULES, WORKOUT_INTENT_SYSTEM_PROMPT
from apps.common.utils import normalize_text
from apps.workout.contracts import MUSCLE_TAXONOMY


def _mentions_cardio(goal_text):
    text = normalize_text(goal_text)
    return any(token in text for token in ["cardio", "tim mach", "suc ben", "endurance", "hiit", "running", "run", "chay"])


def _clean_focus_muscles(values, goal_text=""):
    focus = []
    if isinstance(values, str):
        values = [values]
    for item in values or []:
        muscle = normalize_text(item).replace("-", "_")
        if muscle in MUSCLE_TAXONOMY and muscle not in focus:
            focus.append(muscle)
    if "cardio" in focus and not _mentions_cardio(goal_text):
        focus.remove("cardio")
    return focus or ["full_body"]


def _heuristic_intent(data):
    goal_text = normalize_text(data.get("goal_text"))
    focus = []
    keyword_map = {
        "shoulder": "shoulders",
        "vai": "shoulders",
        "abs": "core",
        "core": "core",
        "bung": "core",
        "chest": "chest",
        "nguc": "chest",
        "back": "back",
        "lung": "back",
        "xo lung": "back",
        "lat": "back",
        "biceps": "biceps",
        "tay truoc": "biceps",
        "triceps": "triceps",
        "tay sau": "triceps",
        "forearm": "forearms",
        "canh tay": "forearms",
        "leg": "quadriceps",
        "chan": "quadriceps",
        "quad": "quadriceps",
        "dui truoc": "quadriceps",
        "hamstring": "hamstrings",
        "dui sau": "hamstrings",
        "glute": "glutes",
        "mong": "glutes",
        "calf": "calves",
        "bap chan": "calves",
        "cardio": "cardio",
        "tim mach": "cardio",
        "toan than": "full_body",
        "full body": "full_body",
    }
    for keyword, muscle in keyword_map.items():
        if keyword in goal_text and muscle not in focus:
            focus.append(muscle)

    return {"focus_muscles": _clean_focus_muscles(focus, data.get("goal_text"))}


def analyze_workout_intent(data):
    prompt = {
        "goal_text": data.get("goal_text") or "",
        "muscle_taxonomy": MUSCLE_TAXONOMY,
        "rules": WORKOUT_INTENT_RULES,
    }
    try:
        result = generate_json(WORKOUT_INTENT_SYSTEM_PROMPT, json.dumps(prompt, ensure_ascii=True))
    except Exception:
        return _heuristic_intent(data)

    return {"focus_muscles": _clean_focus_muscles(result.get("focus_muscles"), data.get("goal_text"))}
