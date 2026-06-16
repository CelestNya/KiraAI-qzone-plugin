"""Cookie 解析、g_tk 计算、会话上下文。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from http.cookies import SimpleCookie
from typing import Optional


@dataclass
class QzoneContext:
    uin: int
    skey: str
    p_skey: str

    @property
    def gtk2(self) -> str:
        """由 p_skey 计算 g_tk（QZone 接口签名用）。"""
        return str(_calc_gtk(self.p_skey))

    @property
    def cookies(self) -> dict[str, str]:
        """传给 aiohttp 的 cookies 参数。uin 必须带 o 前缀。"""
        return {"uin": f"o{self.uin}", "skey": self.skey, "p_skey": self.p_skey}

    @property
    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0.0.0 Safari/537.36"
            ),
            "referer": f"https://user.qzone.qq.com/{self.uin}",
            "origin": "https://user.qzone.qq.com",
        }


def _calc_gtk(p_skey: str) -> int:
    h = 5381
    for c in p_skey:
        h += (h << 5) + ord(c)
    return h & 0x7FFFFFFF


class QzoneSession:
    """从 cookie 字符串解析会话，线程安全（只读后不加锁）。"""

    def __init__(self, cookie_str: str):
        self._cookie_str = cookie_str
        self._ctx: Optional[QzoneContext] = None

    def get_ctx(self) -> QzoneContext:
        """懒解析并缓存。只读操作，无需锁。"""
        if self._ctx is not None:
            return self._ctx
        self._ctx = self._parse(self._cookie_str)
        return self._ctx

    @staticmethod
    def _parse(cookie_str: str) -> QzoneContext:
        raw = SimpleCookie()
        raw.load(cookie_str)
        uin = _get_cookie_value(raw, "uin") or _get_cookie_value(raw, "p_uin") or ""
        skey = _get_cookie_value(raw, "skey") or ""
        p_skey = _get_cookie_value(raw, "p_skey") or ""
        # QZone cookie 的 uin 带 o 前缀 (如 o2859445368)，存 int
        if not uin.startswith("o"):
            raise ValueError(f"Cookie uin 缺少 o 前缀: {uin}")
        uin_int = int(uin[1:])
        if not uin_int or not p_skey:
            raise ValueError(
                f"Cookie 缺少必要字段 (uin={uin_int} / p_skey)。原始: {cookie_str[:80]}..."
            )
        return QzoneContext(uin=uin_int, skey=skey, p_skey=p_skey)


def _get_cookie_value(raw: SimpleCookie, key: str) -> Optional[str]:
    morsel = raw.get(key)
    return morsel.value if morsel else None
