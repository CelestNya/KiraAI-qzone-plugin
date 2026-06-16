"""
从 NapCat WS 获取 QZone cookie，输出到 stdout。

用法:
  python get_cookie.py
  python get_cookie.py > cookie.txt
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# 读 KiraAI 配置找 WS 连接信息
CONFIG = Path(__file__).parent.parent.parent / "KiraAI-src" / "data" / "config" / "system_config.json"


async def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    qq_cfg = None
    for entry in cfg.get("adapters", {}).values():
        if entry.get("platform", "").upper() == "QQ":
            qq_cfg = entry["config"]
            break
    if not qq_cfg:
        print("未找到 QQ adapter 配置", file=sys.stderr)
        sys.exit(1)

    import websockets
    headers = {"Authorization": f"Bearer {qq_cfg['ws_token']}"} if qq_cfg.get("ws_token") else {}
    async with websockets.connect(
        qq_cfg["ws_uri"], additional_headers=headers, max_size=2**24
    ) as ws:
        await ws.send(json.dumps({
            "action": "get_cookies",
            "params": {"domain": "user.qzone.qq.com"},
            "echo": "get_qzone_cookie",
        }))
        while True:
            raw = await ws.recv()
            msg = json.loads(raw)
            if msg.get("echo") == "get_qzone_cookie":
                if msg.get("status") != "ok":
                    print(f"NapCat 返回错误: {msg}", file=sys.stderr)
                    sys.exit(1)
                cookie = msg.get("data", {}).get("cookies", "")
                if not cookie:
                    print("返回中无 cookies 字段", file=sys.stderr)
                    sys.exit(1)
                print(cookie)
                return


if __name__ == "__main__":
    asyncio.run(main())
