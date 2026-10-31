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
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

login = call("POST", "/auth/login", {"username": USER, "password": PWD})
token = login["data"]["token"]

r = call("GET", "/v1/plugins/market", None, token)
data = r.get("data") or {}
plugins = data.get("plugins") or {}
print("市场插件总数:", len(plugins))

kw = ["qzone", "qq空间", "空间", "说说", "qzone_publish", "post"]
hits = []
for key, p in plugins.items():
    text = (json.dumps(p, ensure_ascii=False)).lower()
    if any(k.lower() in text for k in ["qzone", "空间", "说说"]):
        hits.append(p)

print("相关插件:", len(hits))
for p in hits[:20]:
    print("-", p.get("name"), "|", p.get("display_name"), "|", (p.get("desc") or "")[:80].replace("\n", " "))
    print("   repo:", p.get("repo"), "| astrbot:", p.get("astrbot_version"))
