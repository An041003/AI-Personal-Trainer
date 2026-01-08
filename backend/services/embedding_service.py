from __future__ import annotations

import os
import random
import re
import time
from typing import List, Optional

from openai import OpenAI
from openai import OpenAIError

DEFAULT_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
DEFAULT_DIM = int(os.getenv("OPENAI_EMBED_DIM", "1536"))

_CLIENT: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Thiếu OPENAI_API_KEY trong environment variables.")

    _CLIENT = OpenAI(api_key=api_key)
    return _CLIENT


def parse_retry_seconds(message: str) -> float:
    # Một số lỗi có thể chứa: "Please try again in 38.34s"
    m = re.search(r"(retry|try again) in\s+([0-9.]+)\s*s", message, re.IGNORECASE)
    if m:
        return float(m.group(2))

    # Hoặc: "retry_after: 38"
    m = re.search(r"retry[_-]?after[:=]\s*([0-9.]+)", message, re.IGNORECASE)
    if m:
        return float(m.group(1))

    return 30.0


def _extract_retry_after_seconds(err: Exception) -> Optional[float]:
    """
    Cố gắng lấy Retry-After từ exception của OpenAI SDK (nếu có).
    Tùy phiên bản SDK, error có thể có .response.headers hoặc thông tin tương tự.
    """
    resp = getattr(err, "response", None)
    headers = getattr(resp, "headers", None) if resp is not None else None
    if headers:
        # chuẩn: Retry-After (giây)
        ra = headers.get("retry-after")
        if ra:
            try:
                return float(ra)
            except Exception:
                pass

        # đôi khi có retry-after-ms
        ram = headers.get("retry-after-ms")
        if ram:
            try:
                return float(ram) / 1000.0
            except Exception:
                pass

    return None


def embed_texts(
    texts: List[str],
    task_type: str,  # giữ để tương thích; OpenAI embeddings không dùng
    model: str = DEFAULT_EMBED_MODEL,
    output_dim: int = DEFAULT_DIM,
    title: Optional[str] = None,  # giữ để tương thích; OpenAI embeddings không dùng
    max_retries: int = 10,
) -> List[List[float]]:
    if not texts:
        return []

    client = get_client()
    last_err: Exception | None = None

    for attempt in range(max_retries):
        try:
            # OpenAI embeddings: input có thể là list[str]
            # Với text-embedding-3-*, có thể truyền dimensions để giảm chiều nếu muốn.
            kwargs = {"model": model, "input": texts}
            if output_dim and model.startswith("text-embedding-3"):
                kwargs["dimensions"] = int(output_dim)

            res = client.embeddings.create(**kwargs)

            # res.data là list; mỗi item có .embedding
            return [list(item.embedding) for item in res.data]

        except OpenAIError as e:
            # Thường gặp rate-limit / quota -> chờ theo retry-after nếu có
            wait_s = _extract_retry_after_seconds(e)
            if wait_s is None:
                wait_s = parse_retry_seconds(str(e))

            # thêm chút đệm để tránh “đụng” rate limit ngay khi retry
            time.sleep(float(wait_s) + 1.0)
            last_err = e

        except Exception as e:
            last_err = e
            # backoff cho lỗi tạm thời khác
            sleep_s = min(16.0, (2 ** attempt) + random.random())
            time.sleep(sleep_s)

    raise last_err if last_err else RuntimeError("Embedding failed without exception detail.")


def embed_document(texts: List[str], output_dim: int = DEFAULT_DIM) -> List[List[float]]:
    return embed_texts(
        texts=texts,
        task_type="RETRIEVAL_DOCUMENT",
        output_dim=output_dim,
        title="Exercise",
    )


def embed_query(text: str, output_dim: int = DEFAULT_DIM) -> List[float]:
    vecs = embed_texts(
        texts=[text],
        task_type="RETRIEVAL_QUERY",
        output_dim=output_dim,
        title=None,
    )
    return vecs[0]
