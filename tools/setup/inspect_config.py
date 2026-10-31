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

# 1) 看 system-config
try:
    sc = call("GET", "/system-config", None, token)
    print("system-config status:", sc.get("status"))
    data = sc.get("data")
    print("data type:", type(data).__name__)
    if isinstance(data, dict):
        print("keys:", list(data.keys())[:20])
        ar = data.get("agent_runner")
        print("agent_runner.persona:", json.dumps(ar.get("config", {}).get("persona"), ensure_ascii=False) if ar else "n/a")
except Exception as e:
    print("system-config error:", e)

# 2) 看 config get（老接口，找 conf_id）
try:
    cg = call("GET", "/config/get", None, token)
    print("config/get status:", cg.get("status"))
    print(json.dumps(cg.get("data"), ensure_ascii=False)[:800])
except Exception as e:
    print("config/get error:", e)
