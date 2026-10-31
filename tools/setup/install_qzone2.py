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

# 1) 给 AstrBot 配代理
cg = call("GET", "/config/get", None, token)
cfg = cg["data"]["config"]
cfg["http_proxy"] = "http://127.0.0.1:7890"
cfg["no_proxy"] = ["localhost", "127.0.0.1", "::1", "172.27.*"]
r = call("POST", "/config/astrbot/update", {"conf_id": "default", "config": cfg}, token)
print("设置代理:", r.get("status"))

# 2) 取市场下载地址
mk = call("GET", "/v1/plugins/market", None, token)
data = mk.get("data") or {}
entry = None
for k, v in data.items():
    if k == "$meta" or not isinstance(v, dict):
        continue
    if v.get("name") == "astrbot_plugin_qzone_publish":
        entry = v
        break
if not entry:
    print("没找到插件市场条目")
else:
    print("找到:", entry.get("name"), entry.get("version"))
    dl = entry.get("download_url")
    print("download_url:", dl)
    # 3) 用下载地址安装
    try:
        r2 = call("POST", "/v1/plugins/install/url", {"url": dl, "download_url": dl}, token, timeout=240)
        print("install:", r2.get("status"), str(r2.get("message"))[:300])
    except Exception as e:
        print("install error:", e)

# 4) 列表
p = call("GET", "/v1/plugins", None, token)
items = p.get("data")
items = items if isinstance(items, list) else (items.get("plugins") if isinstance(items, dict) else [])
print("已装插件:")
for it in (items if isinstance(items, list) else []):
    if isinstance(it, dict):
        print(" -", it.get("name"), it.get("version"), "activated:", it.get("activated"))
