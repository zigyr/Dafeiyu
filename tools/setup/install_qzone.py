import os
import json, urllib.request

BASE = "http://127.0.0.1:6185/api"
USER = "astrbot"
PWD = os.environ.get("ASTRBOT_PWD", "")
if not PWD:
    raise SystemExit("请先设置环境变量 ASTRBOT_PWD（AstrBot 控制台密码）")

def call(method, path, body=None, token=None, timeout=120):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

login = call("POST", "/auth/login", {"username": USER, "password": PWD})
token = login["data"]["token"]

repo = "https://github.com/Fangnai-byte/astrbot_plugin_qzone_publish"
print("安装:", repo)
try:
    r = call("POST", "/v1/plugins/install/url", {"url": repo}, token, timeout=180)
    print("install:", r.get("status"), str(r.get("message"))[:300])
except Exception as e:
    print("install error:", e)

# 列出已装插件
try:
    p = call("GET", "/v1/plugins", None, token)
    data = p.get("data")
    items = data if isinstance(data, list) else (data.get("plugins") if isinstance(data, dict) else [])
    print("已装插件数:", len(items) if isinstance(items, list) else "?")
    for it in (items if isinstance(items, list) else []):
        if isinstance(it, dict):
            print(" -", it.get("name"), "|", it.get("version"), "| activated:", it.get("activated"))
except Exception as e:
    print("list error:", e)
