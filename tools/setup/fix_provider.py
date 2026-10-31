import os

API_KEY = os.environ.get("TOKENRHYTHM_API_KEY", "")
if not API_KEY:
    raise SystemExit("请先设置环境变量 TOKENRHYTHM_API_KEY（模型服务密钥）")
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

provider = {
    "id": "tokenrhythm",
    "type": "openai_chat_completion",
    "provider_type": "chat_completion",
    "enable": True,
    "key": [API_KEY],
    "api_base": "https://tokenrhythm.studio/v1",
    "model": "deepseek-v4-pro-0813",
    "max_context_tokens": 1000000,
}

# update (id + config)
r = call("POST", "/config/provider/update", {"id": "tokenrhythm", "config": provider}, token)
print("provider/update:", r.get("status"), r.get("message"))

# list
pl = call("GET", "/config/provider/list?provider_type=chat_completion", None, token)
print("providers(chat_completion):", [(p.get("id"), p.get("type"), p.get("provider_type"), p.get("model"), p.get("enable")) for p in pl.get("data", [])])

# test
try:
    t = call("POST", "/providers/test", {"id": "tokenrhythm"}, token)
    print("provider/test:", json.dumps(t, ensure_ascii=False)[:400])
except Exception as e:
    print("test endpoint error:", e)
