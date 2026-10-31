#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大肥鱼控制台 - 本地 Web 控制面板
管理 AstrBot (Windows) 与 NapCat (WSL Kali) 的启动/停止/重启/日志/二维码
仅监听 127.0.0.1，不对外网开放。
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = r"F:\dafeiyu"
LOG_DIR = os.path.join(ROOT, "logs")
ASTRBOT_EXE = r"C:\Users\zigyr\.local\bin\astrbot.exe"
ASTRBOT_CWD = os.path.join(ROOT, "astrbot")
ASTRBOT_LOG = os.path.join(LOG_DIR, "astrbot-console.log")
ASTRBOT_FALLBACK_LOG = os.path.join(LOG_DIR, "astrbot-first.log")
WSL_DISTRO = "kali-linux"
NAPCAT_DIR = "/root/Napcat"
NAPCAT_CONFIG_DIR = "/root/Napcat/opt/QQ/resources/app/app_launcher/napcat/config"
NAPCAT_LOG = "/root/napcat-run.log"
NAPCAT_QR = "/root/Napcat/opt/QQ/resources/app/app_launcher/napcat/cache/qrcode.png"
CONSOLE_PORT = 6186
CREATE_NO_WINDOW = 0x08000000

_astrbot_proc = None


def run(cmd, timeout=25, cwd=None):
    try:
        return subprocess.run(
            cmd, capture_output=True, timeout=timeout, cwd=cwd,
            encoding="utf-8", errors="replace",
            creationflags=0x08000000,  # CREATE_NO_WINDOW：调用 wsl.exe 时不弹黑框
        )
    except Exception as e:
        class R:
            stdout = ""
            stderr = str(e)
            returncode = -1
        return R()


def wsl(args, timeout=25):
    return run(["wsl", "-d", WSL_DISTRO, "-u", "root", "--"] + args, timeout=timeout)


def wsl_bash(script, timeout=25):
    return wsl(["bash", "-c", script], timeout=timeout)


def port_open(port, host="127.0.0.1", timeout=0.6):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def pid_on_port(port):
    r = run(["netstat", "-ano", "-p", "TCP"])
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1].endswith(":" + str(port)) and parts[3].upper() == "LISTENING":
            return parts[4]
    return None


def wsl_gateway():
    r = wsl_bash("ip route | awk '/default/{print $3; exit}'")
    import re as _re
    m = _re.search(r"(\d+\.\d+\.\d+\.\d+)", r.stdout)
    return m.group(1) if m else ""


def napcat_pids():
    r = wsl_bash("pgrep -f 'opt/QQ/qq --no-sandbox' | tr '\\n' ' '")
    return [p for p in r.stdout.split() if p.isdigit()]


def qq_linked():
    r = run(["netstat", "-ano", "-p", "TCP"])
    for line in r.stdout.splitlines():
        if ":6199" in line and "ESTABLISHED" in line.upper():
            return True
    return False


def read_tail(path, lines=150):
    try:
        with open(path, "rb") as f:
            data = f.read()
        text = data.decode("utf-8", errors="replace")
        text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)  # 去掉终端颜色码
        text = text.replace("\r\n", "\n").split("\n")
        return "\n".join(text[-lines:])
    except Exception as e:
        return "[无法读取日志] %s" % e


def wsl_probe():
    """一次 wsl 调用同时取「网关 IP」和「NapCat 进程 PID」，减少弹窗与开销"""
    r = wsl_bash(
        "ip route | awk '/default/{print $3; exit}'; echo '@@@'; "
        "pgrep -f 'opt/QQ/qq --no-sandbox' | tr '\\n' ' '"
    )
    out = r.stdout or ""
    parts = out.split("@@@")
    gw = ""
    m = re.search(r"(\d+\.\d+\.\d+\.\d+)", parts[0])
    if m:
        gw = m.group(1)
    pids = []
    if len(parts) > 1:
        pids = [p for p in parts[1].split() if p.isdigit()]
    return gw, pids


_cached_gw = None


