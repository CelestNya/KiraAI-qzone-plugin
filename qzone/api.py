"""QQ 空间 HTTP API 封装。"""

from __future__ import annotations

import base64
import logging
import time
from typing import Any, Optional

from .client import QzoneHttpClient
from .model import ApiResponse, Post, Comment
from .parser import QzoneParser
from .session import QzoneSession

logger = logging.getLogger(__name__)

BASE = "https://user.qzone.qq.com"
PROXY = "https://user.qzone.qq.com/proxy/domain"
H5 = "https://h5.qzone.qq.com/proxy/domain"


class QzoneAPI(QzoneHttpClient):
    """QQ 空间 API。9 个端点 + 图片上传。"""

    # ── 端点 URL ──
    URL_PUBLISH = f"{PROXY}/taotao.qzone.qq.com/cgi-bin/emotion_cgi_publish_v6"
    URL_LIKE = f"{PROXY}/w.qzone.qq.com/cgi-bin/likes/internal_dolike_app"
    URL_COMMENT = f"{PROXY}/taotao.qzone.qq.com/cgi-bin/emotion_cgi_re_feeds"
    URL_REPLY = f"{H5}/taotao.qzone.qq.com/cgi-bin/emotion_cgi_re_feeds"
    URL_DELETE = f"{H5}/taotao.qzone.qq.com/cgi-bin/emotion_cgi_delete_v6"
    URL_LIST = f"{PROXY}/taotao.qq.com/cgi-bin/emotion_cgi_msglist_v6"
    URL_DETAIL = f"{H5}/taotao.qq.com/cgi-bin/emotion_cgi_msgdetail_v6"
    URL_FEEDS = f"{PROXY}/ic2.qzone.qq.com/cgi-bin/feeds/feeds3_html_more"
    URL_VISITOR = f"{H5}/g.qzone.qq.com/cgi-bin/friendshow/cgi_get_visitor_more"
    URL_UPLOAD = "https://up.qzone.qq.com/cgi-bin/upload/cgi_upload_image"

    def __init__(self, session: QzoneSession, timeout: int = 10):
        super().__init__(session, timeout)
        self._parser = QzoneParser()

    # ── 公开 API ──

    async def publish(self, post: Post) -> ApiResponse:
        """发表说说。图片自动上传。"""
        ctx = self._session.get_ctx()
        data = {
            "syn_tweet_verson": "1", "paramstr": "1", "who": "1",
            "con": post.text, "feedversion": "1", "ver": "1",
            "ugc_right": "1", "to_sign": "0", "hostuin": ctx.uin,
            "code_version": "1", "format": "json",
            "qzreferrer": f"{BASE}/{ctx.uin}",
        }
        if post.images:
            pics, richvals = await self._upload_images(post.images)
            if pics:
                data.update(pic_bo=",".join(pics), richtype="1", richval="\t".join(richvals))

        raw = await self.request("POST", self.URL_PUBLISH,
                                 params={"g_tk": ctx.gtk2, "uin": ctx.uin}, data=data)
        return ApiResponse.from_raw(raw)

    async def like(self, post: Post) -> ApiResponse:
        """点赞。"""
        ctx = self._session.get_ctx()
        unikey = f"{BASE}/{post.uin}/mood/{post.tid}"
        raw = await self.request("POST", self.URL_LIKE, params={"g_tk": ctx.gtk2}, data={
            "qzreferrer": f"{BASE}/{ctx.uin}",
            "opuin": ctx.uin, "unikey": unikey, "curkey": unikey,
            "appid": 311, "from": 1, "typeid": 0,
            "abstime": int(time.time()), "fid": post.tid,
            "active": 0, "format": "json", "fupdate": 1,
        })
        return ApiResponse.from_raw(raw)

    async def comment(self, post: Post, content: str) -> ApiResponse:
        """评论说说。"""
        ctx = self._session.get_ctx()
        raw = await self.request("POST", self.URL_COMMENT, params={"g_tk": ctx.gtk2}, data={
            "topicId": f"{post.uin}_{post.tid}__1",
            "uin": ctx.uin, "hostUin": post.uin, "feedsType": 100,
            "inCharset": "utf-8", "outCharset": "utf-8",
            "plat": "qzone", "source": "ic", "platformid": 52,
            "format": "fs", "ref": "feeds", "content": content,
        })
        return ApiResponse.from_raw(raw)

    async def reply(self, post: Post, comment: Comment, content: str) -> ApiResponse:
        """回复评论。"""
        ctx = self._session.get_ctx()
        raw = await self.request("POST", self.URL_REPLY, params={"g_tk": ctx.gtk2}, data={
            "topicId": f"{post.uin}_{post.tid}__1",
            "uin": ctx.uin, "hostUin": post.uin, "feedsType": 100,
            "inCharset": "utf-8", "outCharset": "utf-8",
            "plat": "qzone", "source": "ic", "platformid": 52,
            "format": "fs", "ref": "feeds", "content": content,
            "commentId": comment.tid, "commentUin": comment.uin,
            "richval": "", "richtype": "", "private": "0",
            "paramstr": "2", "qzreferrer": f"{BASE}/{ctx.uin}/main",
        }, headers={
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Referer": f"{BASE}/", "Origin": BASE,
        })
        return ApiResponse.from_raw(raw)

    async def delete(self, tid: str) -> ApiResponse:
        """删除自己的一条说说。"""
        ctx = self._session.get_ctx()
        raw = await self.request("POST", self.URL_DELETE, params={"g_tk": ctx.gtk2}, data={
            "uin": ctx.uin, "topicId": f"{ctx.uin}_{tid}__1",
            "feedsType": 0, "feedsFlag": 0, "feedsKey": tid,
            "feedsAppid": 311, "feedsTime": int(time.time()),
            "fupdate": 1, "ref": "feeds",
        })
        return ApiResponse.from_raw(raw)

    async def get_feeds(self, target_uin: str, *, pos: int = 0, num: int = 10, replynum: int = 5) -> ApiResponse:
        """获取指定用户的说说列表。"""
        ctx = self._session.get_ctx()
        raw = await self.request("GET", self.URL_LIST, params={
            "g_tk": ctx.gtk2, "uin": target_uin,
            "ftype": 0, "sort": 0, "pos": pos, "num": num,
            "replynum": replynum, "callback": "_preloadCallback",
            "code_version": 1, "format": "json",
            "need_comment": 1, "need_private_comment": 1,
        })
        return ApiResponse.from_raw(raw)

    async def get_detail(self, post: Post) -> ApiResponse:
        """获取单条说说明细（含完整评论）。"""
        ctx = self._session.get_ctx()
        raw = await self.request("GET", self.URL_DETAIL, params={
            "uin": post.uin, "tid": post.tid,
            "format": "jsonp", "g_tk": ctx.gtk2,
        })
        return ApiResponse.from_raw(raw)

    async def get_recent_feeds(self, page: int = 1) -> ApiResponse:
        """获取好友圈说说列表（含已读/未读）。"""
        ctx = self._session.get_ctx()
        raw = await self.request("GET", self.URL_FEEDS, params={
            "uin": ctx.uin, "scope": 0, "view": 1,
            "filter": "all", "flag": 1, "applist": "all",
            "pagenum": page, "aisortEndTime": 0, "aisortOffset": 0,
            "aisortBeginTime": 0, "begintime": 0,
            "format": "json", "g_tk": ctx.gtk2,
            "useutf8": 1, "outputhtmlfeed": 1,
        })
        return ApiResponse.from_raw(raw)

    async def get_visitor(self) -> ApiResponse:
        """获取访客记录。"""
        ctx = self._session.get_ctx()
        raw = await self.request("GET", self.URL_VISITOR, params={
            "uin": ctx.uin, "mask": 7, "g_tk": ctx.gtk2,
            "page": 1, "fupdate": 1, "clear": 1,
        })
        return ApiResponse.from_raw(raw)

    # ── 内部：图片上传 ──

    async def _upload_images(self, images: list[str]) -> tuple[list[str], list[str]]:
        """上传多张图片，返回 (pic_bo_list, richval_list)。"""
        pics, richvals = [], []
        for url in images:
            try:
                picbo, richval = await self._upload_one(url)
                pics.append(picbo)
                richvals.append(richval)
            except Exception as e:
                logger.warning(f"上传图片失败 {url[:60]}: {e}")
        return pics, richvals

    async def _upload_one(self, url_or_path: str) -> tuple[str, str]:
        """上传单张图片（URL 或本地路径），返回 (pic_bo, richval)。"""
        data = await _read_image(url_or_path)
        ctx = self._session.get_ctx()
        raw = await self.request("POST", self.URL_UPLOAD, data={
            "filename": "filename", "uploadtype": "1", "albumtype": "7",
            "skey": ctx.skey, "uin": ctx.uin, "p_skey": ctx.p_skey,
            "output_type": "json", "base64": "1",
            "picfile": base64.b64encode(data).decode(),
        }, headers={
            "referer": f"{BASE}/{ctx.uin}", "origin": BASE,
        }, timeout=60)
        resp = ApiResponse.from_raw(raw, code_key="ret", msg_key="msg")
        if not resp.ok:
            raise RuntimeError(f"上传失败: {resp.message}")
        return self._parser.parse_upload(resp.data)


async def _read_image(url_or_path: str) -> bytes:
    """从 URL 或本地路径读取图片字节。"""
    if url_or_path.startswith(("http://", "https://")):
        import aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.get(url_or_path, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                return await resp.read()
    else:
        import aiofiles
        async with aiofiles.open(url_or_path, "rb") as f:
            return await f.read()
