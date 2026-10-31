import json
import os
import urllib.request

API_KEY = os.environ.get("TOKENRHYTHM_API_KEY", "")
if not API_KEY:
    raise SystemExit("请先设置环境变量 TOKENRHYTHM_API_KEY（模型服务密钥）")


def raw(model):
    url = "https://tokenrhythm.studio/v1/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "只回复两个字：在吗"}],
        "max_tokens": 20,
        "stream": False,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + API_KEY)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


for m in ["deepseek-v4-pro-0813", "deepseek-flash"]:
    print("=" * 40, m)
    try:
        resp = raw(m)
        print(json.dumps(resp, ensure_ascii=False)[:800])
    except Exception as e:
        print("ERROR:", e)
