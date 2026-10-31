# -*- coding: utf-8 -*-
"""
大肥鱼控制台 · 核心层
------------------------------------------------------------
负责 AstrBot（Windows）与 NapCat（WSL Kali）的启动、停止、状态、
OneBot 反向连接校准、NapCat WebUI 通讯、快速登录与二维码。

设计原则：
1. 所有子进程都不弹黑窗（CREATE_NO_WINDOW + SW_HIDE）。
2. 状态判断不靠猜：AstrBot 看端口/PID，NapCat 看进程 + WebUI，
   QQ 看 WebUI 登录态 + 6199 反向 WS。
3. 连接不上时能自动定位并修复：网关 IP、token、配置文件名、
   OneBot 平台开关、二维码时效。
"""
from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import re
import secrets
import shlex
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import psutil

from settings import ROOT, Settings

# 把随包携带的 qrcode（BSD）放进搜索路径，离线也能生成二维码
_VENDOR = Path(__file__).resolve().parent / "vendor"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
LOG_DIR = ROOT / "logs"
ASTRBOT_LOG = LOG_DIR / "astrbot-console.log"
ASTRBOT_FALLBACK_LOG = LOG_DIR / "astrbot-first.log"
EVENT_LOG = LOG_DIR / "console-events.log"
ANSI_RE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\)|[@-_])")

Progress = Callable[[int, str], None]


def _noop(_pct: int, _msg: str) -> None:
    pass


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text or "")


def _decode(data: bytes) -> str:
    if not data:
        return ""
    for enc in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _startupinfo():
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    return si


def run_hidden(
    cmd: list[str],
    timeout: float = 20,
    cwd: str | None = None,
    input_data: bytes | None = None,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """隐藏窗口执行命令。绝对不要用 DETACHED_PROCESS，否则会新建黑窗。"""
    kwargs = dict(
        capture_output=True,
        timeout=timeout,
        cwd=cwd,
        input=input_data,
        env=env,
        creationflags=CREATE_NO_WINDOW,
        startupinfo=_startupinfo(),
    )
    if not cmd:
        raise ValueError("empty command")
    return subprocess.run(cmd, **kwargs)


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def listening_pids(port: int) -> list[int]:
    out: list[int] = []
    try:
        for c in psutil.net_connections(kind="tcp"):
            if c.laddr and c.laddr.port == int(port) and c.status == psutil.CONN_LISTEN:
                if c.pid:
                    out.append(int(c.pid))
    except Exception:
        pass
    return out


def established_peers(port: int) -> list[str]:
    peers: list[str] = []
    try:
        for c in psutil.net_connections(kind="tcp"):
            if c.status != psutil.CONN_ESTABLISHED:
                continue
            if c.laddr and c.laddr.port == int(port) and c.raddr:
                peers.append("%s:%s" % (c.raddr.ip, c.raddr.port))
    except Exception:
        pass
    return peers


def process_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        p = psutil.Process(int(pid))
        return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
    except Exception:
        return False


def read_tail(path: str | Path, lines: int = 200) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return "[日志不存在] %s" % p
        size = p.stat().st_size
        with p.open("rb") as f:
            if size > 700_000:
                f.seek(size - 700_000)
            data = f.read()
        text = strip_ansi(_decode(data))
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        parts = text.split("\n")
        return "\n".join(parts[-max(20, int(lines)):])
    except Exception as e:
        return "[无法读取日志] %s" % e


def _clean_path(line: str) -> str:
    """过滤 wsl.exe 错误输出混进路径列表的情况。"""
    s = (line or "").strip().strip("\x00").strip()
    if not s.startswith("/") or any(ord(ch) < 32 for ch in s):
        return ""
    if "\ufffd" in s or "拒绝" in s or "denied" in s.lower():
        return ""
    return s


# ---------------------------------------------------------------------------
# WSL
# ---------------------------------------------------------------------------
class WSL:
    def __init__(self, st: Settings):
        self.st = st
        self.exe = self._find_exe()
        self._gw = ""
        self._gw_at = 0.0
        self._probe_cache: dict = {}
        self._probe_at = 0.0
        self._lock = threading.RLock()

    @staticmethod
    def _find_exe() -> str:
        for cand in (
            os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "wsl.exe"),
            r"C:\Windows\System32\wsl.exe",
        ):
            if os.path.exists(cand):
                return cand
        import shutil

        return shutil.which("wsl") or "wsl.exe"

    def _env(self) -> dict:
        env = dict(os.environ)
        env["WSL_UTF8"] = "1"
        env["PYTHONUTF8"] = "1"
        return env

    def run(self, script: str, timeout: float = 20, input_data: bytes | None = None):
        cmd = [
            self.exe,
            "-d",
            self.st.wsl_distro,
            "-u",
            "root",
            "--",
            "bash",
            "-lc",
            script,
        ]
        try:
            return run_hidden(
                cmd, timeout=timeout, input_data=input_data, env=self._env()
            )
        except subprocess.TimeoutExpired as e:
            @dataclass
            class R:
                returncode: int = -9
                stdout: bytes = b""
                stderr: bytes = b""

            return R(stderr=("WSL 命令超时: %s" % e).encode())
        except Exception as e:
            @dataclass
            class R:
                returncode: int = -1
                stdout: bytes = b""
                stderr: bytes = b""

            return R(stderr=str(e).encode())

    def ok(self, timeout: float = 8) -> bool:
        return self.run("true", timeout=timeout).returncode == 0

    def text(self, script: str, timeout: float = 20) -> str:
        r = self.run(script, timeout=timeout)
        return _decode(r.stdout or b"").strip()

    def read(self, path: str, timeout: float = 15) -> str:
        r = self.run("cat -- %s 2>/dev/null" % shlex.quote(path), timeout=timeout)
        if r.returncode != 0:
            return ""
        return _decode(r.stdout or b"").strip()

    def write(self, path: str, data: str | bytes, timeout: float = 20) -> bool:
        if isinstance(data, str):
            data = data.encode("utf-8")
        script = "mkdir -p -- $(dirname %s) && cat > %s" % (
            shlex.quote(path),
            shlex.quote(path),
        )
        r = self.run(script, timeout=timeout, input_data=data)
        return r.returncode == 0

    def exists(self, path: str) -> bool:
        return self.run("test -e %s" % shlex.quote(path), timeout=8).returncode == 0

    def find(self, roots: str, name_expr: str, limit: int = 8, timeout: float = 15) -> list[str]:
        script = (
            "for d in %s; do [ -e \"$d\" ] && find \"$d\" -maxdepth 9 %s 2>/dev/null; done "
            "| head -n %d" % (roots, name_expr, int(limit))
        )
        out = self.text(script, timeout=timeout)
        return [x for x in (_clean_path(x) for x in out.splitlines()) if x]

    def gateway(self, force: bool = False) -> str:
        with self._lock:
            now = time.time()
            if not force and self._gw and now - self._gw_at < 20:
                return self._gw
            out = self.text(
                "ip route show default 2>/dev/null | awk '/default/{print $3; exit}'",
                timeout=8,
            )
            m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", out)
            self._gw = m.group(1) if m else ""
            self._gw_at = now
            return self._gw

    def ip(self) -> str:
        out = self.text("hostname -I 2>/dev/null | awk '{print $1}'", timeout=8)
        m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", out)
        return m.group(1) if m else ""

    def probe(self, qr_path: str, log_path: str, ttl: float = 4.0) -> dict:
        """一次 WSL 调用拿齐网关、NapCat PID、screen、二维码/日志时间。"""
        with self._lock:
            now = time.time()
            if self._probe_cache and now - self._probe_at < ttl:
                return dict(self._probe_cache)
            script = (
                "GW=$(ip route show default 2>/dev/null | awk '/default/{print $3; exit}'); "
                "PIDS=$(pgrep -f '[o]pt/QQ/qq' 2>/dev/null | tr '\\n' ','); "
                "SCREEN=$(command -v screen >/dev/null 2>&1 && screen -ls 2>/dev/null | grep -c 'napcat' || echo 0); "
                "QR=$(stat -c '%%Y %%s' %s 2>/dev/null || echo '0 0'); "
                "LOG=$(stat -c '%%Y %%s' %s 2>/dev/null || echo '0 0'); "
                'echo "GW=$GW"; echo "PIDS=$PIDS"; echo "SCREEN=$SCREEN"; '
                'echo "QR=$QR"; echo "LOG=$LOG"'
            ) % (shlex.quote(qr_path), shlex.quote(log_path))
            r = self.run(script, timeout=12)
            result = {
                "ok": r.returncode == 0,
                "gateway": "",
                "pids": [],
                "screen": False,
                "qr_mtime": 0.0,
                "qr_size": 0,
                "log_mtime": 0.0,
                "error": "",
            }
            if r.returncode != 0:
                result["error"] = strip_ansi(_decode(r.stderr or b"")).strip()
                self._probe_cache, self._probe_at = result, now
                return dict(result)
            for line in _decode(r.stdout or b"").splitlines():
                if line.startswith("GW="):
                    result["gateway"] = line[3:].strip()
                elif line.startswith("PIDS="):
                    result["pids"] = [
                        int(x) for x in line[5:].split(",") if x.strip().isdigit()
                    ]
                elif line.startswith("SCREEN="):
                    try:
                        result["screen"] = int(line[7:].strip() or 0) > 0
                    except Exception:
                        result["screen"] = False
                elif line.startswith("QR="):
                    bits = line[3:].strip().split()
                    if len(bits) >= 2:
                        try:
                            result["qr_mtime"] = float(bits[0])
                            result["qr_size"] = int(bits[1])
                        except Exception:
                            pass
                elif line.startswith("LOG="):
                    bits = line[4:].strip().split()
                    if bits:
                        try:
                            result["log_mtime"] = float(bits[0])
                        except Exception:
                            pass
            if result["gateway"]:
                self._gw = result["gateway"]
                self._gw_at = now
            self._probe_cache, self._probe_at = result, now
            return dict(result)

    def invalidate(self) -> None:
        with self._lock:
            self._probe_cache = {}
            self._probe_at = 0
            self._gw_at = 0


