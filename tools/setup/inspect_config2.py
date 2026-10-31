import os
import json, urllib.request

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
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

login = call("POST", "/auth/login", {"username": USER, "password": PWD})
token = login["data"]["token"]

cg = call("GET", "/config/get", None, token)
d = cg.get("data")
print("top keys:", list(d.keys()) if isinstance(d, dict) else type(d))
# 找实际配置
for k, v in (d.items() if isinstance(d, dict) else []):
    if k == "metadata":
        continue
    print("KEY:", k, "TYPE:", type(v).__name__)
    if isinstance(v, dict):
        print("   sub keys:", list(v.keys())[:15])

# 打印 metadata 里的 conf 列表
meta = d.get("metadata", {})
print("metadata keys:", list(meta.keys())[:20])
for k, v in meta.items():
    if isinstance(v, dict) and "conf_id" in json.dumps(v, ensure_ascii=False)[:5000]:
        print("meta item", k, "->", json.dumps(v, ensure_ascii=False)[:300])
