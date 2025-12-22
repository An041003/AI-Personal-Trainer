from __future__ import annotations

import re
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class LLMConfig:
    provider: str
    gemini_api_key: Optional[str]
    gemini_model: str
    openai_api_key: Optional[str]
    openai_model: str
    temperature: float = 0.2

    @staticmethod
    def from_env() -> "LLMConfig":
        return LLMConfig(
            provider=(os.getenv("LLM_PROVIDER") or "gemini").lower(),
            gemini_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL") or "gemini-2.0-flash",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
        )


def _extract_json_block(text: str) -> str:
    """
    Cố gắng lấy ra object JSON đầu tiên trong text.
    """
    if not text:
        return ""

    # loại bỏ markdown fences nếu có
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*```$", "", t)

    # tìm từ '{' đầu tiên đến '}' cuối cùng
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        return t[start:end + 1]
    return t


def _try_parse_json(text: str) -> dict:
    """
    Thử parse JSON, nếu fail thì raise JSONDecodeError.
    """
    return json.loads(text)

def _log_prompt_stats(tag: str, prompt: str) -> None:
    try:
        prompt = prompt or ""
        chars = len(prompt)
        lines = prompt.count("\n") + 1
        approx_tokens = chars // 4  # ước lượng rất thô
        head = prompt[:300].replace("\n", "\\n")
        tail = prompt[-300:].replace("\n", "\\n")

        print(f"[LLM][{tag}] prompt_chars={chars} prompt_lines={lines} approx_tokens~={approx_tokens}")
        print(f"[LLM][{tag}] prompt_head={head}")
        print(f"[LLM][{tag}] prompt_tail={tail}")
    except Exception:
        print(f"[LLM][{tag}] prompt log failed")


class LLMClient:
    def __init__(self, cfg: Optional[LLMConfig] = None) -> None:
        self.cfg = cfg or LLMConfig.from_env()

    def generate_plan_json(self, prompt: str, response_schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.cfg.provider == "gemini":
            return self._gemini_generate_json(prompt, response_schema)
        if self.cfg.provider == "openai":
            return self._openai_generate_json(prompt)
        raise ValueError(f"Unsupported LLM_PROVIDER={self.cfg.provider}")

    def _gemini_generate_json(self, prompt: str, response_schema: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.cfg.gemini_api_key:
            raise RuntimeError("Missing GEMINI_API_KEY (or GOOGLE_API_KEY)")

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.cfg.gemini_api_key)

        cfg = types.GenerateContentConfig(
            temperature=self.cfg.temperature,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        if response_schema:
            cfg.response_schema = response_schema

        # ===== MAIN CALL =====
        _log_prompt_stats("GEMINI_MAIN_INPUT", prompt)

        resp = client.models.generate_content(
            model=self.cfg.gemini_model,
            contents=prompt,
            config=cfg,
        )

        # ===== DEBUG LOG (MAIN) =====
        try:
            cand0 = resp.candidates[0] if getattr(resp, "candidates", None) else None
            finish_reason = getattr(cand0, "finish_reason", None) if cand0 else None
            usage = getattr(resp, "usage_metadata", None)
            print("[GEMINI][MAIN] model:", self.cfg.gemini_model)
            print("[GEMINI][MAIN] finish_reason:", finish_reason)
            print("[GEMINI][MAIN] usage_metadata:", usage)
            print("[GEMINI][MAIN] text_len:", len(resp.text or ""))
        except Exception:
            print("[GEMINI][MAIN] debug log failed")
        # =============================

        text = (resp.text or "").strip()

        # 1) try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2) try extracting JSON block
        candidate = _extract_json_block(text)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # 3) one-shot repair: ask Gemini to output valid JSON only
        repair_prompt = (
            "Chỉ trả về JSON hợp lệ theo chuẩn JSON (tất cả key/string dùng dấu nháy kép). "
            "Không thêm chữ giải thích, không markdown.\n\n"
            "Nội dung cần chuyển thành JSON hợp lệ:\n"
            f"{candidate}"
        )

        # ===== REPAIR CALL =====
        _log_prompt_stats("GEMINI_REPAIR_INPUT", repair_prompt)


        resp2 = client.models.generate_content(
            model=self.cfg.gemini_model,
            contents=repair_prompt,
            config=cfg,
        )

        # ===== DEBUG LOG (REPAIR) =====
        try:
            cand0 = resp2.candidates[0] if getattr(resp2, "candidates", None) else None
            finish_reason = getattr(cand0, "finish_reason", None) if cand0 else None
            usage = getattr(resp2, "usage_metadata", None)
            print("[GEMINI][REPAIR] model:", self.cfg.gemini_model)
            print("[GEMINI][REPAIR] finish_reason:", finish_reason)
            print("[GEMINI][REPAIR] usage_metadata:", usage)
            print("[GEMINI][REPAIR] text_len:", len(resp2.text or ""))
        except Exception:
            print("[GEMINI][REPAIR] debug log failed")
        # ===============================

        text2 = _extract_json_block((resp2.text or "").strip())
        return json.loads(text2)

    def _openai_generate_json(self, prompt: str) -> Dict[str, Any]:
        if not self.cfg.openai_api_key:
            raise RuntimeError("Missing OPENAI_API_KEY")

        from openai import OpenAI

        client = OpenAI(api_key=self.cfg.openai_api_key)
        resp = client.responses.create(
            model=self.cfg.openai_model,
            instructions="Bạn là trợ lý lập lịch tập gym. Chỉ trả về JSON hợp lệ. Không markdown.",
            input=prompt,
        )
        text = (resp.output_text or "").strip()
        return json.loads(text)
