"""帖子结构化导出：树状评论 + 图片下载到本地路径。"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles
import aiohttp

from .api import QzoneAPI
from .model import Post, Comment

logger = logging.getLogger(__name__)


@dataclass
class ExportedComment:
    """树状评论（含楼中楼回复）"""
    uin: int
    nickname: str
    content: str
    create_time: int
    tid: str
    replies: list["ExportedComment"] = field(default_factory=list)

    @staticmethod
    def from_comment(c: Comment) -> "ExportedComment":
        return ExportedComment(
            uin=c.uin, nickname=c.nickname, content=c.content,
            create_time=c.create_time, tid=c.tid,
            replies=[ExportedComment.from_comment(r) for r in c.replies],
        )


@dataclass
class ExportedPost:
    """树状帖子"""
    tid: str
    uin: int
    author: str
    text: str
    create_time: int
    images: list[str] = field(default_factory=list)     # 本地路径
    videos: list[str] = field(default_factory=list)
    comments: list[ExportedComment] = field(default_factory=list)


class Exporter:
    """拉取帖子 + 下载图片 + 输出结构化的本地树。"""

    def __init__(self, api: QzoneAPI, export_dir: str | Path):
        self._api = api
        self._export_dir = Path(export_dir)
        self._http: Optional[aiohttp.ClientSession] = None

    async def close(self):
        if self._http:
            await self._http.close()

    async def _get_http(self) -> aiohttp.ClientSession:
        if self._http is None:
            self._http = aiohttp.ClientSession()
        return self._http

    async def export_feeds(
        self, target_uin: str, num: int = 10, download_images: bool = True,
    ) -> list[ExportedPost]:
        """拉取说说列表 → 逐条取详情 → 下载图片 → 返回结构化数据。"""
        # 1. 取列表
        resp = await self._api.get_feeds(target_uin, num=num, replynum=100)
        msglist = resp.data.get("msglist", [])
        posts = self._api._parser.parse_feeds(msglist)

        result = []
        for p in posts:
            ep = await self._export_one(p, download_images)
            result.append(ep)

        return result

    async def export_post(self, post: Post, download_images: bool = True) -> ExportedPost:
        return await self._export_one(post, download_images)

    async def _export_one(self, post: Post, dl: bool) -> ExportedPost:
        # 取详情（拉完整评论树）
        detail = await self._api.get_detail(post)
        full_posts = self._api._parser.parse_feeds([detail.data]) if detail.ok else []
        fp = full_posts[0] if full_posts else post

        post_dir = self._export_dir / str(post.uin) / post.tid

        # 下载图片
        local_images: list[str] = []
        if dl and fp.images:
            local_images = await self._download_images(post.tid, fp.images, post_dir)

        # 构建树
        return ExportedPost(
            tid=post.tid,
            uin=post.uin,
            author=fp.name,
            text=fp.text,
            create_time=fp.create_time,
            images=local_images,
            videos=fp.videos,
            comments=[ExportedComment.from_comment(c) for c in fp.comments],
        )

    async def _download_images(self, tid: str, urls: list[str], post_dir: Path) -> list[str]:
        img_dir = post_dir / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        http = await self._get_http()
        local = []
        for idx, url in enumerate(urls, 1):
            ext = _guess_ext(url)
            fname = f"{idx:02d}{ext}"
            path = img_dir / fname
            try:
                async with http.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    data = await resp.read()
                async with aiofiles.open(str(path), "wb") as f:
                    await f.write(data)
                local.append(str(path.resolve()))
                logger.debug(f"下载图片 {fname} OK")
            except Exception as e:
                logger.warning(f"下载图片失败 {url[:60]}: {e}")
                local.append(url)  # 下载失败保留 URL
        return local

    def save_json(self, posts: list[ExportedPost]) -> Path:
        """保存结构化数据为 JSON（图片路径为本地）。"""
        data = [_post_to_dict(p) for p in posts]
        path = self._export_dir / str(posts[0].uin) / "posts.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def _guess_ext(url: str) -> str:
    for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
        if ext in url.lower():
            return ext
    return ".jpg"


def _post_to_dict(p: ExportedPost) -> dict:
    """递归转 dict，时间戳转可读字符串。"""
    return {
        "tid": p.tid,
        "uin": p.uin,
        "author": p.author,
        "text": p.text,
        "create_time": datetime.fromtimestamp(p.create_time).isoformat() if p.create_time else "",
        "images": p.images,
        "videos": p.videos,
        "comments": [_comment_to_dict(c) for c in p.comments],
    }


def _comment_to_dict(c: ExportedComment) -> dict:
    return {
        "uin": c.uin,
        "nickname": c.nickname,
        "content": c.content,
        "create_time": datetime.fromtimestamp(c.create_time).isoformat() if c.create_time else "",
        "tid": c.tid,
        "replies": [_comment_to_dict(r) for r in c.replies],
    }
