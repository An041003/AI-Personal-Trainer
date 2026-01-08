from __future__ import annotations

import uuid
from typing import Any, Dict
from typing_extensions import TypedDict
from dataclasses import dataclass, field


class BaseGraphState(TypedDict, total=False):
    """Base state cho tất cả graphs"""
    request_id: str
    raw_input: Dict[str, Any]
    iteration: int
    max_iter: int
    issues: list
    warnings: list
    audit: Dict[str, Any]


@dataclass
class BaseResult:
    """Base result cho tất cả domains"""
    request_id: str
    issues: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    audit: Dict[str, Any] = field(default_factory=lambda: {"events": [], "iterations": []})


def generate_request_id() -> str:
    """Generate unique request ID"""
    return str(uuid.uuid4())


