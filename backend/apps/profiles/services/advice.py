import json

from django.core.exceptions import ImproperlyConfigured

from apps.common.openai_client import generate_json
from apps.common.prompt import PROFILE_ADVICE_SYSTEM_PROMPT


def profile_advice(profile, metrics, preferences, medical):
    payload = {
        "profile": profile,
        "metrics": metrics,
        "preferences": preferences,
        "medical": medical,
    }
    user_prompt = json.dumps(payload, ensure_ascii=True)
    try:
        return generate_json(PROFILE_ADVICE_SYSTEM_PROMPT, user_prompt)
    except ImproperlyConfigured:
        return {
            "summary": "OpenAI is not configured yet. Fill OPENAI_API_KEY in backend/.env to enable AI advice.",
            "risks": [],
            "recommendations": [
                "Keep profile metrics complete before generating targets.",
                "Use medical conditions and allergies as hard constraints in nutrition planning.",
            ],
            "suggested_goal": {"goal_type": profile.get("goal_type") or "recomp", "reason": "Fallback only."},
            "safety_note": "This is not medical advice.",
        }
