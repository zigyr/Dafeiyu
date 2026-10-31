import os
import json, urllib.request, urllib.parse

BASE = "http://127.0.0.1:6185/api"
USER = "astrbot"
PWD = os.environ.get("ASTRBOT_PWD", "")
if not PWD:
    raise SystemExit("请先设置环境变量 ASTRBOT_PWD（AstrBot 控制台密码）")

def call(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))

login = call("POST", "/auth/login", {"username": USER, "password": PWD})
token = login["data"]["token"]

# 试几个可能的搜索结果
for kw in ["qzone", "空间", "说说"]:
    try:
        path = "/plugins/market?search=" + urllib.parse.quote(kw)
        r = call("GET", path, None, token)
        data = r.get("data")
        # 兼容不同结构
        items = data if isinstance(data, list) else (data.get("plugins") or data.get("items") or data.get("data") or [])
        print("=== search:", kw, "->", len(items) if isinstance(items, list) else type(items))
        if isinstance(items, list):
            for it in items[:12]:
                if isinstance(it, dict):
                    name = it.get("name") or it.get("id") or it.get("repo") or ""
                    desc = (it.get("desc") or it.get("description") or "")[:60]
                    print("   -", name, "|", desc)
    except Exception as e:
        print("=== search:", kw, "ERROR:", e)
