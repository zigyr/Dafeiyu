# -*- coding: utf-8 -*-
"""把阻塞的后端调用放到线程池，通过 Qt 信号回主线程。"""
from __future__ import annotations

import webbrowser
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from PySide6.QtCore import QObject, Signal

from core import Backend
from settings import Settings


class Service(QObject):
    status_ready = Signal(dict)
    progress = Signal(int, str)
    action_done = Signal(dict)
    stop_done = Signal(dict)
    qr_ready = Signal(dict)
    log_ready = Signal(str, str)
    diag_ready = Signal(list)
    login_state = Signal(dict)
    toast = Signal(str, bool)

    def __init__(self, st: Settings, parent=None):
        super().__init__(parent)
        self.st = st
        self.backend = Backend(st)
        self.pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="dafeiyu")
        self._polling = False
        self._busy = False
        self._stopping = False

    @property
    def busy(self) -> bool:
        return self._busy or self._stopping

    # -- 基础任务 ----------------------------------------------------------
    def refresh_status(self):
        if self._polling:
            return
        self._polling = True

        def job():
            try:
                s = self.backend.status()
            except Exception:
                s = None
            finally:
                self._polling = False
            if s:
                self.status_ready.emit(s)

        self.pool.submit(job)

    def start_all(self):
        if self._busy or self._stopping:
            return
        self._busy = True

        def job():
            try:
                res = self.backend.start_all(lambda p, m: self.progress.emit(p, m))
            except Exception as e:
                res = {"ok": False, "msg": "启动异常: %s" % e, "needs_qr": False}
            finally:
                self._busy = False
            try:
                self.action_done.emit(res)
                self.status_ready.emit(self.backend.status())
            except Exception:
                pass

        self.pool.submit(job)

    def stop_all(self):
        if self._stopping:
            return
        self._stopping = True

        def job():
            try:
                res = self.backend.stop_all()
            except Exception as e:
                res = {"ok": False, "msg": "停止异常: %s" % e}
            finally:
                self._stopping = False
            self.stop_done.emit(res)
            self.status_ready.emit(self.backend.status())

        self.pool.submit(job)

    def restart_napcat(self):
        if self._busy or self._stopping:
            return
        self._busy = True

        def job():
            try:
                res = self.backend.restart_napcat()
            except Exception as e:
                res = {"ok": False, "msg": "重启 NapCat 失败: %s" % e}
            finally:
                self._busy = False
            self.action_done.emit(res)
            self.status_ready.emit(self.backend.status())

        self.pool.submit(job)

    # -- 二维码 / 登录 -----------------------------------------------------
    def fetch_qr(self, force: bool = False):
        def job():
            try:
                data = self.backend.get_qr(force_refresh=force)
            except Exception as e:
                data = {"error": "获取二维码失败: %s" % e}
            self.qr_ready.emit(data)

        self.pool.submit(job)

    def check_login(self):
        def job():
            try:
                data = self.backend.check_login()
            except Exception as e:
                data = {"ok": False, "error": str(e)}
            self.login_state.emit(data)

        self.pool.submit(job)

    def quick_login(self):
        def job():
            try:
                res = self.backend.try_quick_login()
            except Exception as e:
                res = {"ok": False, "msg": str(e)}
            self.toast.emit(res.get("msg", ""), not res.get("ok"))
            self.status_ready.emit(self.backend.status())

        self.pool.submit(job)

    # -- 日志 / 诊断 -------------------------------------------------------
    def read_log(self, target: str):
        def job():
            try:
                text = self.backend.read_log(target)
            except Exception as e:
                text = "[读取失败] %s" % e
            self.log_ready.emit(target, text)

        self.pool.submit(job)

    def diagnose(self):
        def job():
            try:
                items = self.backend.diagnose()
            except Exception as e:
                items = [
                    {
                        "name": "诊断失败",
                        "ok": False,
                        "detail": str(e),
                        "hint": "请查看控制台事件日志",
                    }
                ]
            self.diag_ready.emit(items)

        self.pool.submit(job)

    # -- 设置 --------------------------------------------------------------
    def save_settings(self, st: Settings):
        st.save()
        self.st = st
        self.backend = Backend(st)
        self.status_ready.emit(self.backend.status())

    def apply_settings(self, st: Settings):
        self.save_settings(st)

    def open_dashboard(self):
        webbrowser.open("http://127.0.0.1:%d" % self.st.dashboard_port)

    def open_logs(self):
        try:
            import os

            import core

            os.startfile(str(core.LOG_DIR))
        except Exception:
            pass

    def shutdown(self):
        try:
            self.pool.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
