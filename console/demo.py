# -*- coding: utf-8 -*-
"""演示模式：没有 WSL 时也能预览完整界面。"""
from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer, Signal

from core import Backend
from settings import Settings


def demo_status(kind: str = "running") -> dict:
    st = Settings.load()
    now = time.time()
    base = {
        "astrbot": {"running": False, "pid": None, "port": 6185, "url": "http://127.0.0.1:6185"},
        "napcat": {
            "running": False,
            "pids": [],
            "screen": False,
            "gateway": "",
            "webui": False,
            "webui_error": "",
            "qr_mtime": 0.0,
            "layout": {},
        },
        "qq": {
            "logged_in": False,
            "online": False,
            "linked": False,
            "peers": [],
            "phase": "",
            "phase_text": "",
            "qr_accepted": False,
            "login_error": "",
            "account": st.account,
            "quick_ready": None,
        },
        "onebot": {"listening": False, "port": 6199, "clients": 0, "token_set": True},
        "health": {"level": "idle", "text": "服务已停止"},
        "desired_running": False,
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": now,
    }
    if kind == "idle":
        return base
    base["astrbot"] = {"running": True, "pid": 43212, "port": 6185, "url": "http://127.0.0.1:6185"}
    base["napcat"] = {
        "running": True,
        "pids": [22764, 22788],
        "screen": True,
        "gateway": "172.27.48.1",
        "webui": True,
        "webui_error": "",
        "qr_mtime": now - 8,
        "layout": {},
    }
    base["onebot"] = {"listening": True, "port": 6199, "clients": 0, "token_set": True}
    if kind == "warn":
        base["qq"] = {
            "logged_in": False,
            "online": False,
            "linked": False,
            "peers": [],
            "phase": "waiting_qrcode",
            "phase_text": "等待扫码",
            "qr_accepted": False,
            "login_error": "",
            "account": st.account,
            "quick_ready": True,
        }
        base["health"] = {"level": "warn", "text": "QQ 待登录"}
        return base
    if kind == "partial":
        base["napcat"] = {
            "running": False,
            "pids": [],
            "screen": False,
            "gateway": "172.27.48.1",
            "webui": False,
            "webui_error": "",
            "qr_mtime": 0,
            "layout": {},
        }
        base["onebot"] = {"listening": True, "port": 6199, "clients": 0, "token_set": True}
        base["health"] = {"level": "bad", "text": "NapCat 未运行"}
        return base
    base["qq"] = {
        "logged_in": True,
        "online": True,
        "linked": True,
        "peers": ["172.27.57.199:49216"],
        "phase": "ready",
        "phase_text": "已就绪",
        "qr_accepted": False,
        "login_error": "",
        "account": st.account,
        "quick_ready": True,
    }
    base["onebot"] = {"listening": True, "port": 6199, "clients": 1, "token_set": True}
    base["health"] = {"level": "ok", "text": "运行正常"}
    base["desired_running"] = True
    return base


