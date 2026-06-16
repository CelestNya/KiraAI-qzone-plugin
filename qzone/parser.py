"""QZone 响应解析。"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .model import Post, Comment

logger = logging.getLogger(__name__)


class QzoneParser:

    # ── 说说列表解析 ──

    def parse_feeds(self, msglist: list[dict]) -> list[Post]:
        """解析 msglist 数组为 Post 列表。"""
        return [self._parse_post(m) for m in msglist if m]

    def parse_recent_feeds(self, data: Any) -> list[Post]:
        """解析好友圈 HTML feeds 数据为 Post 列表。"""
        posts = []
        if isinstance(data, dict):
            for item in data.get("msglist", []):
                posts.append(self._parse_post(item))
        return posts

    def _parse_post(self, item: dict) -> Post:
        return Post(
            uin=int(item.get("uin", 0) or 0),
            tid=str(item.get("tid", "") or ""),
            name=str(item.get("name", "") or ""),
            text=str(item.get("content", "") or ""),
            create_time=int(item.get("created_time", 0) or 0),
            images=self._extract_images(item),
            videos=self._extract_videos(item),
            comments=self._parse_comments(item.get("commentlist") or []),
        )

    def parse_comments(self, commentlist: list[dict]) -> list[Comment]:
        return self._parse_comments(commentlist)

    def _parse_comments(self, raw: list[dict]) -> list[Comment]:
        result = []
        for c in raw:
            if not c:
                continue
            main = Comment(
                uin=int(c.get("uin", 0) or 0),
                nickname=str(c.get("nickname", "") or ""),
                content=str(c.get("content", "") or ""),
                create_time=int(c.get("create_time", 0) or 0),
                tid=str(c.get("tid", "") or ""),
            )
            # list_3 = 楼中楼回复
            for sub in c.get("list_3") or []:
                if sub:
                    main.replies.append(Comment(
                        uin=int(sub.get("uin", 0) or 0),
                        nickname=str(sub.get("nickname", "") or ""),
                        content=str(sub.get("content", "") or ""),
                        create_time=int(sub.get("create_time", 0) or 0),
                        tid=str(sub.get("tid", "") or ""),
                    ))
            result.append(main)
        return result

    @staticmethod
    def _extract_images(item: dict) -> list[str]:
        urls = []
        for pic in item.get("pic", []):
            url = pic.get("url", "") or pic.get("pic", "") or ""
            if url:
                urls.append(url)
        return urls

    @staticmethod
    def _extract_videos(item: dict) -> list[dict]:
        return item.get("video", []) or []

    # ── 图片上传解析 ──

    @staticmethod
    def parse_upload(data: Any) -> tuple[str, str]:
        """解析图片上传结果，返回 (pic_bo, richval)。"""
        if isinstance(data, dict):
            # key 可能是 pic_bo 或 album
            pic_bo = str(data.get("pic_bo", data.get("album", "")))
            richval = str(data.get("richval", ""))
            return pic_bo, richval
        return "", ""