# ---------------------------------------------------------------------------
# NapCat WebUI（在 WSL 里监听 6099，Windows 通过 localhost 访问）
# ---------------------------------------------------------------------------
class WebUIError(Exception):
    pass


class WebUI:
    def __init__(self, backend: "Backend"):
        self.b = backend
        self.st = backend.st
        self.wsl = backend.wsl
        self._lock = threading.RLock()
        self._base = ""
        self._cred = ""
        self._cred_at = 0.0
        self._cfg = {}
        self._cfg_at = 0.0
        self._failed_at = 0.0
        self._last_error = ""
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    # -- 基础 HTTP ---------------------------------------------------------
    def _http(self, method: str, url: str, payload: dict | None, timeout: float):
        data = None
        headers = {"Accept": "application/json", "User-Agent": "DafeiyuConsole/2"}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self._cred:
            headers["Authorization"] = "Bearer " + self._cred
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=timeout) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            raise WebUIError("HTTP %s" % e.code)
        except Exception as e:
            raise WebUIError(str(e))
        try:
            obj = json.loads(raw.decode("utf-8", errors="replace"))
        except Exception:
            raise WebUIError("WebUI 返回了非 JSON 数据")
        if not isinstance(obj, dict):
            raise WebUIError("WebUI 返回格式异常")
        if int(obj.get("code", -1)) != 0:
            msg = str(obj.get("message") or "未知错误")
            if "Unauthorized" in msg or "Authorization" in msg:
                self._cred = ""
                self._cred_at = 0
            raise WebUIError(msg)
        return obj.get("data")

    def _read_cfg(self, force: bool = False) -> dict:
        with self._lock:
            now = time.time()
            if not force and self._cfg and now - self._cfg_at < 90:
                return dict(self._cfg)
            path = self.b.napcat.webui_file()
            raw = self.wsl.read(path, timeout=10) if path else ""
            if not raw:
                # NapCat 可能把 webui.json 放在别处，做一次轻量查找
                cands = self.wsl.find(
                    self.st.napcat_home, "-iname 'webui.json' -path '*napcat*'", limit=3
                )
                if cands:
                    self.b.napcat.set_webui_file(cands[0])
                    raw = self.wsl.read(cands[0], timeout=10)
            if not raw:
                raise WebUIError("找不到 NapCat WebUI 配置（WSL 可能未启动）")
            if not raw.lstrip().startswith("{"):
                raise WebUIError("读取 webui.json 失败（WSL 不可用或权限不足）")
            try:
                cfg = json.loads(raw)
            except Exception:
                raise WebUIError("webui.json 格式异常")
            if cfg.get("disableWebUI"):
                raise WebUIError("NapCat WebUI 已被禁用")
            self._cfg = cfg
            self._cfg_at = now
            return dict(cfg)

    def _candidates(self, port: int) -> Iterable[str]:
        yield "http://127.0.0.1:%d" % port
        yield "http://localhost:%d" % port
        yield "http://[::1]:%d" % port
        ip = self.wsl.ip()
        if ip:
            yield "http://%s:%d" % (ip, port)

    def _auth(self, force_cfg: bool = False):
        with self._lock:
            if self._cred and time.time() - self._cred_at < 3000:
                return
            cfg = self._read_cfg(force=force_cfg or not self._cfg)
            token = str(cfg.get("token") or "")
            if not token:
                raise WebUIError("WebUI token 为空")
            port = int(cfg.get("port") or self.st.webui_port)
            digest = hashlib.sha256((token + ".napcat").encode("utf-8")).hexdigest()
            last = ""
            for base in self._candidates(port):
                try:
                    data = self._http(
                        "POST", base + "/api/auth/login", {"hash": digest}, 1.8
                    )
                    cred = str((data or {}).get("Credential") or "")
                    if not cred:
                        if (data or {}).get("require2FA"):
                            raise WebUIError("WebUI 开启了 2FA，暂不支持自动登录")
                        raise WebUIError("WebUI 登录未返回凭证")
                    self._base = base
                    self._cred = cred
                    self._cred_at = time.time()
                    self._failed_at = 0
                    self._last_error = ""
                    return
                except Exception as e:
                    last = str(e)
                    continue
            self._failed_at = time.time()
            self._last_error = last or "WebUI 无法连接"
            raise WebUIError(self._last_error)

    def call(self, path: str, payload: dict | None = None, timeout: float = 3.0):
        with self._lock:
            try:
                self._auth()
            except WebUIError as e:
                raise
            url = self._base + path
            try:
                return self._http("POST", url, payload or {}, timeout)
            except WebUIError as e:
                # 凭证过期或 NapCat 重启后 token 变化：重新认证一次
                if "Unauthorized" in str(e) or "Authorization" in str(e):
                    self._cred = ""
                    self._cred_at = 0
                    self._auth(force_cfg=True)
                    return self._http("POST", self._base + path, payload or {}, timeout)
                raise

    # -- 业务 API ----------------------------------------------------------
    def available(self) -> bool:
        try:
            self._auth()
            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    def last_error(self) -> str:
        return self._last_error or ""

    def check_login(self) -> dict:
        data = self.call("/api/QQLogin/CheckLoginStatus", {})
        return data if isinstance(data, dict) else {}

    def login_info(self) -> dict:
        data = self.call("/api/QQLogin/GetQQLoginInfo", {})
        return data if isinstance(data, dict) else {}

    def quick_login_list(self) -> list[str]:
        data = self.call("/api/QQLogin/GetQuickLoginList")
        if isinstance(data, list):
            return [str(x) for x in data]
        return []

    def set_quick_login(self, uin: str) -> None:
        self.call("/api/QQLogin/SetQuickLogin", {"uin": str(uin)}, timeout=8)

    def set_auto_login(self, uin: str) -> None:
        try:
            self.call("/api/QQLogin/SetQuickLoginQQ", {"uin": str(uin)}, timeout=5)
        except Exception:
            pass

    def get_qr(self) -> dict:
        data = self.call("/api/QQLogin/GetQQLoginQrcode", {})
        return data if isinstance(data, dict) else {}

    def refresh_qr(self) -> dict:
        data = self.call("/api/QQLogin/RefreshQRcode", {}, timeout=8)
        return data if isinstance(data, dict) else {}

    def restart(self) -> None:
        self.call("/api/QQLogin/RestartNapCat", {}, timeout=12)

    def ob11_config(self) -> dict:
        data = self.call("/api/OB11Config/GetConfig", {}, timeout=5)
        return data if isinstance(data, dict) else {}

    def set_ob11_config(self, cfg: dict) -> None:
        self.call("/api/OB11Config/SetConfig", cfg, timeout=6)


