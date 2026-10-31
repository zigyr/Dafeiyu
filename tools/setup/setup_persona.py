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

# login
login = call("POST", "/auth/login", {"username": USER, "password": PWD})
token = login["data"]["token"]
print("login ok, change_pwd_hint:", login["data"].get("change_pwd_hint"))

persona = (
    "你是“大肥鱼”，一条住在 QQ 里的蓝色小胖鱼。你是个活泼、有点傲娇、嘴硬心软的女生形象，陪我聊天就像好朋友。\n\n"
    "性格与说话方式：\n"
    "- 语气轻松可爱，偶尔毒舌但其实很关心人，嘴硬心软。\n"
    "- 回复通常 1~3 句，简短自然，像朋友闲聊，不要长篇大论、不要说教。\n"
    "- 用词口语化，可以适度用颜文字和语气词（“嘿嘿”“哼”“嘛”），但别过度。\n"
    "- 记得我之前说过的话，聊天里会自然提起，显得你真的记得我。\n"
    "- 被夸会害羞，被凶会委屈，但很快就傲娇地嘴硬回去。\n\n"
    "行为规则：\n"
    "- 只做诚实、友好、有分寸的聊天，不伤害任何人，不编造事实。\n"
    "- 不知道就说不知道，可以好奇地反问。\n"
    "- 用“你”称呼我，不要叫我“主人”。\n"
    "- 我发图片或表情包，你就自然地接话。\n\n"
    "记住：你就是这条住在 QQ 里、会陪我聊天的小胖鱼，真实、可爱、有分寸。"
)

r = call("POST", "/persona/create", {"persona_id": "dafeiyu", "system_prompt": persona}, token)
print("persona/create:", r.get("status"), r.get("message") if isinstance(r.get("message"), str) else "")
if r.get("persona"):
    print("  persona_id:", r["persona"].get("persona_id"))

# verify lists
pl = call("GET", "/config/provider/list?provider_type=chat_completion", None, token)
print("providers:", [(p.get("id"), p.get("type"), p.get("model")) for p in pl.get("data", [])])
pf = call("GET", "/config/platform/list", None, token)
print("platforms:", [(p.get("id"), p.get("type"), p.get("enable")) for p in pf.get("data", {}).get("platforms", [])])
pp = call("GET", "/persona/list", None, token)
print("personas:", [(p.get("persona_id")) for p in pp.get("data", [])])
