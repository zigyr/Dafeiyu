# -*- coding: utf-8 -*-
"""大肥鱼控制台 - 配置管理（纯标准库）。"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent
SETTINGS_PATH = APP_DIR / "settings.json"

AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_VALUE = "DafeiyuConsole"


@dataclass
class Settings:
    # 账号与登录
    account: str = "2960405592"
    quick_login: bool = True

    # 运行环境
    wsl_distro: str = "kali-linux"
    astrbot_exe: str = r"C:\Users\zigyr\.local\bin\astrbot.exe"
    astrbot_cwd: str = str(ROOT / "astrbot")
    napcat_home: str = "/root/Napcat"
    napcat_qq: str = "/root/Napcat/opt/QQ/qq"
    napcat_log: str = "/root/napcat-run.log"
    dashboard_port: int = 6185
    onebot_port: int = 6199
    webui_port: int = 6099

    # 行为
    minimize_to_tray: bool = True
    auto_heal: bool = True
    autostart: bool = False
    start_services_on_launch: bool = False
    log_lines: int = 220

    # 运行期缓存（不展示给用户）
    onebot_token: str = ""

    @classmethod
    def load(cls) -> "Settings":
        data = {}
        try:
            if SETTINGS_PATH.exists():
                data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
        except Exception:
            try:
                SETTINGS_PATH.replace(SETTINGS_PATH.with_suffix(".bad.json"))
            except Exception:
                pass
            data = {}
        known = {f.name for f in fields(cls)}
        clean = {k: v for k, v in (data or {}).items() if k in known}
        obj = cls(**clean)
        obj.normalize()
        return obj

    def normalize(self) -> None:
        self.account = str(self.account or "").strip()
        self.wsl_distro = (self.wsl_distro or "kali-linux").strip()
        self.astrbot_cwd = str(self.astrbot_cwd or (ROOT / "astrbot"))
        self.napcat_home = (self.napcat_home or "/root/Napcat").rstrip("/")
        try:
            self.dashboard_port = int(self.dashboard_port)
            self.onebot_port = int(self.onebot_port)
            self.webui_port = int(self.webui_port)
            self.log_lines = max(60, min(2000, int(self.log_lines)))
        except Exception:
            self.dashboard_port, self.onebot_port, self.webui_port = 6185, 6199, 6099
            self.log_lines = 220
        if not self.napcat_qq:
            self.napcat_qq = self.napcat_home + "/opt/QQ/qq"
        if not self.napcat_log:
            self.napcat_log = "/root/napcat-run.log"
        self.onebot_token = str(self.onebot_token or "").strip()

    def save(self) -> None:
        self.normalize()
        tmp = SETTINGS_PATH.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(asdict(self), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp, SETTINGS_PATH)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

    # ---------- 路径推导 ----------
    @property
    def napcat_config_dir(self) -> str:
        return self.napcat_home + "/opt/QQ/resources/app/app_launcher/napcat/config"

    @property
    def napcat_qr(self) -> str:
        return self.napcat_home + "/opt/QQ/resources/app/app_launcher/napcat/cache/qrcode.png"

    # ---------- 开机自启 ----------
    @staticmethod
    def _pythonw() -> str:
        exe = Path(sys.executable)
        if exe.name.lower() == "python.exe":
            cand = exe.with_name("pythonw.exe")
            if cand.exists():
                return str(cand)
        return str(exe)

    @staticmethod
    def _app_script() -> str:
        return str(APP_DIR / "app.py")

    @classmethod
    def autostart_enabled(cls) -> bool:
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY) as key:
                winreg.QueryValueEx(key, AUTOSTART_VALUE)
            return True
        except Exception:
            return False

    @classmethod
    def apply_autostart(cls, enabled: bool) -> bool:
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE
            ) as key:
                if enabled:
                    cmd = '"%s" "%s" --minimized' % (cls._pythonw(), cls._app_script())
                    winreg.SetValueEx(key, AUTOSTART_VALUE, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(key, AUTOSTART_VALUE)
                    except FileNotFoundError:
                        pass
            return True
        except Exception:
            return False


def settings() -> Settings:
    return Settings.load()
