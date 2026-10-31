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
        self._closed = False

    @property
    def busy(self) -> bool:
        return self._busy or self._stopping

    def _submit(self, fn) -> bool:
        if self._closed:
            return False
        try:
            self.pool.submit(fn)
            return True
        except RuntimeError:
            # 退出流程中线程池已关闭，静默忽略
            self._closed = True
            return False

    # -- 基础任务 ----------------------------------------------------------
    def refresh_status(self):
        if self._closed or self._polling:
            return
        self._polling = True

        def job():
            try:
                s = self.backend.status()
            except Exception:
                s = None
            finally:
                self._polling = False
            if s and not self._closed:
                self.status_ready.emit(s)

        if not self._submit(job):
            self._polling = False

    def start_all(self):
        if self._closed or self._busy or self._stopping:
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
                if not self._closed:
                    self.status_ready.emit(self.backend.status())
            except Exception:
                pass

        if not self._submit(job):
            self._busy = False

    def stop_all(self):
        if self._closed or self._stopping:
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
            if not self._closed:
                self.status_ready.emit(self.backend.status())

        if not self._submit(job):
            self._stopping = False

    def restart_napcat(self):
        if self._closed or self._busy or self._stopping:
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
            if not self._closed:
                self.status_ready.emit(self.backend.status())

        if not self._submit(job):
            self._busy = False

    # -- 二维码 / 登录 -----------------------------------------------------
    def fetch_qr(self, force: bool = False):
        if self._closed:
            return

        def job():
            try:
                data = self.backend.get_qr(force_refresh=force)
            except Exception as e:
                data = {"error": "获取二维码失败: %s" % e}
            if not self._closed:
                self.qr_ready.emit(data)

        self._submit(job)

    def check_login(self):
        if self._closed:
            return

        def job():
            try:
                data = self.backend.check_login()
            except Exception as e:
                data = {"ok": False, "error": str(e)}
            if not self._closed:
                self.login_state.emit(data)

        self._submit(job)

    def quick_login(self):
        if self._closed:
            return

        def job():
            try:
                res = self.backend.try_quick_login()
            except Exception as e:
                res = {"ok": False, "msg": str(e)}
            if self._closed:
                return
            self.toast.emit(res.get("msg", ""), not res.get("ok"))
            if not self._closed:
                self.status_ready.emit(self.backend.status())

        self._submit(job)

    # -- 日志 / 诊断 -------------------------------------------------------
    def read_log(self, target: str):
        if self._closed:
            return

        def job():
            try:
                text = self.backend.read_log(target)
            except Exception as e:
                text = "[读取失败] %s" % e
            if not self._closed:
                self.log_ready.emit(target, text)

        self._submit(job)

    def diagnose(self):
        if self._closed:
            return

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
            if not self._closed:
                self.diag_ready.emit(items)

        self._submit(job)

    def allow_firewall(self):
        if self._closed:
            return

        def job():
            try:
                res = self.backend.allow_firewall()
            except Exception as e:
                res = {"ok": False, "msg": "放行失败: %s" % e}
            if self._closed:
                return
            self.toast.emit(res.get("msg", ""), not res.get("ok"))
            try:
                if not self._closed:
                    self.diag_ready.emit(self.backend.diagnose())
            except Exception:
                pass

        self._submit(job)

    # -- 设置 --------------------------------------------------------------
    def save_settings(self, st: Settings):
        if self._closed:
            return
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
        self._closed = True
        try:
            self.pool.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