# ---------------------------------------------------------------------------
# AstrBot
# ---------------------------------------------------------------------------
class AstrBot:
    def __init__(self, backend: "Backend"):
        self.b = backend
        self.st = backend.st

    @property
    def cfg_path(self) -> Path:
        return Path(self.st.astrbot_cwd) / "data" / "cmd_config.json"

    def read_cfg(self) -> dict:
        p = self.cfg_path
        if not p.exists():
            raise FileNotFoundError("AstrBot 配置不存在: %s" % p)
        return json.loads(p.read_text(encoding="utf-8-sig"))

    def write_cfg(self, cfg: dict) -> None:
        p = self.cfg_path
        backup = p.with_suffix(".json.console.bak")
        try:
            if p.exists() and not backup.exists():
                backup.write_bytes(p.read_bytes())
        except Exception:
            pass
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, p)

    def existing_token(self) -> str:
        """只读地取当前 AstrBot 的 OneBot token，避免状态轮询写配置。"""
        try:
            cfg = self.read_cfg()
        except Exception:
            return ""
        for p in cfg.get("platform") or []:
            if isinstance(p, dict) and p.get("type") == "aiocqhttp":
                return str(p.get("ws_reverse_token") or "").strip()
        return ""

    def ensure_platform(self) -> tuple[str, bool, str]:
        """确保 aiocqhttp 平台开启，返回 (token, changed, error)。"""
        try:
            cfg = self.read_cfg()
        except Exception as e:
            return self.st.onebot_token, False, str(e)
        platforms = cfg.get("platform")
        if not isinstance(platforms, list):
            platforms = []
            cfg["platform"] = platforms
        entry = None
        for p in platforms:
            if isinstance(p, dict) and p.get("type") == "aiocqhttp":
                entry = p
                break
        token = str((entry or {}).get("ws_reverse_token") or "").strip()
        if not token:
            token = self.st.onebot_token.strip()
        if not token:
            token_file = Path(self.st.astrbot_cwd) / "ws_token.txt"
            try:
                if token_file.exists():
                    token = token_file.read_text(encoding="utf-8-sig").strip()
            except Exception:
                token = ""
        if not token:
            token = secrets.token_hex(16)

        changed = False
        if entry is None:
            entry = {
                "id": "napcat",
                "type": "aiocqhttp",
                "enable": True,
                "ws_reverse_host": "0.0.0.0",
                "ws_reverse_port": int(self.st.onebot_port),
                "ws_reverse_token": token,
            }
            platforms.append(entry)
            changed = True
        else:
            desired = {
                "enable": True,
                "ws_reverse_host": "0.0.0.0",
                "ws_reverse_port": int(self.st.onebot_port),
                "ws_reverse_token": token,
            }
            for k, v in desired.items():
                if entry.get(k) != v:
                    entry[k] = v
                    changed = True
        if changed:
            try:
                self.write_cfg(cfg)
            except Exception as e:
                return token, False, "写入 AstrBot 配置失败: %s" % e
        return token, changed, ""

    def running(self) -> bool:
        return port_open(self.st.dashboard_port)

    def pid(self) -> int | None:
        pids = listening_pids(self.st.dashboard_port)
        return pids[0] if pids else None

    @staticmethod
    def looks_like_astrbot(pid: int | None) -> bool:
        if not pid:
            return False
        try:
            cmd = " ".join(psutil.Process(int(pid)).cmdline()).lower()
        except Exception:
            return True  # 拿不到命令行时不阻止停止，避免误判导致关不掉
        if not cmd:
            return True
        return "astrbot" in cmd

    def start(self, progress: Progress = _noop) -> dict:
        if self.running():
            pid = self.pid()
            if pid and not self.looks_like_astrbot(pid):
                return {
                    "ok": False,
                    "msg": "端口 %d 被其他程序占用，不是 AstrBot" % self.st.dashboard_port,
                }
            return {"ok": True, "msg": "AstrBot 已在运行", "pid": pid}
        exe = Path(self.st.astrbot_exe)
        if not exe.exists():
            return {"ok": False, "msg": "找不到 AstrBot: %s" % exe}
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if ASTRBOT_LOG.exists():
                old = ASTRBOT_LOG.with_suffix(".log.old")
                if old.exists():
                    old.unlink(missing_ok=True)
                os.replace(ASTRBOT_LOG, old)
        except Exception:
            pass
        logf = None
        try:
            logf = open(ASTRBOT_LOG, "ab", buffering=0)
            env = dict(os.environ)
            env.update(
                {
                    "PYTHONUTF8": "1",
                    "PYTHONIOENCODING": "utf-8",
                    "PYTHONLEGACYWINDOWSSTDIO": "0",
                    "PYTHONUNBUFFERED": "1",
                    "NO_COLOR": "1",
                    "CLICOLOR": "0",
                    "TERM": "dumb",
                }
            )
            proc = subprocess.Popen(
                [str(exe), "run", "--port", str(self.st.dashboard_port)],
                cwd=self.st.astrbot_cwd,
                stdin=subprocess.DEVNULL,
                stdout=logf,
                stderr=subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
                startupinfo=_startupinfo(),
                env=env,
                close_fds=True,
            )
            try:
                (LOG_DIR / "console-astrbot.pid").write_text(
                    str(proc.pid), encoding="ascii"
                )
            except Exception:
                pass
        except Exception as e:
            return {"ok": False, "msg": "启动 AstrBot 失败: %s" % e}
        finally:
            if logf is not None:
                logf.close()

        deadline = time.time() + 70
        started = time.time()
        while time.time() < deadline:
            if port_open(self.st.dashboard_port):
                progress(38, "AstrBot 面板已就绪")
                return {
                    "ok": True,
                    "msg": "AstrBot 已启动 (pid %s)" % proc.pid,
                    "pid": proc.pid,
                }
            if proc.poll() is not None and time.time() - started > 10:
                tail = read_tail(ASTRBOT_LOG, 40)
                return {
                    "ok": False,
                    "msg": "AstrBot 启动后退出，日志：\n" + tail[-1200:],
                }
            time.sleep(0.5)
        return {"ok": False, "msg": "AstrBot 启动超时，请看 AstrBot 日志"}

    def stop(self) -> dict:
        pids: list[int] = []
        port_pid = self.pid()
        if port_pid:
            pids.append(port_pid)
        try:
            raw = (LOG_DIR / "console-astrbot.pid").read_text().strip()
            if raw.isdigit() and process_alive(int(raw)):
                if int(raw) not in pids:
                    pids.append(int(raw))
        except Exception:
            pass
        if not pids:
            return {"ok": True, "msg": "AstrBot 未在运行"}
        if port_pid and not self.looks_like_astrbot(port_pid):
            return {
                "ok": False,
                "msg": "端口 %d 被其他程序占用，未执行停止" % self.st.dashboard_port,
            }
        # 先杀端口对应的真实进程（它可能已经被 uv trampoline 重新挂到别的父进程下），
        # 再清理启动器 PID。taskkill 在部分受限环境下会 Access denied，这里用 psutil。
        for pid in list(pids):
            try:
                p = psutil.Process(pid)
            except Exception:
                continue
            try:
                for child in p.children(recursive=True):
                    try:
                        child.kill()
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                p.kill()
            except Exception:
                pass
        for _ in range(40):
            if not port_open(self.st.dashboard_port):
                try:
                    (LOG_DIR / "console-astrbot.pid").unlink(missing_ok=True)
                except Exception:
                    pass
                return {"ok": True, "msg": "AstrBot 已停止"}
            time.sleep(0.25)
        # 再补一刀：重新找端口 PID
        late = self.pid()
        if late and late not in pids:
            try:
                psutil.Process(late).kill()
            except Exception:
                pass
            for _ in range(16):
                if not port_open(self.st.dashboard_port):
                    return {"ok": True, "msg": "AstrBot 已停止"}
                time.sleep(0.25)
        return {"ok": False, "msg": "AstrBot 停止超时（可能仍在退出）"}


