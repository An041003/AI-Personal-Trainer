from __future__ import annotations

from typing import Any, Dict, Optional, Type

from pydantic import BaseModel

from backend.shared.llm.config import LLMConfig
from backend.domains.workout.schemas import WorkoutPlan


def _log_prompt_stats(tag: str, prompt: str) -> None:
    try:
        prompt = prompt or ""
        chars = len(prompt)
        lines = prompt.count("\n") + 1
        approx_tokens = chars // 4  # ước lượng thô
        head = prompt[:300].replace("\n", "\\n")
        print(f"[LLM][{tag}] prompt_chars={chars} prompt_lines={lines} approx_tokens~={approx_tokens}")
        print(f"[LLM][{tag}] prompt_head={head}")
    except Exception:
        print(f"[LLM][{tag}] prompt log failed")


class LLMClient:
    """
    Generic LLM client cho mọi domain.
    Hỗ trợ structured output theo schema Pydantic bất kỳ.
    """

    def __init__(self, cfg: Optional[LLMConfig] = None) -> None:
        self.cfg = cfg or LLMConfig.from_env()

    # -----------------------------
    # Backward-compatible entrypoint
    # -----------------------------
    def generate_plan_json(self, prompt: str, response_schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # response_schema giữ lại để tương thích chữ ký cũ, hiện không dùng
        return self.generate_structured(prompt, WorkoutPlan)

    # -----------------------------
    # New generic entrypoint
    # -----------------------------
    def generate_structured(self, prompt: str, schema_model: Type[BaseModel]) -> Dict[str, Any]:
        """
        Generate structured JSON theo schema_model (Pydantic BaseModel).
        Return: dict (model_dump) để pipeline dùng thống nhất.
        """
        if self.cfg.provider == "gemini":
            return self._gemini_generate_structured(prompt, schema_model)
        if self.cfg.provider == "openai":
            return self._openai_generate_structured(prompt, schema_model)
        raise ValueError(f"Unsupported LLM_PROVIDER={self.cfg.provider}")

    # -----------------------------
    # Providers
    # -----------------------------
    def _gemini_generate_structured(self, prompt: str, schema_model: Type[BaseModel]) -> Dict[str, Any]:
        if not self.cfg.gemini_api_key:
            raise RuntimeError("Missing GEMINI_API_KEY (or GOOGLE_API_KEY)")

        _log_prompt_stats("GEMINI_LANGCHAIN_INPUT", prompt)

        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=self.cfg.gemini_model,
            temperature=self.cfg.temperature,
            max_retries=self.cfg.max_retries,
            google_api_key=self.cfg.gemini_api_key,
        )

        # Ưu tiên json_schema nếu version hỗ trợ để structured ổn định hơn
        try:
            structured = llm.with_structured_output(schema_model, method="json_schema")
        except TypeError:
            structured = llm.with_structured_output(schema_model)

        result = structured.invoke(prompt)

        # LangChain thường trả về Pydantic model
        if hasattr(result, "model_dump"):
            return result.model_dump()
        # Fallback nếu trả dict
        return dict(result)

    def _openai_generate_structured(self, prompt: str, schema_model: Type[BaseModel]) -> Dict[str, Any]:
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

        # Một số version có thể hỗ trợ method, nhưng OpenAI thường ổn với mặc định
        try:
            structured = llm.with_structured_output(schema_model, method="json_schema")
        except TypeError:
            structured = llm.with_structured_output(schema_model)

        result = structured.invoke(prompt)

        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json")
        return dict(result)
