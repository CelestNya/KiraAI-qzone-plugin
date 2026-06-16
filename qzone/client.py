"""aiohttp HTTP 客户端封装，连接池复用。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import aiohttp

from .session import QzoneSession

logger = logging.getLogger(__name__)

_RETRY_MAX = 2


class QzoneHttpClient:
    """带 cookie 签名的 HTTP 客户端。连接池复用，仅 cookie 过期时重建。"""

    def __init__(self, session: QzoneSession, timeout: int = 10):
        self._session = session
        self._timeout = timeout
        self._http: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()

    async def _get_http(self) -> aiohttp.ClientSession:
        if self._http is None or self._http.closed:
            async with self._lock:
                if self._http is None or self._http.closed:
                    self._http = aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=self._timeout),
                    )
        return self._http

    async def close(self):
        if self._http and not self._http.closed:
            await self._http.close()

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> dict:
        """发起请求，自动带 cookie header。过期时最多重试 2 次。"""
        ctx = self._session.get_ctx()
        req_headers = {"User-Agent": _UA}
        req_headers.update(ctx.cookies)
        if headers:
            req_headers.update(headers)

        http = await self._get_http()
        last_error: Optional[Exception] = None

        for attempt in range(1 + _RETRY_MAX):
            try:
                async with http.request(
                    method, url,
                    params=params,
                    data=data,
                    headers=req_headers,
                    timeout=aiohttp.ClientTimeout(total=timeout or self._timeout),
                ) as resp:
                    text = await resp.text()
                    if resp.status == 401 or resp.status == 403:
                        logger.warning(f"HTTP {resp.status}，可能 cookie 过期 (attempt {attempt+1})")
                        raise _LoginExpired(text)
                    return await _parse_json(text)

            except _LoginExpired:
                if attempt < _RETRY_MAX:
                    logger.info(f"请求失败，重试 {attempt+1}/{_RETRY_MAX}")
                    await asyncio.sleep(1)
                    continue
                raise
            except aiohttp.ClientError as e:
                last_error = e
                if attempt < _RETRY_MAX:
                    wait = 2 ** attempt
                    logger.warning(f"网络错误 {e}，{wait}s 后重试")
                    await asyncio.sleep(wait)
                    continue
                raise RuntimeError(f"请求失败 (重试{_RETRY_MAX}次): {last_error}") from last_error

        raise RuntimeError(f"请求失败 (重试{_RETRY_MAX}次): {last_error}")


class _LoginExpired(Exception):
    pass


async def _parse_json(text: str) -> dict:
    """解析 JSON 或 JSONP 响应。"""
    s = text.strip()
    # JSONP: callback({...})
    if s.startswith("_Callback(") or s.endswith("})"):
        start = s.find("(")
        end = s.rfind(")")
        if start != -1 and end != -1:
            s = s[start + 1:end]
    import json
    # 修复 JSON5 遗留逗号
    s = _strip_trailing_commas(s)
    return json.loads(s)


def _strip_trailing_commas(s: str) -> str:
    """去掉 JSON 对象/数组最后一个元素后的逗号（QZone 经常返回）。"""
    import re
    s = re.sub(r',\s*([}\]])', r'\1', s)
    return s


_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)
