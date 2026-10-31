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
cfg = cg["data"]["config"]

# 1) 默认人格切到 dafeiyu
cfg.setdefault("agent_runner", {}).setdefault("config", {}).setdefault("persona", {})
cfg["agent_runner"]["config"]["persona"]["persona_id"] = "dafeiyu"
cfg["agent_runner"]["config"]["persona"]["safety_mode"] = True

# 2) 管理者（主人）= 你的大号
admins = cfg.get("admins_id") or []
for qq in ["2721400746"]:
    if qq not in admins:
        admins.append(qq)
cfg["admins_id"] = admins

# 3) 私聊免唤醒前缀（已经是 false，确保）
cfg.setdefault("platform_settings", {})
cfg["platform_settings"]["friend_message_needs_wake_prefix"] = False

# 4) 确保 provider_settings 开启
cfg.setdefault("provider_settings", {})
cfg["provider_settings"]["enable"] = True

# 保存
r = call("POST", "/config/astrbot/update", {"conf_id": "default", "config": cfg}, token)
print("update:", r.get("status"), r.get("message") if isinstance(r.get("message"), str) else "")

# 回读确认
cg2 = call("GET", "/config/get", None, token)
c2 = cg2["data"]["config"]
print("persona now:", c2["agent_runner"]["config"]["persona"]["persona_id"])
print("admins now:", c2.get("admins_id"))
