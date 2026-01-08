from __future__ import annotations

import time
from typing import Any, Dict, Tuple

# In-memory TTL cache đơn giản, dùng chung nội bộ process
_CACHE: Dict[str, Dict[Any, Tuple[float, Any]]] = {}


def cache_get(cache_name: str, key: Any) -> Any:
    """Lấy giá trị từ cache; trả None nếu hết hạn hoặc không có."""
    bucket = _CACHE.get(cache_name)
    if not bucket:
        return None

    item = bucket.get(key)
    if not item:
        return None

    expires_at, value = item
    if expires_at < time.time():
        # Hết hạn: xóa bỏ để tránh phình bộ nhớ
        bucket.pop(key, None)
        return None

    return value


def cache_set(cache_name: str, key: Any, value: Any, ttl_seconds: int = 600) -> None:
    """Ghi giá trị vào cache với TTL (mặc định 10 phút)."""
    bucket = _CACHE.setdefault(cache_name, {})
    bucket[key] = (time.time() + ttl_seconds, value)

