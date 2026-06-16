# KiraAI QQ空间插件（重构版）

纯 QZone HTTP SDK + KiraAI 插件。

## 架构

```
qzone/                    ← 纯 SDK，与 KiraAI 无关
  ├── session.py          ← Cookie 解析 + g_tk 计算
  ├── client.py           ← aiohttp 客户端（连接池复用）
  ├── api.py              ← 9 个 API 端点 + 图片上传
  ├── model.py            ← Post / Comment / ApiResponse
  └── parser.py           ← JSON/JSONP/HTML 解析

main.py                   ← 插件层（待实现）
tests/test_api.py         ← 手动端点测试
```

## 测试端点

```bash
# 从 oneBot 获取 cookie：
# 在 KiraAI 中发：get_cookies(domain="user.qzone.qq.com")

# 测试说说列表
python tests/test_api.py "uin=xxx;skey=xxx;p_skey=xxx" feeds

# 测试全部端点
python tests/test_api.py "uin=xxx;skey=xxx;p_skey=xxx" all
```

## 9 个 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `publish` | POST | 发表说说（文字+图片） |
| `like` | POST | 点赞 |
| `comment` | POST | 评论 |
| `reply` | POST | 回复评论 |
| `delete` | POST | 删除说说 |
| `get_feeds` | GET | 获取指定用户说说 |
| `get_detail` | GET | 单条说说明细 |
| `get_recent_feeds` | GET | 好友圈列表 |
| `get_visitor` | GET | 访客记录 |
