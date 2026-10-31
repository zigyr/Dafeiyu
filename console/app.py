# -*- coding: utf-8 -*-
"""
大肥鱼控制台入口。
- 正常启动：无控制台窗口，展示 Qt 界面，关闭时收进托盘。
- --minimized：直接驻留托盘。
- --demo：用演示数据预览界面。
- --screenshot PATH [--state running|idle|warn|partial]：离屏截图（调试用）。
"""
from __future__ import annotations

import argparse
import ctypes
import os
import sys
import threading
import time
import traceback
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
ROOT = APP_DIR.parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

from PySide6.QtCore import QCoreApplication, QLocale, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QHostAddress, QTcpServer, QTcpSocket
from PySide6.QtWidgets import QApplication

import theme

SINGLE_NAME = "DafeiyuConsole.v2"
SINGLE_PORT = 6197


def _log_error(text: str) -> None:
    try:
        with (LOG_DIR / "console-error.log").open("a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), text))
    except Exception:
        pass


def _excepthook(exc_type, exc, tb):
    _log_error("".join(traceback.format_exception(exc_type, exc, tb)))
    sys.__excepthook__(exc_type, exc, tb)


def _thread_excepthook(args):
    _log_error(
        "线程 %s 异常:\n%s"
        % (getattr(args.thread, "name", "?"), "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))
    )


sys.excepthook = _excepthook
try:
    threading.excepthook = _thread_excepthook
except Exception:
    pass


def _set_app_id():
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Dafeiyu.Console.2")
        except Exception:
            pass


def _notify_existing() -> bool:
    # 用本机 TCP 而不是命名管道：部分受限环境 / 安全软件会拦截 named pipe。
    sock = QTcpSocket()
    sock.connectToHost(QHostAddress.LocalHost, SINGLE_PORT)
    if sock.waitForConnected(300):
        sock.write(b"show\n")
        sock.waitForBytesWritten(300)
        sock.disconnectFromHost()
        return True
    return False


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--minimized", action="store_true", help="启动后只驻留托盘")
    parser.add_argument("--demo", action="store_true", help="演示模式")
    parser.add_argument("--screenshot", default="", help="离屏截图输出路径")
    parser.add_argument(
        "--state",
        default="running",
        choices=["running", "idle", "warn", "partial"],
        help="截图使用的状态",
    )
    parser.add_argument(
        "--dialog",
        default="",
        choices=["", "qr", "settings", "diagnose"],
        help="截图指定弹窗",
    )
    args, _ = parser.parse_known_args(argv)

    _set_app_id()
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv[:1])
    app.setApplicationName("大肥鱼控制台")
    app.setApplicationDisplayName("大肥鱼控制台")
    app.setOrganizationName("Dafeiyu")
    app.setQuitOnLastWindowClosed(False)
    theme.apply_theme(app)

    # 截图模式允许开多个实例
    if not args.screenshot and _notify_existing():
        return 0

    from demo import DemoService, demo_status
    from settings import Settings
    from ui import MainWindow, app_icon

    app.setWindowIcon(app_icon())
    st = Settings.load()
    service = DemoService(args.state, parent=app) if (args.demo or args.screenshot) else None
    if service is None:
        from service import Service

        service = Service(st, parent=app)

    win = MainWindow(service, start_minimized=bool(args.minimized or args.screenshot))

    server = None
    if not args.screenshot:
        server = QTcpServer(win)
        if not server.listen(QHostAddress.LocalHost, SINGLE_PORT):
            _log_error("单实例服务监听失败: %s" % server.errorString())
        else:
            def on_new_connection():
                while server.hasPendingConnections():
                    sock = server.nextPendingConnection()
                    sock.waitForReadyRead(250)
                    try:
                        data = bytes(sock.readAll())
                    except Exception:
                        data = b""
                    if b"show" in data or not data:
                        QTimer.singleShot(0, win._show_window)
                    sock.disconnectFromHost()

            server.newConnection.connect(on_new_connection)

    # 截图
    if args.screenshot:
        out = Path(args.screenshot)
        out.parent.mkdir(parents=True, exist_ok=True)
        win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        win.show()
        win.setWindowOpacity(1.0)
        win.apply_status(demo_status(args.state))
        if args.dialog == "qr":
            from ui import QRDialog

            dlg = QRDialog(service, win)
            dlg.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
            dlg.show()
            service.fetch_qr(False)
            for _ in range(60):
                app.processEvents()
                time.sleep(0.02)
            dlg.grab().save(str(out))
        elif args.dialog == "settings":
            from settings import Settings as S
            from ui import SettingsDialog

            dlg = SettingsDialog(S.load(), win)
            dlg.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
            dlg.show()
            for _ in range(30):
                app.processEvents()
                time.sleep(0.02)
            dlg.grab().save(str(out))
        elif args.dialog == "diagnose":
            from ui import DiagnoseDialog

            dlg = DiagnoseDialog(service, win)
            dlg.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
            dlg.show()
            for _ in range(40):
                app.processEvents()
                time.sleep(0.02)
            dlg.grab().save(str(out))
        else:
            for _ in range(40):
                app.processEvents()
                time.sleep(0.02)
            win.grab().save(str(out))
        _log_error("截图已保存: %s" % out)
        return 0

    if args.minimized:
        win.hide()
    # 正常显示由 MainWindow._fade_in 负责
    if st.start_services_on_launch and not args.demo:
        QTimer.singleShot(1800, win._start_all)
    app.exec()
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    # 后台轮询线程可能还在等 WSL 命令；托盘程序直接退出，避免关不掉
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main())