class DemoService(QObject):
    status_ready = Signal(dict)
    progress = Signal(int, str)
    action_done = Signal(dict)
    stop_done = Signal(dict)
    qr_ready = Signal(dict)
    log_ready = Signal(str, str)
    diag_ready = Signal(list)
    login_state = Signal(dict)
    toast = Signal(str, bool)

    def __init__(self, kind: str = "running", parent=None):
        super().__init__(parent)
        self.st = Settings.load()
        self.kind = kind
        self.status = demo_status(kind)
        self._busy = False
        self._seq = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next_step)

    @property
    def busy(self):
        return self._busy

    def refresh_status(self):
        self.status_ready.emit(self.status)

    def start_all(self):
        if self._busy:
            return
        self._busy = True
        self._seq = [
            (8, "检查运行环境"),
            (18, "启动 AstrBot"),
            (38, "AstrBot 面板已就绪"),
            (50, "读取 WSL 网关并校准 NapCat"),
            (60, "正在拉起 NapCat 网关"),
            (76, "等待 NapCat WebUI 就绪"),
            (86, "快速登录 QQ"),
            (96, "检查 QQ 登录与反向连接"),
            (100, "启动完成"),
        ]
        self._timer.start(420)

    def _next_step(self):
        if not self._seq:
            self._timer.stop()
            self._busy = False
            self.status = demo_status("running" if self.kind != "warn" else "warn")
            self.action_done.emit(
                {"ok": True, "msg": "已全部启动，QQ 与 AstrBot 已连通", "needs_qr": False}
            )
            self.status_ready.emit(self.status)
            return
        pct, msg = self._seq.pop(0)
        self.progress.emit(pct, msg)

    def stop_all(self):
        self.status = demo_status("idle")
        self.stop_done.emit({"ok": True, "msg": "已停止"})
        self.status_ready.emit(self.status)

    def restart_napcat(self):
        self.toast.emit("NapCat 已重启", False)

    def fetch_qr(self, force: bool = False):
        matrix = Backend._qr_matrix("https://qrcode.example.invalid/qq-login?uin=2960405592&t=%d" % time.time())
        self.qr_ready.emit(
            {
                "source": "demo",
                "url": "demo",
                "matrix": matrix,
                "fetched_at": time.time(),
                "expires_in": 120,
                "phase": "waiting_qrcode",
            }
        )

    def check_login(self):
        self.login_state.emit(
            {
                "ok": True,
                "isLogin": self.status["qq"]["logged_in"],
                "phase": self.status["qq"]["phase"],
                "qrLoginAccepted": False,
                "error": "",
            }
        )

    def read_log(self, target: str):
        samples = {
            "console": "21:30:02 开始一键启动\n21:30:05 AstrBot 已启动 (pid 43212)\n21:30:08 已校准 NapCat 连接配置\n21:30:18 NapCat 已启动\n21:30:26 QQ 快速登录成功\n21:30:28 反向 WS 已连接 · 一切就绪",
            "astrbot": "21:30:05 [Core] [INFO] AstrBot v4.29.3\n21:30:06 [Core] [INFO] Loading IM platform adapter aiocqhttp(napcat) ...\n21:30:07 [Core] [INFO] Starting WebUI at http://0.0.0.0:6185\n21:30:27 [Core] [INFO] aiocqhttp(OneBot v11) 反向连接成功。\n21:30:28 [Core] [INFO] AstrBot started.",
            "napcat": "21:30:18 [NapCat] [WebUi] WebUi Token: ********\n21:30:19 [NapCat] [Core] NapCat.Core Version: 4.x\n21:30:24 [Core] [Login] 正在快速登录 2960405592\n21:30:26 [Core] [Login] 登录成功\n21:30:27 [OneBot] WebSocket Client Connected",
            "qq": "21:30:29 发送 -> [好友] 2721400746: 晚上好呀\n21:30:31 接收 <- [好友] 2721400746: 今天过得怎么样？",
        }
        self.log_ready.emit(target, samples.get(target, ""))

    def diagnose(self):
        self.diag_ready.emit(
            [
                {"name": "AstrBot 程序", "ok": True, "detail": "astrbot.exe", "hint": ""},
                {"name": "WSL 发行版", "ok": True, "detail": "kali-linux", "hint": ""},
                {"name": "OneBot 服务 (:6199)", "ok": True, "detail": "端口监听", "hint": ""},
                {"name": "NapCat 进程", "ok": True, "detail": "PID 22764,22788", "hint": ""},
                {"name": "QQ 登录", "ok": True, "detail": "ready", "hint": ""},
                {"name": "反向 WS 连接", "ok": True, "detail": "172.27.57.199:49216", "hint": ""},
            ]
        )

    def quick_login(self):
        self.toast.emit("快速登录成功", False)

    def allow_firewall(self):
        self.toast.emit("演示模式：已模拟放行 TCP 6199", False)
        self.diagnose()

    def save_settings(self, st: Settings):
        self.st = st
        st.save()
        self.toast.emit("设置已保存", False)

    def apply_settings(self, st: Settings):
        self.save_settings(st)

    def open_dashboard(self):
        pass

    def open_logs(self):
        pass

    def shutdown(self):
        pass

    def __getattr__(self, name):
        # 让 Demo 模式也能访问 backend 的一些属性
        raise AttributeError(name)
