import os
import json, urllib.request

BASE = "http://127.0.0.1:6185/api"
USER = "astrbot"
PWD = os.environ.get("ASTRBOT_PWD", "")
if not PWD:
    raise SystemExit("请先设置环境变量 ASTRBOT_PWD（AstrBot 控制台密码）")
DL = "https://astrbot-cloud-test-s3.astrbot.app/plugins/releases/fangnai-byte/astrbot_plugin_qzone_publish/0.2.1/astrbot_plugin_qzone_publish-0.2.1-5538677f1afe.zip"

def call(method, path, body=None, token=None, timeout=180):
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

for payload in [
    {"market_plugin_id": "fangnai-byte/astrbot_plugin_qzone_publish"},
    {"download_url": DL, "url": DL},
    {"url": DL},
]:
    try:
        r = call("POST", "/plugin/install", payload, token, timeout=200)
        print("payload", list(payload.keys()), "->", r.get("status"), str(r.get("message"))[:200])
        if r.get("status") == "ok":
            break
    except Exception as e:
        print("payload", list(payload.keys()), "ERR:", e)

# 列表确认
p = call("GET", "/v1/plugins", None, token)
items = p.get("data")
items = items if isinstance(items, list) else (items.get("plugins") if isinstance(items, dict) else [])
for it in (items if isinstance(items, list) else []):
    if isinstance(it, dict):
        print(" -", it.get("name"), it.get("version"), "activated:", it.get("activated"))
