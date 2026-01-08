from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    provider: str
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"
    temperature: float = 0.2
    max_retries: int = 2

    @staticmethod
    def from_env() -> "LLMConfig":
        return LLMConfig(
            provider=(os.getenv("LLM_PROVIDER") or "gemini").lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
            gemini_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL") or "gemini-1.5-flash",
            temperature=float(os.getenv("LLM_TEMPERATURE") or 0.2),
            max_retries=int(os.getenv("LLM_MAX_RETRIES") or 2),
        )


