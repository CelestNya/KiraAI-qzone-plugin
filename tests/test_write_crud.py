"""
测试写入端点：publish → like → comment → reply → delete。

用法:  python test_write_crud.py <cookie_str>
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from qzone import QzoneAPI, QzoneSession, Post, Comment


async def main():
    if len(sys.argv) < 2:
        print("用法: python test_write_crud.py <cookie_str>")
        return

    session = QzoneSession(sys.argv[1])
    api = QzoneAPI(session, timeout=15)
    ctx = session.get_ctx()
    print(f"账号: {ctx.uin}")

    try:
        # 1. PUBLISH
        print("\n--- 1. publish ---")
        text = f"[SDK 测试] 自动测试 {datetime.now().strftime('%H:%M:%S')}"
        post = Post(uin=ctx.uin, text=text)
        resp = await api.publish(post)
        if not resp.ok:
            print(f"[FAIL] publish: {resp.message}")
            return
        tid = resp.data.get("data", {}).get("tid", "")
        if not tid:
            # 有时 data 结构不同
            tid = str(resp.data.get("tid", "") or resp.data.get("id", ""))
        print(f"[OK] 发布成功, tid={tid}")

        await asyncio.sleep(2)

        # 2. LIKE
        print("\n--- 2. like ---")
        like_post = Post(uin=ctx.uin, tid=tid)
        resp = await api.like(like_post)
        print(f"[{'OK' if resp.ok else 'FAIL'}] like: {resp.message}")

        await asyncio.sleep(1)

        # 3. COMMENT
        print("\n--- 3. comment ---")
        comment_text = "SDK 测试评论"
        resp = await api.comment(like_post, comment_text)
        if not resp.ok:
            print(f"[FAIL] comment: {resp.message}")
        else:
            print(f"[OK] comment: {comment_text}")
            # 获取 comment_id 用于后续回复
            detail_resp = await api.get_detail(like_post)
            if detail_resp.ok:
                posts = api._parser.parse_feeds([detail_resp.data])
                if posts and posts[0].comments:
                    comment_id = posts[0].comments[0].tid
                    print(f"  获取到 comment_id={comment_id}")
                else:
                    print("  无法获取 comment_id，跳过 reply")
                    comment_id = None
            else:
                print("  无法获取详情，跳过 reply")
                comment_id = None

        await asyncio.sleep(1)

        # 4. REPLY (如果有 comment_id)
        print("\n--- 4. reply ---")
        if comment_id:
            target_comment = Comment(uin=ctx.uin, tid=comment_id)
            reply_text = "SDK 测试回复"
            resp = await api.reply(like_post, target_comment, reply_text)
            print(f"[{'OK' if resp.ok else 'FAIL'}] reply: {resp.message}")
        else:
            print("[SKIP] 无 comment_id")

        await asyncio.sleep(1)

        # 5. DELETE
        print("\n--- 5. delete ---")
        resp = await api.delete(tid)
        print(f"[{'OK' if resp.ok else 'FAIL'}] delete: {resp.message}")

        print("\n全部测试完成")

    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
