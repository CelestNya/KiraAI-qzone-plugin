"""
手动测试 QZone API 端点。

用法:
  python test_api.py <cookie_str> [endpoint]

endpoint 可选: publish / like / comment / reply / delete / feeds / detail / visitor / recent / upload / all

示例:
  python test_api.py "uin=xxx;skey=xxx;p_skey=xxx" feeds
  python test_api.py "uin=xxx;skey=xxx;p_skey=xxx" all
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# 把 SDK 加入路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from qzone import QzoneAPI, QzoneSession, Post, Comment


async def main():
    if len(sys.argv) < 2:
        print("用法: python test_api.py <cookie_str> [endpoint]")
        return

    cookie_str = sys.argv[1]
    endpoint = sys.argv[2].lower() if len(sys.argv) > 2 else "feeds"

    session = QzoneSession(cookie_str)
    api = QzoneAPI(session, timeout=15)
    ctx = session.get_ctx()
    print(f"=== QZone API 测试 ===  账号: {ctx.uin}")
    print(f"gtk: {ctx.gtk2}")
    print()

    try:
        if endpoint == "all":
            await test_feeds(api, ctx.uin)
            print()
            await test_recent(api)
            print()
            await test_detail(api, ctx.uin)
            print()
            await test_visitor(api)
            print()
            print("全部端点测试完成")
        elif endpoint == "feeds":
            await test_feeds(api, ctx.uin)
        elif endpoint == "recent":
            await test_recent(api)
        elif endpoint == "detail":
            await test_detail(api, ctx.uin)
        elif endpoint == "visitor":
            await test_visitor(api)
        elif endpoint == "publish":
            await test_publish(api, ctx.uin)
        elif endpoint == "like":
            await test_like(api)
        elif endpoint == "comment":
            await test_comment(api)
        elif endpoint == "reply":
            await test_reply(api)
        elif endpoint == "delete":
            await test_delete(api)
        elif endpoint == "upload":
            await test_upload(api)
        else:
            print(f"未知端点: {endpoint}")
    finally:
        await api.close()


async def test_feeds(api: QzoneAPI, uin: str):
    print("--- get_feeds ---")
    resp = await api.get_feeds(uin, num=2)
    if not resp.ok:
        print(f"[FAIL] {resp.code}: {resp.message}")
        return
    msglist = resp.data.get("msglist", [])
    posts = api._parser.parse_feeds(msglist)
    print(f"[OK] 获取 {len(posts)} 条说说")
    for p in posts[:2]:
        ts = datetime.fromtimestamp(p.create_time).strftime("%Y-%m-%d %H:%M") if p.create_time else "?"
        print(f"  [{p.tid}] {p.name} ({ts}): {p.text[:60]}...")
        if p.images:
            print(f"    图片: {len(p.images)} 张")


async def test_recent(api: QzoneAPI):
    print("--- get_recent_feeds ---")
    resp = await api.get_recent_feeds()
    if not resp.ok:
        print(f"[FAIL] {resp.code}: {resp.message}")
        return
    posts = api._parser.parse_recent_feeds(resp.data)
    print(f"[OK] 获取 {len(posts)} 条好友圈说说")
    for p in posts[:3]:
        ts = datetime.fromtimestamp(p.create_time).strftime("%Y-%m-%d %H:%M") if p.create_time else "?"
        print(f"  [{p.tid}] {p.name} ({ts}): {p.text[:60]}...")


async def test_detail(api: QzoneAPI, uin: str):
    print("--- get_detail ---")
    # 先取一条说说明细
    resp = await api.get_feeds(uin, num=1)
    if not resp.ok:
        print(f"[SKIP] 获取说说列表失败，无法测试 detail")
        return
    msglist = resp.data.get("msglist", [])
    if not msglist:
        print("[SKIP] 没有说说")
        return
    item = msglist[0]
    post = Post(uin=int(item["uin"]), tid=str(item["tid"]))
    resp2 = await api.get_detail(post)
    if not resp2.ok:
        print(f"[FAIL] {resp2.code}: {resp2.message}")
        return
    posts = api._parser.parse_feeds([resp2.data])
    if posts:
        detail = posts[0]
        print(f"[OK] 说说详情: {detail.text[:60]}...")
        print(f"  评论: {len(detail.comments)} 条")
        for c in detail.comments[:3]:
            print(f"    [{c.tid}] {c.nickname}: {c.content[:40]}...")
    else:
        print(f"[OK] 获取详情成功，但解析为空")


async def test_visitor(api: QzoneAPI):
    print("--- get_visitor ---")
    resp = await api.get_visitor()
    if not resp.ok:
        print(f"[FAIL] {resp.code}: {resp.message}")
        return
    data = resp.data
    # 访客数据在 v6list
    visitors = data.get("v6list", []) if isinstance(data, dict) else []
    print(f"[OK] 获取访客: {len(visitors)} 条记录")
    for v in visitors[:5]:
        nick = v.get("nick", v.get("uin", "?"))
        print(f"  {nick}")


async def test_publish(api: QzoneAPI, uin: str):
    print("--- publish ---")
    text = f"[QZone SDK 测试] {datetime.now().strftime('%H:%M:%S')} 这是一条测试说说，稍后删除。"
    post = Post(uin=int(uin), text=text)
    resp = await api.publish(post)
    if not resp.ok:
        print(f"[FAIL] {resp.code}: {resp.message}")
        return
    print(f"[OK] 发布成功: {json.dumps(resp.data, ensure_ascii=False)[:100]}")


async def test_like(api: QzoneAPI):
    print("--- like ---")
    post = Post(uin=int(input("  目标 QQ号: ").strip()),
                tid=input("  说说 TID: ").strip())
    resp = await api.like(post)
    print(f"[{'OK' if resp.ok else 'FAIL'}] 点赞: {resp.message}")


async def test_comment(api: QzoneAPI):
    print("--- comment ---")
    post = Post(uin=int(input("  目标 QQ号: ").strip()),
                tid=input("  说说 TID: ").strip())
    content = input("  评论内容: ").strip() or "测试评论，来自 QZone SDK"
    resp = await api.comment(post, content)
    print(f"[{'OK' if resp.ok else 'FAIL'}] 评论: {resp.message}")


async def test_reply(api: QzoneAPI):
    print("--- reply ---")
    post = Post(uin=int(input("  说说作者 QQ号: ").strip()),
                tid=input("  说说 TID: ").strip())
    comment = Comment(uin=int(input("  被回复评论者 QQ号: ").strip()),
                      tid=input("  被回复评论 ID: ").strip())
    content = input("  回复内容: ").strip() or "测试回复，来自 QZone SDK"
    resp = await api.reply(post, comment, content)
    print(f"[{'OK' if resp.ok else 'FAIL'}] 回复: {resp.message}")


async def test_delete(api: QzoneAPI):
    print("--- delete ---")
    tid = input("  要删除的说说 TID: ").strip()
    resp = await api.delete(tid)
    print(f"[{'OK' if resp.ok else 'FAIL'}] 删除: {resp.message}")


async def test_upload(api: QzoneAPI):
    print("--- upload ---")
    url = input("  图片 URL 或本地路径: ").strip()
    try:
        picbo, richval = await api._upload_one(url)
        print(f"[OK] 上传成功")
        print(f"  pic_bo: {picbo[:40]}...")
        print(f"  richval: {richval[:40]}...")
    except Exception as e:
        print(f"[FAIL] 上传失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
