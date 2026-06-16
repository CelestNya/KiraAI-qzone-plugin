"""数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ApiResponse:
    """统一 API 响应包装。"""
    ok: bool
    code: int
    message: str
    data: Any = None

    @classmethod
    def from_raw(cls, raw: dict, *, code_key: str = "code", msg_key: str = "message") -> "ApiResponse":
        code = raw.get(code_key, -1)
        msg = raw.get(msg_key, "")
        if isinstance(code, str):
            try:
                code = int(code)
            except (ValueError, TypeError):
                code = -1
        return cls(
            ok=(code == 0),
            code=code,
            message=msg or "",
            data=raw,
        )

    @classmethod
    def error(cls, message: str) -> "ApiResponse":
        return cls(ok=False, code=-1, message=message)


@dataclass
class Post:
    uin: int
    tid: str = ""
    name: str = ""
    text: str = ""
    create_time: int = 0
    images: list[str] = field(default_factory=list)
    videos: list[Any] = field(default_factory=list)
    comments: list["Comment"] = field(default_factory=list)


@dataclass
class Comment:
    uin: int
    nickname: str = ""
    content: str = ""
    create_time: int = 0
    tid: str = ""
    replies: list["Comment"] = field(default_factory=list)
