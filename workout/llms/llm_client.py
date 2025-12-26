from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


from workout.llms.schemas import WorkoutPlan


@dataclass
class LLMConfig:
    provider: str
    openai_api_key: Optional[str]
    openai_model: str
    temperature: float = 0.2
    max_retries: int = 2

    @staticmethod
    def from_env() -> "LLMConfig":
        return LLMConfig(
            provider=(os.getenv("LLM_PROVIDER") or "gemini").lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
            temperature=float(os.getenv("LLM_TEMPERATURE") or 0.2),
            max_retries=int(os.getenv("LLM_MAX_RETRIES") or 2),
        )


def _log_prompt_stats(tag: str, prompt: str) -> None:
    try:
        prompt = prompt or ""
        chars = len(prompt)
        lines = prompt.count("\n") + 1
        approx_tokens = chars // 4  # ước lượng thô
        head = prompt[:300].replace("\n", "\\n")
        tail = prompt[-300:].replace("\n", "\\n")

        print(f"[LLM][{tag}] prompt_chars={chars} prompt_lines={lines} approx_tokens~={approx_tokens}")
        print(f"[LLM][{tag}] prompt_head={head}")
        print(f"[LLM][{tag}] prompt_tail={tail}")
    except Exception:
        print(f"[LLM][{tag}] prompt log failed")


class LLMClient:
    """
    Phase 1 (LangChain):
    - Output được ép kiểu theo WorkoutPlan (Pydantic) thông qua LangChain structured output.
    - response_schema argument giữ lại để không phá chữ ký hàm cũ, nhưng không còn dùng.
    """

    def __init__(self, cfg: Optional[LLMConfig] = None) -> None:
        self.cfg = cfg or LLMConfig.from_env()

    def generate_plan_json(self, prompt: str, response_schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.cfg.provider == "gemini":
            return self._gemini_generate_structured(prompt)
        if self.cfg.provider == "openai":
            return self._openai_generate_structured(prompt)
        raise ValueError(f"Unsupported LLM_PROVIDER={self.cfg.provider}")

    def _gemini_generate_structured(self, prompt: str) -> Dict[str, Any]:
        if not self.cfg.gemini_api_key:
            raise RuntimeError("Missing GEMINI_API_KEY (or GOOGLE_API_KEY)")

        _log_prompt_stats("GEMINI_LANGCHAIN_INPUT", prompt)

        # Import nội bộ để tránh lỗi import nếu bạn chưa cài dependency provider khác
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=self.cfg.gemini_model,
            temperature=self.cfg.temperature,
            max_retries=self.cfg.max_retries,
            google_api_key=self.cfg.gemini_api_key,
        )

        # Ưu tiên dùng native json_schema (ổn định hơn cho structured output)
        try:
            structured = llm.with_structured_output(WorkoutPlan, method="json_schema")
        except TypeError:
            # fallback nếu version cũ không hỗ trợ tham số method
            structured = llm.with_structured_output(WorkoutPlan)

        result = structured.invoke(prompt)  # trả về WorkoutPlan (Pydantic)
        return result.model_dump()

    def _openai_generate_structured(self, prompt: str) -> Dict[str, Any]:
        if not self.cfg.openai_api_key:
            raise RuntimeError("Missing OPENAI_API_KEY")

        _log_prompt_stats("OPENAI_LANGCHAIN_INPUT", prompt)

        from langchain_openai import ChatOpenAI

        # Tương thích nhiều version: api_key vs openai_api_key
        try:
            llm = ChatOpenAI(
                model=self.cfg.openai_model,
                api_key=self.cfg.openai_api_key,
                temperature=self.cfg.temperature,
                max_retries=self.cfg.max_retries,
            )
        except TypeError:
            llm = ChatOpenAI(
                model=self.cfg.openai_model,
                openai_api_key=self.cfg.openai_api_key,
                temperature=self.cfg.temperature,
                max_retries=self.cfg.max_retries,
            )

        structured = llm.with_structured_output(WorkoutPlan)
        result = structured.invoke(prompt)

        if hasattr(result, "model_dump"):
            return result.model_dump()
        return dict(result)
