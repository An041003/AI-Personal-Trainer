import json
import time
from contextvars import ContextVar
from copy import deepcopy

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openai import OpenAI


_token_usage_context = ContextVar("openai_token_usage_context", default=None)


def get_openai_client():
    if not settings.OPENAI_API_KEY:
        raise ImproperlyConfigured("OPENAI_API_KEY is not configured.")
    return OpenAI(api_key=settings.OPENAI_API_KEY, timeout=45)


def _loads_json(content):
    if isinstance(content, dict):
        return content
    if not content:
        return {}
    return json.loads(content)


def start_token_usage_tracking():
    return _token_usage_context.set(
        {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "calls": [],
        }
    )


def reset_token_usage_tracking(token):
    _token_usage_context.reset(token)


def get_token_usage():
    usage = _token_usage_context.get()
    if usage is None:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "calls": [],
        }
    return deepcopy(usage)


def _model_dump(value):
    if not value:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {}


def _record_token_usage(response, *, model, operation):
    tracker = _token_usage_context.get()
    if tracker is None:
        return

    usage = getattr(response, "usage", None)
    if not usage:
        return

    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", 0) or 0)
    if not total_tokens:
        total_tokens = prompt_tokens + completion_tokens

    call = {
        "operation": operation,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }
    details = {}
    prompt_details = _model_dump(getattr(usage, "prompt_tokens_details", None))
    completion_details = _model_dump(getattr(usage, "completion_tokens_details", None))
    if prompt_details:
        details["prompt_tokens_details"] = prompt_details
    if completion_details:
        details["completion_tokens_details"] = completion_details
    if details:
        call["details"] = details

    tracker["prompt_tokens"] += prompt_tokens
    tracker["completion_tokens"] += completion_tokens
    tracker["total_tokens"] += total_tokens
    tracker["calls"].append(call)


def generate_json(system_prompt, user_prompt, *, model=None, max_retries=1):
    client = get_openai_client()
    selected_model = model or settings.OPENAI_CHAT_MODEL
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            _record_token_usage(response, model=selected_model, operation="chat.completions")
            return _loads_json(response.choices[0].message.content)
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(0.8 * (attempt + 1))

    raise last_error


def generate_json_with_image(system_prompt, user_prompt, image_data_url, *, model=None, max_retries=1):
    client = get_openai_client()
    selected_model = model or settings.OPENAI_CHAT_MODEL
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "image_url", "image_url": {"url": image_data_url}},
                        ],
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            _record_token_usage(response, model=selected_model, operation="chat.completions.vision")
            return _loads_json(response.choices[0].message.content)
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(0.8 * (attempt + 1))

    raise last_error


def embed_texts(texts, *, model=None, max_retries=1):
    if not texts:
        return []
    client = get_openai_client()
    selected_model = model or settings.OPENAI_EMBED_MODEL
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = client.embeddings.create(model=selected_model, input=texts)
            _record_token_usage(response, model=selected_model, operation="embeddings")
            return [item.embedding for item in response.data]
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(0.8 * (attempt + 1))

    raise last_error