# ---------------------------------------------------------------------------
# NapCat（WSL）
# ---------------------------------------------------------------------------
class NapCat:
    def __init__(self, backend: "Backend"):
        self.b = backend
        self.st = backend.st
        self.wsl = backend.wsl
        self._layout: dict = {}
        self._webui_file = ""
        self._lock = threading.RLock()

    # -- 路径发现 ----------------------------------------------------------
    def discover(self, force: bool = False) -> dict:
        with self._lock:
            if self._layout and not force:
                return dict(self._layout)
            home = self.st.napcat_home.rstrip("/")
            qq = self.st.napcat_qq
            cfg = home + "/opt/QQ/resources/app/app_launcher/napcat/config"
            qr = home + "/opt/QQ/resources/app/app_launcher/napcat/cache/qrcode.png"
            log = self.st.napcat_log

            def ok_paths() -> bool:
                return bool(self.wsl.exists(qq)) and bool(self.wsl.exists(cfg))

            if not ok_paths():
                found_cfg = self.wsl.find(
                    home + " /opt /root",
                    "-type d -path '*app_launcher/napcat/config'",
                    limit=4,
                )
                if found_cfg:
                    cfg = found_cfg[0].rstrip("/")
                    base = cfg[: -len("/config")] if cfg.endswith("/config") else cfg
                    home_guess = base.split("/opt/QQ/")[0] or home
                    home = home_guess
                    qr = base + "/cache/qrcode.png"
                found_qq = self.wsl.find(
                    "/root /opt /home", "-type f -name qq -path '*QQ*'", limit=5
                )
                if found_qq:
                    qq = found_qq[0]
            layout = {
                "home": home,
                "qq": qq,
                "config_dir": cfg,
                "qr": qr,
                "log": log,
                "webui": cfg + "/webui.json",
            }
            self._layout = layout
            return dict(layout)

    def set_webui_file(self, path: str) -> None:
        self._webui_file = path

    def webui_file(self) -> str:
        if self._webui_file:
            return self._webui_file
        try:
            return self.discover()["webui"]
        except Exception:
            return self.st.napcat_config_dir + "/webui.json"

    # -- 状态 --------------------------------------------------------------
    def probe(self, ttl: float = 4.0) -> dict:
        layout = self.discover()
        return self.wsl.probe(layout["qr"], layout["log"], ttl=ttl)

    def pids(self) -> list[int]:
        return list(self.probe(ttl=3).get("pids") or [])

    def running(self) -> bool:
        return bool(self.pids())

    def read_log(self, lines: int = 200) -> str:
        layout = self.discover()
        out = self.wsl.text(
            "tail -n %d -- %s 2>/dev/null" % (max(20, int(lines)), shlex.quote(layout["log"])),
            timeout=15,
        )
        if not out:
            return "(NapCat 日志为空)"
        return strip_ansi(out)

    def read_qq_log(self, lines: int = 200) -> str:
        layout = self.discover()
        out = self.wsl.text(
            "grep -E '发送 ->|接收 <-' -- %s 2>/dev/null | tail -n %d"
            % (shlex.quote(layout["log"]), max(20, int(lines))),
            timeout=15,
        )
        return strip_ansi(out) if out else "(暂无 QQ 会话)"

    def read_qr_file(self) -> dict:
        layout = self.discover()
        qr = shlex.quote(layout["qr"])
        r = self.wsl.run(
            "if [ -f %s ]; then stat -c '%%Y' %s; base64 -w0 %s; fi" % (qr, qr, qr),
            timeout=15,
        )
        if r.returncode != 0:
            return {}
        text = _decode(r.stdout or b"").strip()
        if not text:
            return {}
        lines = text.splitlines()
        mtime = 0.0
        try:
            mtime = float(lines[0].strip())
        except Exception:
            pass
        b64 = "".join(lines[1:]).strip()
        if not b64:
            return {}
        try:
            raw = base64.b64decode(b64)
        except Exception:
            return {}
        if not raw.startswith(b"\x89PNG"):
            return {}
        return {"png": raw, "mtime": mtime}

    # -- OneBot 配置 -------------------------------------------------------
    def onebot_files(self) -> list[str]:
        cfg = self.discover()["config_dir"]
        out = self.wsl.text(
            "find %s -maxdepth 2 -iname '*onebot11*.json' -type f 2>/dev/null"
            % shlex.quote(cfg),
            timeout=12,
        )
        files = [x for x in (_clean_path(v) for v in out.splitlines()) if x]
        if not files:
            legacy = cfg + "/onebot11.json"
            if self.wsl.exists(legacy):
                files = [legacy]
        return sorted(set(files))

    @staticmethod
    def _patch_cfg_obj(cfg: dict, gateway: str, port: int, token: str) -> bool:
        changed = False
        network = cfg.setdefault("network", {})
        clients = network.get("websocketClients")
        if not isinstance(clients, list):
            clients = []
            network["websocketClients"] = clients
        target = None
        for c in clients:
            if isinstance(c, dict) and str(c.get("name", "")).lower() in (
                "astrbot",
                "dafeiyu",
            ):
                target = c
                break
        if target is None and clients:
            target = clients[0]
        if target is None:
            target = {
                "name": "astrbot",
                "enable": True,
                "url": "ws://%s:%d/ws" % (gateway, port),
                "messagePostFormat": "array",
                "reportSelfMessage": False,
                "reconnectInterval": 3000,
                "token": token,
                "debug": False,
                "heartInterval": 30000,
            }
            clients.append(target)
            changed = True
        desired = {
            "enable": True,
            "url": "ws://%s:%d/ws" % (gateway, port),
            "token": token,
            "reconnectInterval": 3000,
            "heartInterval": 30000,
        }
        for k, v in desired.items():
            if target.get(k) != v:
                target[k] = v
                changed = True
        return changed

    def ensure_onebot(self, gateway: str, token: str) -> dict:
        if not gateway:
            return {"ok": False, "changed": False, "msg": "拿不到 WSL 网关 IP"}
        cfg_dir = self.discover()["config_dir"]
        files = self.onebot_files()
        if not files:
            path = cfg_dir + "/onebot11.json"
            cfg = {
                "network": {
                    "httpServers": [],
                    "httpSseServers": [],
                    "httpClients": [],
                    "websocketServers": [],
                    "websocketClients": [],
                    "plugins": [],
                },
                "musicSignUrl": "",
                "enableLocalFile2Url": False,
                "parseMultMsg": False,
                "imageDownloadProxy": "",
            }
            if self._patch_cfg_obj(cfg, gateway, self.st.onebot_port, token):
                if self.wsl.write(
                    path, json.dumps(cfg, ensure_ascii=False, indent=2)
                ):
                    return {
                        "ok": True,
                        "changed": True,
                        "msg": "已创建 NapCat OneBot 配置",
                        "files": [path],
                    }
            return {"ok": False, "changed": False, "msg": "NapCat 配置文件不存在"}
        changed_files = []
        errors = []
        for f in files:
            raw = self.wsl.read(f)
            if not raw:
                continue
            try:
                cfg = json.loads(raw)
            except Exception as e:
                errors.append("%s: %s" % (f, e))
                continue
            if not self._patch_cfg_obj(cfg, gateway, self.st.onebot_port, token):
                continue
            try:
                self.wsl.run(
                    "cp -f -- %s %s.console.bak 2>/dev/null || true"
                    % (shlex.quote(f), shlex.quote(f)),
                    timeout=8,
                )
            except Exception:
                pass
            if self.wsl.write(f, json.dumps(cfg, ensure_ascii=False, indent=2)):
                changed_files.append(f)
            else:
                errors.append("写入失败: %s" % f)
        if changed_files:
            return {
                "ok": True,
                "changed": True,
                "msg": "已校准 NapCat 连接配置",
                "files": changed_files,
            }
        if errors:
            return {"ok": False, "changed": False, "msg": "; ".join(errors)}
        return {"ok": True, "changed": False, "msg": "NapCat 连接配置已是最新"}

    # -- 启停 --------------------------------------------------------------
    def start(self, progress: Progress = _noop) -> dict:
        layout = self.discover()
        if self.pids():
            return {
                "ok": True,
                "msg": "NapCat 已在运行",
                "pids": self.pids(),
                "already": True,
            }
        qq = layout["qq"]
        log = layout["log"]
        script = r"""
set +e
Q=%(qq)s
L=%(log)s
export Q L
pkill -f '[o]pt/QQ/qq' >/dev/null 2>&1
pkill -f 'Xvfb :99' >/dev/null 2>&1
sleep 0.4
screen -S napcat -X quit >/dev/null 2>&1
screen -wipe >/dev/null 2>&1
: > "$L"
if command -v Xvfb >/dev/null 2>&1; then
  nohup Xvfb :99 -screen 0 1440x900x24 >/root/napcat-xvfb.log 2>&1 &
  sleep 1
fi
if command -v screen >/dev/null 2>&1; then
  if pgrep -f 'Xvfb :99' >/dev/null 2>&1; then
    screen -dmS napcat bash -c 'DISPLAY=:99 exec "$Q" --no-sandbox >> "$L" 2>&1'
  else
    screen -dmS napcat bash -c 'exec xvfb-run -a "$Q" --no-sandbox >> "$L" 2>&1'
  fi
else
  if pgrep -f 'Xvfb :99' >/dev/null 2>&1; then
    nohup env DISPLAY=:99 "$Q" --no-sandbox >> "$L" 2>&1 &
  else
    nohup xvfb-run -a "$Q" --no-sandbox >> "$L" 2>&1 &
  fi
fi
sleep 0.6
pgrep -f '[o]pt/QQ/qq' | tr '\n' ' '
""" % {"qq": shlex.quote(qq), "log": shlex.quote(log)}
        progress(58, "正在拉起 NapCat 网关")
        r = self.wsl.run(script, timeout=35)
        out = _decode(r.stdout or b"").strip()
        pids = [int(x) for x in out.split() if x.isdigit()]
        if not pids:
            # 再等一会儿：Linux QQ 在部分机器上启动较慢
            deadline = time.time() + 35
            while time.time() < deadline:
                pids = self.pids()
                if pids:
                    break
                time.sleep(0.8)
        if not pids:
            tail = self.read_log(60)
            return {
                "ok": False,
                "msg": "NapCat 启动失败，日志：\n" + tail[-1500:],
                "pids": [],
            }
        self.wsl.invalidate()
        progress(66, "NapCat 进程已拉起")
        return {"ok": True, "msg": "NapCat 已启动", "pids": pids}

    def stop(self) -> dict:
        layout = self.discover()
        script = r"""
Q=%(qq)s
export Q
screen -S napcat -X quit >/dev/null 2>&1
pkill -f '[o]pt/QQ/qq' >/dev/null 2>&1
sleep 1
pkill -f 'Xvfb :99' >/dev/null 2>&1
pkill -f "xvfb-run -a $Q" >/dev/null 2>&1
sleep 0.4
pgrep -f '[o]pt/QQ/qq' | tr '\n' ' '
""" % {"qq": shlex.quote(layout["qq"])}
        self.wsl.run(script, timeout=18)
        self.wsl.invalidate()
        for _ in range(20):
            if not self.pids():
                return {"ok": True, "msg": "NapCat 已停止"}
            time.sleep(0.35)
        return {"ok": False, "msg": "NapCat 仍在退出中"}


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
class Backend:
    def __init__(self, st: Settings):
        self.st = st
        self.wsl = WSL(st)
        self.astrbot = AstrBot(self)
        self.napcat = NapCat(self)
        self.webui = WebUI(self)
        self._lock = threading.RLock()
        self._action_lock = threading.Lock()
        self._webui_state = {}
        self._webui_state_at = 0.0
        self._webui_checked_at = 0.0
        self._status_cache = {}
        self._status_at = 0.0
        self._token = ""
        self.desired_running = False
        self._last_repair_at = 0.0
        self._last_quick_at = 0.0
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    # -- 事件日志 ----------------------------------------------------------
    def event(self, msg: str) -> None:
        line = "[%s] %s\n" % (time.strftime("%H:%M:%S"), msg)
        try:
            with self._lock:
                with EVENT_LOG.open("a", encoding="utf-8") as f:
                    f.write(line)
                if EVENT_LOG.stat().st_size > 300_000:
                    text = EVENT_LOG.read_text(encoding="utf-8", errors="replace")
                    EVENT_LOG.write_text("\n".join(text.splitlines()[-800:]) + "\n", encoding="utf-8")
        except Exception:
            pass

    def token(self) -> str:
        if not self._token:
            self._token = self.astrbot.existing_token() or self.st.onebot_token
        return self._token

    # -- WebUI 状态 --------------------------------------------------------
    def _webui_status(self, ttl: float = 2.0, force: bool = False) -> dict:
        with self._lock:
            now = time.time()
            if not force and self._webui_state and now - self._webui_state_at < ttl:
                return dict(self._webui_state)
            if not force and now - self._webui_checked_at < 8 and self._webui_state.get("error"):
                return dict(self._webui_state)
            result = {
                "ok": False,
                "error": "",
                "isLogin": False,
                "online": False,
                "phase": "",
                "qrLoginAccepted": False,
                "qrcodeurl": "",
                "loginError": "",
                "uin": "",
                "avatarUrl": "",
                "quick": [],
            }
            try:
                st = self.webui.check_login()
                result.update(
                    {
                        "ok": True,
                        "isLogin": bool(st.get("isLogin")),
                        "online": bool(st.get("isLogin"))
                        and not bool(st.get("isOffline")),
                        "phase": str(st.get("loginPhase") or ""),
                        "qrLoginAccepted": bool(st.get("qrLoginAccepted")),
                        "qrcodeurl": str(st.get("qrcodeurl") or ""),
                        "loginError": str(st.get("loginError") or ""),
                    }
                )
                try:
                    info = self.webui.login_info()
                    uin = info.get("uin")
                    if uin:
                        result["uin"] = str(uin)
                    result["avatarUrl"] = str(info.get("avatarUrl") or "")
                    if "online" in info:
                        result["online"] = bool(info.get("online"))
                except Exception:
                    pass
                if not result["isLogin"]:
                    try:
                        result["quick"] = self.webui.quick_login_list()
                    except Exception:
                        pass
            except Exception as e:
                result["error"] = str(e)
            self._webui_state = result
            self._webui_state_at = time.time()
            self._webui_checked_at = self._webui_state_at
            return dict(result)

    # -- 状态 --------------------------------------------------------------
    def status(self) -> dict:
        now = time.time()
        with self._lock:
            if self._status_cache and now - self._status_at < 1.2:
                return json.loads(json.dumps(self._status_cache))
        a_running = self.astrbot.running()
        a_pid = self.astrbot.pid() if a_running else None
        onebot_listen = port_open(self.st.onebot_port)
        peers = established_peers(self.st.onebot_port)
        probe = {}
        layout = {}
        try:
            layout = self.napcat.discover()
            probe = self.napcat.probe(ttl=4)
        except Exception as e:
            probe = {"error": str(e), "pids": [], "gateway": ""}
        n_pids = list(probe.get("pids") or [])
        gateway = probe.get("gateway") or self.wsl.gateway()
        n_running = bool(n_pids) or bool(probe.get("screen"))
        wstate = {}
        webui_port_open = port_open(self.st.webui_port)
        if n_running or webui_port_open:
            # NapCat 没跑时不访问 WebUI，避免无谓的等待
            wstate = self._webui_status(ttl=2.0)
        logged_in = bool(wstate.get("isLogin")) or bool(peers)
        online = bool(wstate.get("online")) if wstate.get("ok") else logged_in
        linked = bool(peers)
        if wstate.get("ok") and wstate.get("isLogin") and not online:
            level, text = "warn", "QQ 已离线"
        elif wstate.get("ok") and wstate.get("isLogin") and not linked:
            level, text = "warn", "QQ 已登录，通道未连接"
        elif not a_running and not n_running:
            level, text = "idle", "服务已停止"
        elif not a_running:
            level, text = "bad", "AstrBot 未运行"
        elif not n_running:
            level, text = "bad", "NapCat 未运行"
        elif not logged_in:
            level, text = "warn", "QQ 待登录"
        elif not linked:
            level, text = "warn", "等待 OneBot 连接"
        else:
            level, text = "ok", "运行正常"

        phase_map = {
            "ready": "已就绪",
            "waiting_qrcode": "等待扫码",
            "qrcode_scanned": "已扫码，等待确认",
            "generating_qrcode": "生成二维码",
            "initializing": "初始化中",
            "offline": "离线",
            "reconnecting": "重连中",
        }
        result = {
            "astrbot": {
                "running": a_running,
                "pid": a_pid,
                "port": self.st.dashboard_port,
                "url": "http://127.0.0.1:%d" % self.st.dashboard_port,
            },
            "napcat": {
                "running": n_running,
                "pids": n_pids,
                "screen": bool(probe.get("screen")),
                "gateway": gateway,
                "webui": bool(wstate.get("ok")),
                "webui_error": wstate.get("error", ""),
                "qr_mtime": probe.get("qr_mtime", 0.0),
                "layout": layout,
            },
            "qq": {
                "logged_in": logged_in,
                "online": online,
                "linked": linked,
                "peers": peers,
                "phase": wstate.get("phase", ""),
                "phase_text": phase_map.get(wstate.get("phase", ""), wstate.get("phase", "")),
                "qr_accepted": bool(wstate.get("qrLoginAccepted")),
                "login_error": wstate.get("loginError", ""),
                "account": wstate.get("uin") or self.st.account,
                "quick_ready": (
                    str(self.st.account) in [str(x) for x in (wstate.get("quick") or [])]
                    if wstate.get("quick")
                    else None
                ),
            },
            "onebot": {
                "listening": onebot_listen,
                "port": self.st.onebot_port,
                "clients": len(peers),
                "token_set": bool(self.token()),
            },
            "health": {"level": level, "text": text},
            "desired_running": self.desired_running,
            "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": now,
        }
        with self._lock:
            self._status_cache = result
            self._status_at = now
        return json.loads(json.dumps(result))

    # -- 启动流程 ----------------------------------------------------------
    def start_all(self, progress: Progress = _noop) -> dict:
        if not self._action_lock.acquire(timeout=2):
            return {"ok": False, "msg": "已有启动任务在进行"}
        try:
            self.event("开始一键启动")
            progress(3, "检查运行环境")
            if not self.wsl.ok():
                msg = (
                    "WSL 无法访问（%s）。请确认 WSL 已启动，"
                    "或在设置中换一个发行版。" % self.st.wsl_distro
                )
                self.event(msg)
                return {"ok": False, "msg": msg, "needs_qr": False}

            progress(10, "校准 AstrBot 的 OneBot 平台")
            token, changed, err = self.astrbot.ensure_platform()
            if err:
                self.event("AstrBot 配置: " + err)
                return {"ok": False, "msg": "AstrBot 配置异常: " + err}
            self._token = token
            if self.st.onebot_token != token:
                self.st.onebot_token = token
                self.st.save()
            if changed and self.astrbot.running():
                self.event("AstrBot 平台配置有更新，正在重启 AstrBot")
                progress(15, "重启 AstrBot 以应用配置")
                self.astrbot.stop()

            progress(20, "启动 AstrBot")
            a = self.astrbot.start(progress)
            self.event("AstrBot: " + a["msg"].splitlines()[0])
            if not a.get("ok"):
                return {"ok": False, "msg": a.get("msg", "AstrBot 启动失败"), "needs_qr": False}

            progress(42, "等待 OneBot 服务监听")
            deadline = time.time() + 25
            while time.time() < deadline and not port_open(self.st.onebot_port):
                time.sleep(0.4)
            if not port_open(self.st.onebot_port):
                # 常见原因：平台没启用/被别的配置覆盖，重启一次再试
                self.event("OneBot 6199 未监听，重启 AstrBot")
                progress(46, "OneBot 未监听，重启 AstrBot")
                self.astrbot.stop()
                a = self.astrbot.start(progress)
                if not a.get("ok"):
                    return {"ok": False, "msg": a.get("msg", "AstrBot 重启失败"), "needs_qr": False}
                deadline = time.time() + 25
                while time.time() < deadline and not port_open(self.st.onebot_port):
                    time.sleep(0.4)

            progress(50, "读取 WSL 网关并校准 NapCat")
            gateway = self.wsl.gateway(force=True)
            for _ in range(5):
                if gateway:
                    break
                time.sleep(1)
                gateway = self.wsl.gateway(force=True)
            if not gateway:
                return {"ok": False, "msg": "无法获取 WSL 网关 IP，请检查 WSL 网络", "needs_qr": False}
            patch = self.napcat.ensure_onebot(gateway, token)
            self.event("NapCat 配置: " + patch.get("msg", ""))
            if not patch.get("ok"):
                return {"ok": False, "msg": patch.get("msg", "NapCat 配置失败"), "needs_qr": False}

            progress(58, "启动 NapCat 网关")
            n = self.napcat.start(progress)
            self.event("NapCat: " + n["msg"].splitlines()[0])
            if not n.get("ok"):
                return {"ok": False, "msg": n.get("msg", "NapCat 启动失败"), "needs_qr": False}

            progress(70, "等待 NapCat WebUI 就绪")
            deadline = time.time() + 75
            while time.time() < deadline:
                if self.webui.available():
                    break
                time.sleep(1.0)
            webui_ok = self.webui.available()

            if webui_ok:
                progress(78, "尝试快速登录 QQ")
                q = self.try_quick_login(progress)
                self.event("快速登录: " + q.get("msg", ""))
                progress(86, "检查 QQ 登录与反向连接")
                try:
                    st = self.webui.check_login()
                    logged = bool(st.get("isLogin"))
                except Exception:
                    logged = False
            else:
                logged = False
                progress(86, "检查 QQ 登录状态")

            linked = False
            deadline = time.time() + (40 if logged else 15)
            while time.time() < deadline:
                if established_peers(self.st.onebot_port):
                    linked = True
                    break
                time.sleep(0.7)

            if logged and not linked:
                progress(90, "QQ 已登录，正在修复 OneBot 连接")
                self.event("QQ 已登录但反向连接未建立，尝试重启 NapCat 重载配置")
                self.napcat.stop()
                time.sleep(1)
                self.napcat.start(progress)
                deadline = time.time() + 35
                while time.time() < deadline:
                    if established_peers(self.st.onebot_port):
                        linked = True
                        break
                    time.sleep(0.8)

            needs_qr = not logged
            qr_payload = None
            if needs_qr:
                progress(95, "获取二维码")
                try:
                    qr_payload = self.get_qr()
                except Exception as e:
                    qr_payload = {"error": str(e)}

            self.desired_running = True
            progress(100, "启动完成")
            if linked:
                msg = "已全部启动，QQ 与 AstrBot 已连通"
            elif logged:
                msg = "QQ 已登录，但反向连接仍未建立，请查看诊断"
            elif needs_qr:
                msg = "服务已启动，还需要扫码登录 QQ"
            else:
                msg = "启动完成，状态待确认"
            self.event(msg)
            self.wsl.invalidate()
            self._webui_state = {}
            status = self.status()
            return {
                "ok": bool(linked or logged),
                "msg": msg,
                "needs_qr": needs_qr,
                "qr": qr_payload,
                "status": status,
            }
        except Exception as e:
            self.event("启动异常: %s" % e)
            return {"ok": False, "msg": "启动异常: %s" % e, "needs_qr": False}
        finally:
            self._action_lock.release()

    def stop_all(self) -> dict:
        self.desired_running = False
        self.event("停止全部服务")
        n = self.napcat.stop()
        a = self.astrbot.stop()
        self.wsl.invalidate()
        self._webui_state = {}
        return {"ok": a.get("ok") and n.get("ok"), "msg": a["msg"] + " | " + n["msg"]}

    def restart_napcat(self) -> dict:
        self.event("重启 NapCat")
        s = self.napcat.stop()
        if not s.get("ok"):
            return s
        r = self.napcat.start()
        self._webui_state = {}
        return r

    # -- 快速登录 ----------------------------------------------------------
    def try_quick_login(self, progress: Progress = _noop) -> dict:
        if not self.st.quick_login:
            return {"ok": False, "skipped": True, "msg": "已关闭快速登录"}
        if not str(self.st.account).isdigit():
            return {"ok": False, "msg": "账号格式不正确"}
        try:
            st = self.webui.check_login()
        except Exception as e:
            return {"ok": False, "msg": "WebUI 不可用: %s" % e}
        if st.get("isLogin"):
            return {"ok": True, "msg": "QQ 已登录"}
        if st.get("loginPhase") in ("generating_qrcode", "reconnecting"):
            time.sleep(1.0)
        try:
            self.webui.set_quick_login(str(self.st.account))
        except Exception as e:
            return {"ok": False, "msg": "快速登录失败: %s" % e}
        deadline = time.time() + 12
        while time.time() < deadline:
            try:
                if self.webui.check_login().get("isLogin"):
                    self.webui.set_auto_login(str(self.st.account))
                    self._last_quick_at = time.time()
                    return {"ok": True, "msg": "快速登录成功"}
            except Exception:
                pass
            time.sleep(1.0)
        return {
            "ok": False,
            "msg": "没有可用的登录凭证，需要扫码一次（之后就能免扫码）",
        }

    # -- 二维码 ------------------------------------------------------------
    @staticmethod
    def _qr_matrix(url: str) -> list[list[bool]]:
        try:
            import qrcode

            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=1,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            return [[bool(cell) for cell in row] for row in qr.get_matrix()]
        except Exception:
            return []

    def get_qr(self, force_refresh: bool = False) -> dict:
        now = time.time()
        try:
            st = self.webui.check_login()
        except Exception as e:
            st = {}
            webui_err = str(e)
        else:
            webui_err = ""
        if st.get("isLogin"):
            return {"logged_in": True, "phase": st.get("loginPhase", "")}
        url = str(st.get("qrcodeurl") or "")
        if force_refresh:
            old = url
            try:
                r = self.webui.refresh_qr()
                url = str((r or {}).get("qrcodeurl") or url)
            except Exception as e:
                webui_err = str(e)
            # QQ 刷新二维码是异步的：最多等 4 秒拿新 URL
            deadline = time.time() + 4
            while time.time() < deadline:
                try:
                    st2 = self.webui.check_login()
                except Exception:
                    break
                new = str(st2.get("qrcodeurl") or "")
                if new and new != old:
                    st = st2
                    url = new
                    break
                time.sleep(0.5)
        if not url and not webui_err:
            try:
                data = self.webui.get_qr()
                url = str((data or {}).get("qrcode") or "")
            except Exception as e:
                webui_err = str(e)
        if url:
            if url.startswith("data:image"):
                try:
                    head, body = url.split(",", 1)
                    png = base64.b64decode(body)
                    if png.startswith(b"\x89PNG"):
                        return {
                            "source": "webui_data",
                            "png": png,
                            "fetched_at": now,
                            "expires_in": 120,
                            "phase": st.get("loginPhase", ""),
                            "accepted": bool(st.get("qrLoginAccepted")),
                        }
                except Exception:
                    pass
            matrix = self._qr_matrix(url)
            if matrix:
                return {
                    "source": "webui",
                    "url": url,
                    "matrix": matrix,
                    "fetched_at": now,
                    "expires_in": 120,
                    "phase": st.get("loginPhase", ""),
                    "accepted": bool(st.get("qrLoginAccepted")),
                }
            return {"source": "webui_url_only", "url": url, "fetched_at": now, "expires_in": 120}
        # 兜底：读取 NapCat 缓存的二维码图片
        try:
            f = self.napcat.read_qr_file()
            if f.get("png"):
                age = max(0, now - float(f.get("mtime") or now))
                return {
                    "source": "file",
                    "png": f["png"],
                    "mtime": f.get("mtime", 0),
                    "age": age,
                    "stale": age > 110,
                    "expires_in": max(0, 120 - age),
                    "phase": st.get("loginPhase", ""),
                    "error": webui_err,
                }
        except Exception as e:
            webui_err = (webui_err + " / " + str(e)).strip(" /")
        return {
            "error": webui_err or "暂时拿不到二维码，请稍后再试",
            "phase": st.get("loginPhase", ""),
        }

    def check_login(self) -> dict:
        return self._webui_status(ttl=0.3, force=True)

    # -- 日志 --------------------------------------------------------------
    def read_log(self, target: str, lines: int | None = None) -> str:
        n = int(lines or self.st.log_lines)
        if target == "console":
            return read_tail(EVENT_LOG, n)
        if target == "astrbot":
            path = ASTRBOT_LOG
            if not path.exists() or path.stat().st_size == 0:
                path = ASTRBOT_FALLBACK_LOG
            return read_tail(path, n)
        if target == "napcat":
            try:
                return self.napcat.read_log(n)
            except Exception as e:
                return "[读取 NapCat 日志失败] %s" % e
        if target == "qq":
            try:
                return self.napcat.read_qq_log(n)
            except Exception as e:
                return "[读取 QQ 会话失败] %s" % e
        return ""

    # -- 诊断 --------------------------------------------------------------
    def _firewall_rule_name(self) -> str:
        return "Dafeiyu OneBot %d" % int(self.st.onebot_port)

    def _firewall_rule_exists(self) -> bool:
        if sys.platform != "win32":
            return False
        netsh = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "netsh.exe")
        try:
            r = run_hidden(
                [
                    netsh,
                    "advfirewall",
                    "firewall",
                    "show",
                    "rule",
                    "name=%s" % self._firewall_rule_name(),
                ],
                timeout=12,
            )
            return self._firewall_rule_name() in _decode(r.stdout or b"")
        except Exception:
            return False

    def allow_firewall(self) -> dict:
        """通过 UAC 放行 TCP 6199 入站（只加一条命名规则）。"""
        if sys.platform != "win32":
            return {"ok": False, "msg": "仅支持 Windows"}
        if self._firewall_rule_exists():
            return {"ok": True, "msg": "6199 入站规则已存在"}
        netsh = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "netsh.exe")
        args = (
            'advfirewall firewall add rule name="%s" dir=in action=allow '
            "protocol=TCP localport=%d profile=any"
            % (self._firewall_rule_name(), int(self.st.onebot_port))
        )
        try:
            rc = int(
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", netsh, args, None, 1
                )
            )
        except Exception as e:
            return {"ok": False, "msg": "无法发起管理员提权: %s" % e}
        if rc <= 32:
            return {"ok": False, "msg": "UAC 被取消或提权失败（code %d）" % rc}
        for _ in range(20):
            if self._firewall_rule_exists():
                self.event("已放行 Windows 防火墙 TCP %d" % self.st.onebot_port)
                return {"ok": True, "msg": "已放行 TCP %d 入站" % self.st.onebot_port}
            time.sleep(0.5)
        return {"ok": False, "msg": "未检测到防火墙规则，可能取消了 UAC"}

    def diagnose(self) -> list[dict]:
        items: list[dict] = []

        def add(name, ok, detail="", hint=""):
            items.append({"name": name, "ok": bool(ok), "detail": detail, "hint": hint})

        exe = Path(self.st.astrbot_exe)
        add("AstrBot 程序", exe.exists(), str(exe), "在设置里改成 astrbot.exe 的实际路径")
        wsl_ok = self.wsl.ok()
        add("WSL 发行版", wsl_ok, self.st.wsl_distro, "确认 WSL 已安装并能 `wsl -l -v`")
        layout = {}
        if wsl_ok:
            try:
                layout = self.napcat.discover(force=True)
            except Exception as e:
                layout = {}
                add("NapCat 路径", False, str(e), "检查 NapCat 是否装在 WSL 的 /root/Napcat")
            if layout:
                add(
                    "NapCat QQ 程序",
                    self.wsl.exists(layout["qq"]),
                    layout["qq"],
                    "检查 napcat_home / napcat_qq 设置",
                )
                add(
                    "NapCat 配置目录",
                    self.wsl.exists(layout["config_dir"]),
                    layout["config_dir"],
                    "启动过一次 NapCat 后会自动生成",
                )
        a = self.astrbot.running()
        add("AstrBot 面板 (:%d)" % self.st.dashboard_port, a, "端口监听" if a else "未监听")
        ob = port_open(self.st.onebot_port)
        add("OneBot 服务 (:%d)" % self.st.onebot_port, ob, "端口监听" if ob else "未监听", "AstrBot 平台需启用 aiocqhttp")
        probe = {}
        if wsl_ok:
            try:
                probe = self.napcat.probe(ttl=0)
            except Exception as e:
                probe = {"error": str(e)}
        nrun = bool(probe.get("pids"))
        add("NapCat 进程", nrun, "PID " + ",".join(map(str, probe.get("pids") or [])) if nrun else "未运行")
        gw = probe.get("gateway") or ""
        add("WSL 网关", bool(gw), gw, "WSL 网络异常时重启 WSL")
        w = self._webui_status(ttl=0, force=True)
        add("NapCat WebUI (:%d)" % self.st.webui_port, w.get("ok"), w.get("error") or "已连接", "WebUI 被禁用或端口被占用")
        add("QQ 登录", w.get("isLogin"), w.get("phase") or w.get("loginError", ""), "点「扫码登录」")
        peers = established_peers(self.st.onebot_port)
        add("反向 WS 连接", bool(peers), ", ".join(peers) or "未建立", "会自动重启 NapCat 重载配置")
        if wsl_ok and layout and ob:
            files = self.napcat.onebot_files()
            token = self.token()
            matched = False
            detail = "未找到 onebot11 配置"
            for f in files:
                raw = self.wsl.read(f)
                try:
                    cfg = json.loads(raw)
                except Exception:
                    continue
                for c in (cfg.get("network", {}).get("websocketClients") or []):
                    url = str(c.get("url", ""))
                    if str(self.st.onebot_port) in url and str(c.get("token", "")) == token:
                        matched = True
                        detail = f + " → " + url
            add("OneBot 配置匹配", matched, detail, "一键启动会自动校准")
        if wsl_ok and ob and not peers and layout:
            test = self.wsl.text(
                "timeout 3 bash -c 'cat < /dev/null > /dev/tcp/%s/%d' >/dev/null 2>&1 && echo OPEN || echo CLOSED"
                % (gw or "127.0.0.1", self.st.onebot_port),
                timeout=8,
            )
            add(
                "WSL → Windows 6199",
                "OPEN" in test,
                "可达" if "OPEN" in test else "不可达",
                "可能是 Windows 防火墙拦截；允许 TCP 6199 入站",
            )
        return items

    def open_dashboard_url(self) -> str:
        return "http://127.0.0.1:%d" % self.st.dashboard_port
