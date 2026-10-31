import os
import json, urllib.request

BASE = "http://127.0.0.1:6185/api"
USER = "astrbot"
PWD = os.environ.get("ASTRBOT_PWD", "")
if not PWD:
    raise SystemExit("请先设置环境变量 ASTRBOT_PWD（AstrBot 控制台密码）")

def call(method, path, body=None, token=None, timeout=60):
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

pid = "astrbot_plugin_qzone_publish"
conf = {
    "enabled": True,
    "dry_run": False,
    "cookies": "",
    "uin": "2960405592",
    "auto_fetch_cookie": True,
    "allow_user_ids": ["2721400746"],
    "enable_image": True,
    "max_length": 900,
    "timeout_sec": 30,
    "tool_enabled": True,
    "oneshot_on_load": False,
    "oneshot_delay": 8,
    "oneshot_content": "",
    "oneshot_flag_path": "/root/qzone_oneshot.flag",
    "oneshot_result_path": "/root/qzone_oneshot_result.json",
}
try:
    r = call("PUT", "/v1/plugins/%s/config" % pid, {"config": conf}, token)
    print("config:", r.get("status"), str(r.get("message"))[:200])
except Exception as e:
    print("config error:", e)
    try:
        r = call("PUT", "/v1/plugins/%s/config" % pid, conf, token)
        print("config(flat):", r.get("status"), str(r.get("message"))[:200])
    except Exception as e2:
        print("config(flat) error:", e2)

# 读回
try:
    g = call("GET", "/v1/plugins/%s/config" % pid, None, token)
    print("回读:", json.dumps(g.get("data"), ensure_ascii=False)[:600])
except Exception as e:
    print("get config error:", e)