def status():
    """状态检测：已连接时用 netstat 判断，避免频繁拉起 wsl.exe"""
    global _cached_gw
    astrbot_alive = port_open(6185)
    linked = qq_linked()
    pids = []
    if linked:
        # 反向 WS 已通 => NapCat 必然在运行，不必再探 WSL
        if not _cached_gw:
            _cached_gw = wsl_gateway()
        gw = _cached_gw or ""
        running = True
    else:
        gw, pids = wsl_probe()
        if gw:
            _cached_gw = gw
        running = len(pids) > 0
    return {
        "astrbot": {
            "running": astrbot_alive,
            "pid": pid_on_port(6185) if astrbot_alive else None,
            "url": "http://127.0.0.1:6185",
        },
        "napcat": {
            "running": running,
            "pids": pids,
            "wsl_gateway": gw,
        },
        "qq": {
            "linked": linked,
            "account": "2960405592",
        },
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def start_astrbot():
    if port_open(6185):
        return {"ok": True, "msg": "AstrBot 已在运行"}
    global _astrbot_proc
    os.makedirs(LOG_DIR, exist_ok=True)
    # 轮转旧日志，避免历史 GBK 字节与新 UTF-8 内容混在一起导致乱码
    try:
        if os.path.exists(ASTRBOT_LOG):
            old = ASTRBOT_LOG + ".old"
            if os.path.exists(old):
                os.remove(old)
            os.replace(ASTRBOT_LOG, old)
    except Exception:
        pass
    logf = open(ASTRBOT_LOG, "ab", buffering=0)
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONLEGACYWINDOWSSTDIO"] = "0"
    try:
        _astrbot_proc = subprocess.Popen(
            [ASTRBOT_EXE, "run", "--port", "6185"],
            cwd=ASTRBOT_CWD, stdout=logf, stderr=subprocess.STDOUT,
            creationflags=0x00000008,  # DETACHED_PROCESS: 与控制台解耦，关掉控制台不会带走它
            env=env,
        )
    except Exception as e:
        return {"ok": False, "msg": "启动失败: %s" % e}
    for _ in range(40):
        time.sleep(0.5)
        if port_open(6185):
            return {"ok": True, "msg": "AstrBot 已启动 (pid %s)" % _astrbot_proc.pid}
    return {"ok": False, "msg": "AstrBot 启动超时，请看日志"}


def stop_astrbot():
    pid = pid_on_port(6185)
    if not pid:
        return {"ok": True, "msg": "AstrBot 未在运行"}
    run(["taskkill", "/T", "/F", "/PID", str(pid)])
    time.sleep(1.5)
    return {"ok": True, "msg": "AstrBot 已停止"}


def update_onebot_url():
    gw = wsl_gateway()
    if not gw:
        return None
    script = (
        "for f in " + NAPCAT_CONFIG_DIR + "/onebot11*.json; do "
        "[ -f \"$f\" ] || continue; "
        "sed -i 's#ws://[0-9.]*:6199/ws#ws://" + gw + ":6199/ws#g' \"$f\"; "
        "done; echo " + gw
    )
    wsl_bash(script)
    return gw


def start_napcat():
    if napcat_pids():
        return {"ok": True, "msg": "NapCat 已在运行"}
    gw = update_onebot_url()
    wsl_bash("pkill -f 'Xvfb :' >/dev/null 2>&1; sleep 0.3; "
             "screen -wipe >/dev/null 2>&1; "
             "screen -dmS napcat bash -c 'xvfb-run -a " + NAPCAT_DIR + "/opt/QQ/qq --no-sandbox "
             "> " + NAPCAT_LOG + " 2>&1'")
    for _ in range(40):
        time.sleep(0.5)
        if napcat_pids():
            return {"ok": True, "msg": "NapCat 已启动，网关 %s" % (gw or "?")}
    return {"ok": False, "msg": "NapCat 启动超时，请查看日志（可能需要重新扫码登录）"}


def stop_napcat():
    wsl_bash("screen -S napcat -X quit >/dev/null 2>&1; "
             "pkill -f 'opt/QQ/qq --no-sandbox' >/dev/null 2>&1; "
             "pkill -f 'Xvfb :' >/dev/null 2>&1; sleep 0.5; echo done")
    time.sleep(1)
    return {"ok": True, "msg": "NapCat 已停止"}


def get_qrcode_bytes():
    r = wsl_bash("if [ -f " + NAPCAT_QR + " ]; then base64 -w0 " + NAPCAT_QR + "; fi")
    b64 = r.stdout.strip()
    if not b64:
        return None
    import base64 as _b64
    try:
        return _b64.b64decode(b64)
    except Exception:
        return None


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>大肥鱼控制台</title>
<style>
  :root { --bg:#0f1419; --card:#1a2129; --line:#2a333d; --fg:#e6edf3; --dim:#8b98a5;
          --ok:#2ea043; --bad:#da3633; --warn:#d29922; --accent:#3b82f6; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font-family:"Segoe UI","Microsoft YaHei",system-ui,sans-serif; }
  .wrap { max-width:1080px; margin:0 auto; padding:24px 18px 60px; }
  h1 { font-size:22px; margin:0 0 4px; }
  .sub { color:var(--dim); font-size:13px; margin-bottom:22px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; }
  .card h2 { font-size:14px; margin:0 0 10px; color:var(--dim); font-weight:600; letter-spacing:.5px; }
  .dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:7px; }
  .ok { background:var(--ok); box-shadow:0 0 8px var(--ok); }
  .bad { background:var(--bad); box-shadow:0 0 8px var(--bad); }
  .state { font-size:17px; font-weight:600; }
  .meta { color:var(--dim); font-size:12px; margin-top:6px; word-break:break-all; }
  .btns { display:flex; gap:8px; margin-top:14px; flex-wrap:wrap; }
  button { background:#232c36; color:var(--fg); border:1px solid var(--line); border-radius:8px;
           padding:7px 14px; font-size:13px; cursor:pointer; }
  button:hover { border-color:var(--accent); }
  button.pri { background:var(--accent); border-color:var(--accent); color:#fff; }
  button.danger { background:#3a1e1e; border-color:#5a2a2a; }
  button:disabled { opacity:.45; cursor:not-allowed; }
  .bar { display:flex; gap:10px; margin:18px 0; flex-wrap:wrap; align-items:center; }
  .logs { background:#0b0f14; border:1px solid var(--line); border-radius:10px;
          padding:12px; font-family:Consolas,monospace; font-size:12px; line-height:1.5;
          height:320px; overflow:auto; white-space:pre-wrap; word-break:break-word; color:#c8d3de; }
  .tabs { display:flex; gap:8px; margin-bottom:10px; }
  .tab { padding:6px 14px; border-radius:8px; cursor:pointer; font-size:13px;
         background:#232c36; border:1px solid var(--line); }
  .tab.active { background:var(--accent); border-color:var(--accent); color:#fff; }
  #toast { position:fixed; right:20px; bottom:20px; background:#232c36; border:1px solid var(--line);
           border-radius:10px; padding:12px 18px; font-size:13px; opacity:0; transition:.25s; pointer-events:none; }
  #toast.show { opacity:1; }
  .qrwrap { text-align:center; }
  .qrwrap img { background:#fff; border-radius:10px; padding:10px; max-width:220px; }
  .link { color:var(--accent); text-decoration:none; }
</style>
</head>
<body>
<div class="wrap">
  <h1>🐟 大肥鱼控制台</h1>
  <div class="sub">AstrBot（Windows）· NapCat（WSL Kali）· QQ 2960405592 &nbsp;|&nbsp;
    <span id="clock">--:--:--</span></div>

  <div class="grid">
    <div class="card">
      <h2>AstrBot 本体</h2>
      <div class="state"><span id="a-dot" class="dot bad"></span><span id="a-state">检测中…</span></div>
      <div class="meta" id="a-meta"></div>
      <div class="btns">
        <button class="pri" onclick="act('astrbot','start')">启动</button>
        <button class="danger" onclick="act('astrbot','stop')">停止</button>
        <button onclick="act('astrbot','restart')">重启</button>
        <a class="link" href="http://127.0.0.1:6185" target="_blank" style="align-self:center;font-size:13px;">打开后台 ↗</a>
      </div>
    </div>

    <div class="card">
      <h2>NapCat 网关</h2>
      <div class="state"><span id="n-dot" class="dot bad"></span><span id="n-state">检测中…</span></div>
      <div class="meta" id="n-meta"></div>
      <div class="btns">
        <button class="pri" onclick="act('napcat','start')">启动</button>
        <button class="danger" onclick="act('napcat','stop')">停止</button>
        <button onclick="act('napcat','restart')">重启</button>
        <button onclick="showQR()">二维码</button>
      </div>
    </div>

    <div class="card">
      <h2>QQ 连接</h2>
      <div class="state"><span id="q-dot" class="dot bad"></span><span id="q-state">检测中…</span></div>
      <div class="meta" id="q-meta"></div>
      <div class="btns">
        <button onclick="act('all','restart')">全部重启</button>
        <button onclick="showQR()">需要重登？扫码</button>
      </div>
    </div>
  </div>

  <div class="bar">
    <button class="pri" onclick="act('all','start')">▶ 一键启动全部</button>
    <button class="danger" onclick="act('all','stop')">■ 全部停止</button>
    <span class="meta" id="last-act"></span>
  </div>

  <div class="tabs">
    <div class="tab active" data-t="astrbot" onclick="pick('astrbot')">AstrBot 日志</div>
    <div class="tab" data-t="napcat" onclick="pick('napcat')">NapCat 日志</div>
    <div class="tab" data-t="qq" onclick="pick('qq')">QQ 会话日志</div>
  </div>
  <div class="logs" id="logs">加载中…</div>

  <div id="qrmodal" style="display:none; margin-top:18px;" class="card qrwrap">
    <h2>扫码登录（二维码过期请点「重启 NapCat」后再点此）</h2>
    <img id="qrimg" alt="二维码">
    <div class="meta">用**小号**手机 QQ 扫描</div>
  </div>
</div>
<div id="toast"></div>
<script>
let tab = 'astrbot';
async function j(url, opt) {
  const r = await fetch(url, opt); return await r.json();
}
function toast(msg, bad) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.style.borderColor = bad ? '#da3633' : '#2ea043';
  t.classList.add('show'); setTimeout(()=>t.classList.remove('show'), 3200);
}
async function refresh() {
  try {
    const s = await j('/api/status');
    setState('a', s.astrbot.running, '运行中', '已停止',
      s.astrbot.running ? ('PID ' + s.astrbot.pid) : '未运行');
    setState('n', s.napcat.running, '运行中', '已停止',
      s.napcat.running ? ('PID ' + s.napcat.pids.join(',') + ' · 网关 ' + s.napcat.wsl_gateway)
                       : ('未运行 · 网关 ' + (s.napcat.wsl_gateway || '?')));
    setState('q', s.qq.linked, '已连接', '未连接',
      '账号 ' + s.qq.account + (s.qq.linked ? ' · 反向 WS 已通' : ' · 等待 NapCat 连接'));
    document.getElementById('clock').textContent = s.server_time;
  } catch(e) {}
}
function setState(k, ok, okText, badText, meta) {
  const d = document.getElementById(k+'-dot'), st = document.getElementById(k+'-state');
  d.className = 'dot ' + (ok ? 'ok' : 'bad');
  st.textContent = ok ? okText : badText;
  document.getElementById(k+'-meta').textContent = meta || '';
}
async function act(target, action) {
  const btns = document.querySelectorAll('button'); btns.forEach(b=>b.disabled=true);
  try {
    const r = await j('/api/action', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({target, action})});
    toast(r.msg || '完成', !r.ok);
    document.getElementById('last-act').textContent = new Date().toLocaleTimeString() + ' ' + (r.msg||'');
  } catch(e) { toast('操作失败: '+e, true); }
  btns.forEach(b=>b.disabled=false);
  refresh(); loadLogs();
}
async function loadLogs() {
  try {
    const r = await j('/api/logs?target='+tab+'&lines=200');
    const el = document.getElementById('logs');
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    el.textContent = r.text || '(空)';
    if (atBottom) el.scrollTop = el.scrollHeight;
  } catch(e) {}
}
function pick(t) {
  tab = t;
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active', x.dataset.t===t));
  loadLogs();
}
async function showQR() {
  const m = document.getElementById('qrmodal');
  m.style.display = 'block';
  const img = document.getElementById('qrimg');
  img.src = '/api/qrcode?t=' + Date.now();
  img.onerror = () => { img.removeAttribute('src'); toast('没有可用二维码，请先点「重启 NapCat」', true); };
  m.scrollIntoView({behavior:'smooth'});
}
refresh(); loadLogs();
setInterval(refresh, 3000);
setInterval(loadLogs, 4000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            return self._send(200, INDEX_HTML, "text/html; charset=utf-8")
        if u.path == "/api/status":
            return self._send(200, json.dumps(status(), ensure_ascii=False))
        if u.path == "/api/qrcode":
            data = get_qrcode_bytes()
            if not data:
                return self._send(404, b"no qrcode", "text/plain")
            return self._send(200, data, "image/png")
        if u.path == "/api/logs":
            target = (q.get("target") or ["astrbot"])[0]
            lines = int((q.get("lines") or ["150"])[0])
            if target == "astrbot":
                path = ASTRBOT_LOG if os.path.exists(ASTRBOT_LOG) and os.path.getsize(ASTRBOT_LOG) > 0 else ASTRBOT_FALLBACK_LOG
                text = read_tail(path, lines)
            elif target == "napcat":
                r = wsl_bash("tail -n %d %s 2>/dev/null | sed 's/\\x1b\\[[0-9;]*m//g'" % (lines, NAPCAT_LOG))
                text = r.stdout or "(暂无日志)"
            else:
                r = wsl_bash("grep -E '发送 ->|接收 <-' %s 2>/dev/null | tail -n %d" % (NAPCAT_LOG, lines))
                text = r.stdout or "(暂无会话)"
            return self._send(200, json.dumps({"text": text}, ensure_ascii=False))
        return self._send(404, json.dumps({"ok": False, "msg": "not found"}))

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/api/action":
            return self._send(404, json.dumps({"ok": False, "msg": "not found"}))
        try:
            ln = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(ln).decode("utf-8") or "{}")
        except Exception:
            body = {}
        target = body.get("target")
        action = body.get("action")
        try:
            if target == "astrbot":
                res = start_astrbot() if action == "start" else stop_astrbot()
                if action == "restart":
                    stop_astrbot(); res = start_astrbot()
            elif target == "napcat":
                res = start_napcat() if action == "start" else stop_napcat()
                if action == "restart":
                    stop_napcat(); res = start_napcat()
            elif target == "all":
                if action == "start":
                    a = start_astrbot(); n = start_napcat()
                    res = {"ok": a["ok"] and n["ok"], "msg": a["msg"] + " | " + n["msg"]}
                elif action == "stop":
                    stop_napcat(); res = stop_astrbot()
                else:
                    stop_napcat(); stop_astrbot()
                    a = start_astrbot(); n = start_napcat()
                    res = {"ok": a["ok"] and n["ok"], "msg": a["msg"] + " | " + n["msg"]}
            else:
                res = {"ok": False, "msg": "未知目标"}
        except Exception as e:
            res = {"ok": False, "msg": "异常: %s" % e}
        return self._send(200, json.dumps(res, ensure_ascii=False))


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", CONSOLE_PORT), Handler)
    except OSError:
        print("控制台已在运行: http://127.0.0.1:%d" % CONSOLE_PORT)
        return
    print("大肥鱼控制台已启动: http://127.0.0.1:%d" % CONSOLE_PORT)
    srv.serve_forever()


if __name__ == "__main__":
    main()
