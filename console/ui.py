# -*- coding: utf-8 -*-
"""大肥鱼控制台 - 主界面与对话框。"""
from __future__ import annotations

import copy
import math
import os
import sys
import time
import webbrowser

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

import core
from demo import demo_status
from settings import Settings
from theme import (
    ACCENT,
    ACCENT_DEEP,
    AMBER,
    BG0,
    BG1,
    BG2,
    BLUE,
    CARD,
    CARD_HI,
    CORAL,
    DIM,
    FONT_NUM,
    GREEN,
    LINE,
    MUTED,
    RED,
    SKY,
    TEXT,
    TEXT_SOFT,
    font,
    mono_font,
    num_font,
    qcolor,
)
from widgets import (
    CardIcon,
    FishLogo,
    FooterBar,
    GlassCard,
    HeroCard,
    Icon,
    IconButton,
    LEVEL_COLOR,
    LoginBar,
    LogPanel,
    Pill,
    PrimaryButton,
    QRWidget,
    RecentEvents,
    SecondaryButton,
    StatCard,
    StatusDot,
    TabButton,
    TitleBar,
    Toast,
    ToggleSwitch,
    mix,
)


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def transparent_labels(root: QWidget) -> None:
    from widgets import make_labels_transparent

    make_labels_transparent(root)


def fish_pixmap(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 32.0
    bg = QRectF(1 * s, 1 * s, 30 * s, 30 * s)
    p.setBrush(qcolor("#07131E", 245))
    p.setPen(QPen(qcolor(ACCENT, 70), max(1.0, 1.2 * s)))
    p.drawRoundedRect(bg, 9 * s, 9 * s)
    r = QRectF(5 * s, 7 * s, 23 * s, 18 * s)
    g = QLinearGradient(r.topLeft(), r.bottomRight())
    g.setColorAt(0, qcolor(ACCENT))
    g.setColorAt(1, qcolor(SKY))
    body = QPainterPath()
    body.moveTo(r.x(), r.center().y())
    body.cubicTo(
        r.x() + r.width() * 0.24,
        r.y() + r.height() * 0.05,
        r.x() + r.width() * 0.72,
        r.y() + r.height() * 0.05,
        r.x() + r.width() * 0.90,
        r.center().y(),
    )
    body.cubicTo(
        r.x() + r.width() * 0.72,
        r.y() + r.height() * 0.95,
        r.x() + r.width() * 0.24,
        r.y() + r.height() * 0.95,
        r.x(),
        r.center().y(),
    )
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(g)
    p.drawPath(body)
    tail = QPainterPath()
    tail.moveTo(r.x() + 2 * s, r.center().y())
    tail.lineTo(r.x() - 3 * s, r.y() + 2 * s)
    tail.lineTo(r.x() - 3 * s, r.bottom() - 2 * s)
    tail.closeSubpath()
    p.setBrush(qcolor(ACCENT))
    p.drawPath(tail)
    p.setBrush(qcolor("#04121A"))
    p.drawEllipse(QPointF(r.x() + r.width() * 0.68, r.y() + r.height() * 0.42), 1.6 * s, 1.6 * s)
    p.end()
    return pm


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(fish_pixmap(size))
    return icon


def action_icon(name: str, color: str = TEXT_SOFT, size: int = 18) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    Icon.paint(p, name, QRectF(2, 2, size - 4, size - 4), qcolor(color), 1.5)
    p.end()
    return QIcon(pm)


def set_dwm_dark(widget: QWidget) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = int(widget.winId())
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        value = ctypes.c_int(2)
        try:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 背景
# ---------------------------------------------------------------------------
class Surface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(55)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        if not self.isVisible():
            return
        self._phase = (self._phase + 0.0035) % 1.0
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(14, 14, -14, -14)
        # 柔和外阴影
        for i in range(10, 0, -1):
            alpha = int(4 + 3 * (10 - i) / 10)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, alpha))
            p.drawRoundedRect(r.adjusted(-i, -i + 2, i, i + 2), 20 + i, 20 + i)

        path = QPainterPath()
        path.addRoundedRect(r, 20, 20)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0.0, qcolor("#0A1724"))
        g.setColorAt(0.45, qcolor("#08121D"))
        g.setColorAt(1.0, qcolor("#050B12"))
        p.fillPath(path, g)

        # 深海极光
        p.save()
        p.setClipPath(path)
        x1 = r.left() + r.width() * (0.18 + 0.04 * math.sin(self._phase * 2 * math.pi))
        y1 = r.top() + r.height() * 0.10
        g1 = QRadialGradient(QPointF(x1, y1), r.width() * 0.55)
        g1.setColorAt(0.0, qcolor(SKY, 20))
        g1.setColorAt(0.5, qcolor(BLUE, 7))
        g1.setColorAt(1.0, qcolor(BLUE, 0))
        p.setBrush(QBrush(g1))
        p.drawEllipse(QPointF(x1, y1), r.width() * 0.55, r.height() * 0.55)

        x2 = r.right() - r.width() * (0.12 + 0.03 * math.cos(self._phase * 2 * math.pi))
        y2 = r.bottom() - r.height() * 0.08
        g2 = QRadialGradient(QPointF(x2, y2), r.width() * 0.42)
        g2.setColorAt(0.0, qcolor(ACCENT, 13))
        g2.setColorAt(0.6, qcolor(ACCENT, 4))
        g2.setColorAt(1.0, qcolor(ACCENT, 0))
        p.setBrush(QBrush(g2))
        p.drawEllipse(QPointF(x2, y2), r.width() * 0.42, r.height() * 0.42)
        p.restore()

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(qcolor("#FFFFFF", 20), 1))
        p.drawPath(path)
        # 顶部高光
        p.setPen(QPen(qcolor("#FFFFFF", 9), 1))
        p.drawLine(QPointF(r.left() + 36, r.top() + 1), QPointF(r.right() - 36, r.top() + 1))


class RoundDialog(QDialog):
    def __init__(self, title: str, width: int, height: int, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Dialog
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle(title)
        self.setWindowIcon(app_icon())
        self.setFixedSize(width, height)
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 30, 34, 26)
        root.setSpacing(0)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.title_label = QLabel(title)
        self.title_label.setFont(font(18, 700))
        self.title_label.setStyleSheet("color: %s;" % TEXT)
        top.addWidget(self.title_label)
        top.addStretch(1)
        self.close_btn = IconButton("close", "关闭", size=30)
        self.close_btn.clicked.connect(self.reject)
        top.addWidget(self.close_btn)
        root.addLayout(top)
        root.addSpacing(16)
        self.body = QVBoxLayout()
        self.body.setSpacing(12)
        root.addLayout(self.body, 1)
        self._fade = None

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(10, 10, -10, -10)
        for i in range(8, 0, -1):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, int(6 + 3 * (8 - i) / 8)))
            p.drawRoundedRect(r.adjusted(-i, -i + 2, i, i + 2), 18 + i, 18 + i)
        path = QPainterPath()
        path.addRoundedRect(r, 18, 18)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, qcolor("#0C1B29"))
        g.setColorAt(1, qcolor("#07111B"))
        p.fillPath(path, g)
        p.setPen(QPen(qcolor("#FFFFFF", 22), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and e.position().y() < 90:
            handle = self.windowHandle()
            if handle:
                handle.startSystemMove()
                return
        super().mousePressEvent(e)

    def showEvent(self, e):
        super().showEvent(e)
        set_dwm_dark(self)
        parent = self.parentWidget()
        if parent is not None and parent.isVisible():
            center = parent.frameGeometry().center()
        else:
            center = QApplication.primaryScreen().availableGeometry().center()
        self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)
        transparent_labels(self)


class CountdownBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(5)
        self._ratio = 1.0
        self._color = ACCENT

    def set_ratio(self, ratio: float, color: str | None = None):
        self._ratio = max(0.0, min(1.0, ratio))
        if color:
            self._color = color
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0, 1, self.width(), 3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qcolor("#1A2D41"))
        p.drawRoundedRect(r, 1.5, 1.5)
        if self._ratio > 0:
            fg = QRectF(0, 1, self.width() * self._ratio, 3)
            g = QLinearGradient(fg.topLeft(), fg.topRight())
            g.setColorAt(0, qcolor(self._color))
            g.setColorAt(1, qcolor(SKY))
            p.setBrush(QBrush(g))
            p.drawRoundedRect(fg, 1.5, 1.5)


# ---------------------------------------------------------------------------
# 二维码
# ---------------------------------------------------------------------------
class QRDialog(RoundDialog):
    logged_in = Signal()

    def __init__(self, service, parent=None):
        super().__init__("扫码登录", 400, 566, parent)
        self.service = service
        self._remaining = 0
        self._auto_refreshed = False
        self._success = False
        self._opened_logged = False

        sub = QLabel("账号 %s · 仅首次登录需要扫码" % service.st.account)
        sub.setFont(font(11, 400))
        sub.setStyleSheet("color: %s;" % DIM)
        self.body.addWidget(sub, 0, Qt.AlignmentFlag.AlignHCenter)

        self.qr = QRWidget()
        self.qr.set_placeholder("正在获取二维码…")
        self.body.addWidget(self.qr, 0, Qt.AlignmentFlag.AlignHCenter)
        self.body.addSpacing(2)
        self.bar = CountdownBar()
        self.body.addWidget(self.bar)
        self.status = QLabel("正在连接 NapCat…")
        self.status.setFont(font(11, 600))
        self.status.setStyleSheet("color: %s;" % TEXT_SOFT)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(self.status)
        row = QHBoxLayout()
        row.addStretch(1)
        self.refresh_btn = SecondaryButton("刷新二维码", "refresh", ACCENT)
        self.refresh_btn.clicked.connect(lambda: self.refresh(True))
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.body.addLayout(row)
        self.body.addStretch(1)
        hint = QLabel("用手机 QQ 扫一扫；二维码过期会自动换新")
        hint.setFont(font(9, 400))
        hint.setStyleSheet("color: %s;" % MUTED)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(hint)

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._tick)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(2000)
        self._poll_timer.timeout.connect(self._poll)
        try:
            service.qr_ready.connect(self.set_payload)
            service.login_state.connect(self.on_login_state)
        except Exception:
            pass

    def showEvent(self, e):
        super().showEvent(e)
        self._tick_timer.start()
        self._poll_timer.start()
        if self.qr.matrix is None and self.qr.pixmap is None:
            self.refresh(force=True)

    def _disconnect(self):
        try:
            self.service.qr_ready.disconnect(self.set_payload)
        except Exception:
            pass
        try:
            self.service.login_state.disconnect(self.on_login_state)
        except Exception:
            pass

    def closeEvent(self, e):
        self._tick_timer.stop()
        self._poll_timer.stop()
        self._disconnect()
        super().closeEvent(e)

    def refresh(self, force: bool = True):
        if self._success:
            return
        self.status.setText("正在刷新二维码…" if force else "正在获取二维码…")
        self.status.setStyleSheet("color: %s;" % DIM)
        self.bar.set_ratio(1.0, ACCENT)
        self.qr.set_placeholder("正在获取二维码…")
        self._auto_refreshed = False
        try:
            self.service.fetch_qr(force)
        except Exception as e:
            self.status.setText("获取失败: %s" % e)
            self.status.setStyleSheet("color: %s;" % RED)

    def set_payload(self, data: dict):
        if not isinstance(data, dict):
            return
        if data.get("logged_in"):
            self._opened_logged = True
            self._success = True
            self._tick_timer.stop()
            self._poll_timer.stop()
            self.status.setText("已登录 · 凭证已保存，下次启动免扫码")
            self.status.setStyleSheet("color: %s;" % GREEN)
            self.bar.set_ratio(1.0, GREEN)
            self.refresh_btn.setText("关闭")
            try:
                self.refresh_btn.clicked.disconnect()
            except Exception:
                pass
            self.refresh_btn.clicked.connect(self.accept)
            return
        if data.get("matrix"):
            self.qr.set_matrix(data["matrix"])
            self._remaining = int(data.get("expires_in") or 120)
            self._auto_refreshed = bool(data.get("stale"))
            self.bar.set_ratio(1.0 if not data.get("stale") else 0.0, ACCENT if not data.get("stale") else AMBER)
            self._set_waiting()
            if data.get("stale"):
                self.status.setText("二维码已过期 · 请刷新，或回主界面点一键修复")
                self.status.setStyleSheet("color: %s;" % AMBER)
        elif data.get("png"):
            self.qr.set_png(data["png"])
            self._remaining = int(data.get("expires_in") or 120)
            self._auto_refreshed = bool(data.get("stale"))
            self.bar.set_ratio(max(0.0, self._remaining / 120.0), ACCENT if not data.get("stale") else AMBER)
            self._set_waiting()
            if data.get("stale"):
                self.status.setText("二维码已过期 · 请刷新，或回主界面点一键修复")
                self.status.setStyleSheet("color: %s;" % AMBER)
        elif data.get("error") or data.get("source") == "webui_url_only":
            self.qr.set_placeholder("二维码暂不可用")
            msg = str(data.get("error") or "WebUI 只返回了链接，无法直接生成二维码")
            self.status.setText(msg[:120])
            self.status.setStyleSheet("color: %s;" % AMBER)
            self.bar.set_ratio(0.0, AMBER)
            self._auto_refreshed = True

    def _set_waiting(self):
        accepted = False
        self.status.setText("等待扫码 · 请在手机 QQ 上确认")
        self.status.setStyleSheet("color: %s;" % TEXT_SOFT)

    def _tick(self):
        if self._success:
            return
        if self._remaining > 0:
            self._remaining -= 1
            self.bar.set_ratio(self._remaining / 120.0, ACCENT if self._remaining > 20 else AMBER)
            self.status.setText("等待扫码 · 二维码约 %d 秒后刷新" % self._remaining)
        elif not self._auto_refreshed:
            self._auto_refreshed = True
            self.status.setText("二维码即将过期，正在自动换新…")
            self.refresh(force=True)

    def _poll(self):
        if self._success:
            return
        try:
            self.service.check_login()
        except Exception:
            pass

    def on_login_state(self, data: dict):
        if not isinstance(data, dict) or self._success:
            return
        if data.get("isLogin"):
            self._success = True
            self._tick_timer.stop()
            self._poll_timer.stop()
            self.qr.set_placeholder("✓")
            self.bar.set_ratio(1.0, GREEN)
            self.status.setText("登录成功 · 正在建立反向连接")
            self.status.setStyleSheet("color: %s;" % GREEN)
            self.refresh_btn.setEnabled(False)
            QTimer.singleShot(900, self._finish_success)
        elif data.get("qrLoginAccepted"):
            self.status.setText("已扫码 · 请在手机上点击确认")
            self.status.setStyleSheet("color: %s;" % ACCENT)
        elif data.get("error"):
            self.status.setText("WebUI: %s" % str(data["error"])[:90])
            self.status.setStyleSheet("color: %s;" % AMBER)

    def _finish_success(self):
        self._disconnect()
        self.logged_in.emit()
        self.accept()


# ---------------------------------------------------------------------------
# 设置
# ---------------------------------------------------------------------------
class SwitchRow(QWidget):
    def __init__(self, title: str, desc: str, checked: bool, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        col = QVBoxLayout()
        col.setSpacing(1)
        t = QLabel(title)
        t.setFont(font(12, 600))
        t.setStyleSheet("color: %s;" % TEXT_SOFT)
        d = QLabel(desc)
        d.setFont(font(9, 400))
        d.setStyleSheet("color: %s;" % MUTED)
        col.addWidget(t)
        col.addWidget(d)
        lay.addLayout(col, 1)
        self.switch = ToggleSwitch(checked)
        lay.addWidget(self.switch, 0, Qt.AlignmentFlag.AlignVCenter)


class FieldRow(QWidget):
    def __init__(self, label: str, editor: QWidget, hint: str = "", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        l = QLabel(label)
        l.setFont(font(11, 500))
        l.setStyleSheet("color: %s;" % DIM)
        l.setFixedWidth(98)
        lay.addWidget(l)
        lay.addWidget(editor, 1)
        if hint:
            h = QLabel(hint)
            h.setFont(font(9, 400))
            h.setStyleSheet("color: %s;" % MUTED)
            lay.addWidget(h)


class SectionTitle(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFont(font(9, 700, spacing=1.4))
        self.setStyleSheet("color: %s;" % ACCENT)


class SettingsDialog(RoundDialog):
    saved = Signal(object)
    diagnose_requested = Signal()

    def __init__(self, st: Settings, parent=None):
        super().__init__("设置", 620, 664, parent)
        self.st = copy.deepcopy(st)
        form = QVBoxLayout()
        form.setSpacing(9)
        self.body.addLayout(form)

        form.addWidget(SectionTitle("账号与登录"))
        self.account = QLineEdit(self.st.account)
        self.account.setPlaceholderText("QQ 号")
        self.account.setFixedHeight(34)
        form.addWidget(FieldRow("QQ 账号", self.account))
        self.quick = SwitchRow(
            "启动时快速登录",
            "使用 QQ 本地登录凭证，免扫码；凭证失效时自动回退到二维码",
            bool(self.st.quick_login),
        )
        form.addWidget(self.quick)
        info = QLabel(
            "QQ 官方已不支持稳定的账号密码登录；密码登录仍会触发验证码/新设备验证，且可能触发风控。"
            "推荐保持快速登录：首次扫码一次，之后启动就免扫码。"
        )
        info.setWordWrap(True)
        info.setFont(font(9, 400))
        info.setStyleSheet(
            "color: %s; background: rgba(246,199,107,14); border: 1px solid rgba(246,199,107,45);"
            " border-radius: 9px; padding: 8px 10px;" % TEXT_SOFT
        )
        form.addWidget(info)

        form.addSpacing(3)
        form.addWidget(SectionTitle("运行环境"))
        self.distro = QLineEdit(self.st.wsl_distro)
        self.distro.setFixedHeight(34)
        form.addWidget(FieldRow("WSL 发行版", self.distro))
        self.astrbot = QLineEdit(self.st.astrbot_exe)
        self.astrbot.setFixedHeight(34)
        form.addWidget(FieldRow("AstrBot 程序", self.astrbot))
        self.napcat = QLineEdit(self.st.napcat_home)
        self.napcat.setFixedHeight(34)
        form.addWidget(FieldRow("NapCat 目录", self.napcat))

        form.addSpacing(3)
        form.addWidget(SectionTitle("行为"))
        self.tray = SwitchRow("关闭时最小化到托盘", "右键托盘图标才有「退出」选项", bool(self.st.minimize_to_tray))
        form.addWidget(self.tray)
        self.heal = SwitchRow("自动守护", "检测到服务掉线时自动尝试恢复", bool(self.st.auto_heal))
        form.addWidget(self.heal)
        self.autostart = SwitchRow(
            "开机自启",
            "登录 Windows 后自动在托盘启动控制台",
            Settings.autostart_enabled(),
        )
        form.addWidget(self.autostart)
        self.autostart_services = SwitchRow(
            "启动后自动拉起服务",
            "控制台启动后自动执行一键启动",
            bool(self.st.start_services_on_launch),
        )
        form.addWidget(self.autostart_services)

        form.addStretch(1)
        self.error = QLabel("")
        self.error.setFont(font(10, 500))
        self.error.setStyleSheet("color: %s;" % RED)
        self.error.setVisible(False)
        form.addWidget(self.error)
        row = QHBoxLayout()
        diag = SecondaryButton("体检 / 诊断", "shield", SKY)
        diag.clicked.connect(self.diagnose_requested.emit)
        row.addWidget(diag)
        row.addStretch(1)
        cancel = SecondaryButton("取消", None, DIM)
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        save = SecondaryButton("保存设置", "check", ACCENT)
        save.clicked.connect(self._save)
        row.addWidget(save)
        form.addLayout(row)
        transparent_labels(self)

    def _save(self):
        account = self.account.text().strip()
        if account and (not account.isdigit() or not (5 <= len(account) <= 12)):
            self.error.setText("QQ 账号应为 5-12 位数字")
            self.error.setVisible(True)
            return
        self.st.account = account
        self.st.quick_login = self.quick.switch.isChecked()
        self.st.wsl_distro = self.distro.text().strip() or "kali-linux"
        self.st.astrbot_exe = self.astrbot.text().strip()
        self.st.napcat_home = self.napcat.text().strip().rstrip("/") or "/root/Napcat"
        if not self.st.napcat_qq or not self.st.napcat_qq.startswith(self.st.napcat_home):
            self.st.napcat_qq = self.st.napcat_home + "/opt/QQ/qq"
        self.st.minimize_to_tray = self.tray.switch.isChecked()
        self.st.auto_heal = self.heal.switch.isChecked()
        self.st.autostart = self.autostart.switch.isChecked()
        self.st.start_services_on_launch = self.autostart_services.switch.isChecked()
        ok = Settings.apply_autostart(self.st.autostart)
        if not ok and self.st.autostart:
            self.error.setText("开机自启写入失败（可能被安全软件拦截）")
            self.error.setVisible(True)
            return
        self.saved.emit(self.st)
        self.accept()


# ---------------------------------------------------------------------------
# 诊断
# ---------------------------------------------------------------------------
class DiagnoseDialog(RoundDialog):
    repair_requested = Signal()

    def __init__(self, service, parent=None):
        super().__init__("体检 / 诊断", 640, 560, parent)
        self.service = service
        self._items = []
        self.sub = QLabel("检查 AstrBot、NapCat、OneBot、QQ 登录与反向连接")
        self.sub.setFont(font(10, 400))
        self.sub.setStyleSheet("color: %s;" % DIM)
        self.body.addWidget(self.sub)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }")
        self.scroll.viewport().setAutoFillBackground(False)
        self.container = QWidget()
        self.container.setAutoFillBackground(False)
        self.container.setStyleSheet("background: transparent;")
        self.rows = QVBoxLayout(self.container)
        self.rows.setContentsMargins(0, 2, 8, 2)
        self.rows.setSpacing(8)
        self.rows.addStretch(1)
        self.scroll.setWidget(self.container)
        self.body.addWidget(self.scroll, 1)
        row = QHBoxLayout()
        self.rerun = SecondaryButton("重新检查", "refresh", SKY)
        self.rerun.clicked.connect(self.run)
        row.addWidget(self.rerun)
        self.copy_btn = SecondaryButton("复制结果", "copy", SKY)
        self.copy_btn.clicked.connect(self._copy)
        row.addWidget(self.copy_btn)
        row.addStretch(1)
        self.fw_btn = SecondaryButton("放行 6199", "shield", AMBER)
        self.fw_btn.setToolTip("通过 UAC 添加 Windows 防火墙入站规则，允许 WSL 访问 AstrBot 的 6199")
        self.fw_btn.clicked.connect(self.service.allow_firewall)
        self.fw_btn.setVisible(False)
        row.addWidget(self.fw_btn)
        repair = SecondaryButton("一键修复", "spark", ACCENT)
        repair.clicked.connect(self._repair)
        row.addWidget(repair)
        close = SecondaryButton("关闭", None, DIM)
        close.clicked.connect(self.accept)
        row.addWidget(close)
        self.body.addLayout(row)
        try:
            service.diag_ready.connect(self.render)
        except Exception:
            pass
        self.run()
        transparent_labels(self)

    def run(self):
        self._clear()
        tip = QLabel("正在检查…")
        tip.setFont(font(11, 500))
        tip.setStyleSheet("color: %s;" % DIM)
        self.rows.insertWidget(0, tip)
        try:
            self.service.diagnose()
        except Exception as e:
            self.render([{"name": "诊断失败", "ok": False, "detail": str(e), "hint": ""}])

    def _clear(self):
        while self.rows.count():
            item = self.rows.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self.rows.addStretch(1)

    def render(self, items: list):
        self._items = items or []
        self._clear()
        if not items:
            items = [{"name": "没有结果", "ok": False, "detail": "", "hint": ""}]
        for it in items:
            level = "ok" if it.get("ok") else "bad"
            box = QWidget()
            lay = QVBoxLayout(box)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(2)
            top = QHBoxLayout()
            top.setSpacing(8)
            dot = StatusDot(7)
            dot.set_level(level)
            top.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
            name = QLabel(it.get("name", ""))
            name.setFont(font(11, 600))
            name.setStyleSheet("color: %s;" % (TEXT if it.get("ok") else AMBER))
            top.addWidget(name)
            detail = QLabel(it.get("detail", ""))
            detail.setFont(font(9, 400))
            detail.setStyleSheet("color: %s;" % MUTED)
            detail.setWordWrap(True)
            top.addWidget(detail, 1)
            lay.addLayout(top)
            hint = it.get("hint") or ""
            if hint and not it.get("ok"):
                h = QLabel("建议：" + hint)
                h.setFont(font(9, 400))
                h.setStyleSheet("color: %s; padding-left: 18px;" % DIM)
                h.setWordWrap(True)
                lay.addWidget(h)
            self.rows.insertWidget(self.rows.count() - 1, box)
        fw_failed = any(
            (not it.get("ok")) and "WSL" in str(it.get("name", "")) and "6199" in str(it.get("name", ""))
            for it in items
        )
        self.fw_btn.setVisible(fw_failed)
        transparent_labels(self.container)

    def _copy(self):
        lines = ["大肥鱼控制台 · 体检报告", time.strftime("%Y-%m-%d %H:%M:%S"), ""]
        for it in self._items:
            mark = "OK" if it.get("ok") else "!!"
            lines.append("[%s] %s · %s" % (mark, it.get("name", ""), it.get("detail", "")))
            if it.get("hint") and not it.get("ok"):
                lines.append("     建议：" + str(it.get("hint")))
        QApplication.clipboard().setText("\n".join(lines))
        self.copy_btn.setText("已复制")
        self.copy_btn._recalc()
        self.copy_btn.update()
        QTimer.singleShot(1500, self._reset_copy)

    def _reset_copy(self):
        self.copy_btn.setText("复制结果")
        self.copy_btn._recalc()
        self.copy_btn.update()

    def _repair(self):
        self.repair_requested.emit()
        self.accept()


# ---------------------------------------------------------------------------
# 退出
# ---------------------------------------------------------------------------
class ExitDialog(RoundDialog):
    choice = Signal(str)

    def __init__(self, parent=None):
        super().__init__("退出控制台", 440, 252, parent)
        text = QLabel(
            "关闭窗口只会最小化到托盘，服务会继续运行。\n退出控制台时，你可以让 AstrBot 与 NapCat 继续在后台工作。"
        )
        text.setWordWrap(True)
        text.setFont(font(11, 400))
        text.setStyleSheet("color: %s;" % TEXT_SOFT)
        self.body.addWidget(text)
        self.body.addStretch(1)
        row = QHBoxLayout()
        row.setSpacing(9)
        cancel = SecondaryButton("取消", None, DIM)
        cancel.clicked.connect(lambda: self._pick("cancel"))
        row.addWidget(cancel)
        row.addStretch(1)
        stop = SecondaryButton("退出并停止服务", "stop", RED)
        stop.clicked.connect(lambda: self._pick("exit_stop"))
        row.addWidget(stop)
        leave = SecondaryButton("仅退出", "external", ACCENT)
        leave.clicked.connect(lambda: self._pick("exit"))
        row.addWidget(leave)
        self.body.addLayout(row)
        transparent_labels(self)

    def _pick(self, value: str):
        self.choice.emit(value)
        self.accept()


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------
class MainWindow(QWidget):
    def __init__(self, service, start_minimized: bool = False):
        super().__init__()
        self.service = service
        self.st = service.st
        self._status = None
        self._busy = False
        self._quitting = False
        self._allow_close = False
        self._desired = False
        self._ok_since = 0.0
        self._last_heal = 0.0
        self._last_level = ""
        self._tray_hint = False
        self._qr_dialog = None
        self._settings_dialog = None
        self._diag_dialog = None
        self._start_minimized = start_minimized
        self._log_target = "console"
        self._events: list[tuple[str, str, str]] = []
        self._prev = {"a": None, "n": None, "q": None, "l": None, "phase": ""}
        self._progress_mark = -1

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("大肥鱼控制台")
        self.setWindowIcon(app_icon())
        self.setFixedSize(1000, 680)
        self._build()
        self._setup_tray()
        self._connect()
        transparent_labels(self)
        self._center()
        self._add_event("控制台已启动，托盘守护中", "ok")
        self._poll = QTimer(self)
        self._poll.setInterval(2600)
        self._poll.timeout.connect(self.service.refresh_status)
        self._poll.start()
        self._log_timer = QTimer(self)
        self._log_timer.setInterval(1800)
        self._log_timer.timeout.connect(self._request_log)
        self.service.refresh_status()
        self._request_log()
        QTimer.singleShot(200, self._fade_in)

    # -- 构建 --------------------------------------------------------------
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.surface = Surface(self)
        root.addWidget(self.surface)

        lay = QVBoxLayout(self.surface)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(0)
        self.titlebar = TitleBar()
        lay.addWidget(self.titlebar)

        content = QWidget()
        lay.addWidget(content, 1)
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 6, 24, 10)
        cl.setSpacing(11)
        self.hero = HeroCard()
        cl.addWidget(self.hero)
        row = QHBoxLayout()
        row.setSpacing(12)
        self.card_a = StatCard("ASTRBOT 本体", "bot", ACCENT)
        self.card_n = StatCard("NAPCAT 网关", "gateway", SKY)
        self.card_q = StatCard("QQ 连接", "chat", GREEN)
        row.addWidget(self.card_a, 1)
        row.addWidget(self.card_n, 1)
        row.addWidget(self.card_q, 1)
        cl.addLayout(row)
        self.loginbar = LoginBar()
        cl.addWidget(self.loginbar)
        self.recent = RecentEvents()
        self.recent.set_events([("现在", "控制台已启动，托盘守护中", "ok")])
        self.recent.clicked.connect(self._expand_logs)
        cl.addWidget(self.recent, 1)
        self.logs = LogPanel()
        cl.addWidget(self.logs)
        self.footer = FooterBar()
        cl.addWidget(self.footer)

        self.toast = Toast(self.surface)
        self.hero.button.clicked.connect(self.primary_action)
        self.loginbar.button.clicked.connect(self.open_qr)
        self.titlebar.min_btn.clicked.connect(self.showMinimized)
        self.titlebar.settings_btn.clicked.connect(self.open_settings)
        self.titlebar.close_btn.clicked.connect(self.close)
        self.logs.target_changed.connect(self._on_log_target)
        self.logs.expanded_changed.connect(self._on_log_expanded)
        self.footer.dashboard_clicked.connect(self.service.open_dashboard)
        self.footer.logs_clicked.connect(self.open_logs)

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip("大肥鱼控制台")
        menu = QMenu()
        self.act_show = QAction(action_icon("spark", ACCENT), "显示控制台", self)
        self.act_start = QAction(action_icon("power", ACCENT), "一键启动", self)
        self.act_qr = QAction(action_icon("qr", SKY), "扫码登录", self)
        self.act_dash = QAction(action_icon("external", TEXT_SOFT), "打开 AstrBot 后台", self)
        self.act_stop = QAction(action_icon("stop", RED), "停止全部服务", self)
        self.act_exit = QAction(action_icon("close", RED), "退出控制台", self)
        self.act_show.triggered.connect(self._show_window)
        self.act_start.triggered.connect(self._start_all)
        self.act_qr.triggered.connect(self.open_qr)
        self.act_dash.triggered.connect(self.service.open_dashboard)
        self.act_stop.triggered.connect(self._tray_stop)
        self.act_exit.triggered.connect(self._request_quit)
        menu.addAction(self.act_show)
        menu.addAction(self.act_start)
        menu.addAction(self.act_qr)
        menu.addSeparator()
        menu.addAction(self.act_dash)
        menu.addAction(self.act_stop)
        menu.addSeparator()
        menu.addAction(self.act_exit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        else:
            # 没有托盘时不要把窗口藏起来，否则用户无法操作
            self._start_minimized = False

    def _connect(self):
        s = self.service
        s.status_ready.connect(self.apply_status)
        s.progress.connect(self.on_progress)
        s.action_done.connect(self.on_action_done)
        s.stop_done.connect(self.on_stop_done)
        s.qr_ready.connect(self.on_qr_ready)
        s.log_ready.connect(self.on_log_ready)
        s.toast.connect(self.show_toast)

    def _center(self):
        scr = QApplication.primaryScreen().availableGeometry()
        self.move(
            scr.center().x() - self.width() // 2,
            scr.center().y() - self.height() // 2,
        )

    def _fade_in(self):
        if self._start_minimized:
            return
        self.setWindowOpacity(0.0)
        self.show()
        self._fade = QVariantAnimation(self)
        self._fade.setDuration(280)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.valueChanged.connect(self.setWindowOpacity)
        self._fade.start()
        set_dwm_dark(self)

    # -- 状态刷新 ----------------------------------------------------------
    def apply_status(self, s: dict):
        if not isinstance(s, dict):
            return
        self._status = s
        a = s.get("astrbot", {})
        n = s.get("napcat", {})
        q = s.get("qq", {})
        o = s.get("onebot", {})
        h = s.get("health", {})
        level = h.get("level", "idle")
        text = h.get("text", "未知状态")

        self.titlebar.pill.set_state(text, level)
        self.card_a.set_data(
            "运行中" if a.get("running") else "已停止",
            ("PID %s · 端口 %s" % (a.get("pid"), a.get("port"))) if a.get("running") else ("端口 %s 未监听" % a.get("port")),
            "ok" if a.get("running") else "idle",
        )
        nap_meta = "未运行"
        if n.get("running"):
            pids = ",".join(str(x) for x in (n.get("pids") or []))
            nap_meta = "PID %s · 网关 %s" % (pids or "-", n.get("gateway") or "?")
            if not n.get("webui"):
                nap_meta += " · WebUI 等待"
        elif n.get("gateway"):
            nap_meta = "未运行 · 网关 %s" % n.get("gateway")
        self.card_n.set_data(
            "运行中" if n.get("running") else "已停止",
            nap_meta,
            "ok" if n.get("running") else "idle",
        )
        if q.get("logged_in"):
            qstate = "已登录" if q.get("online") else "已离线"
            qlevel = "ok" if q.get("linked") else "warn"
            qmeta = "账号 %s · %s" % (q.get("account"), "反向 WS 已连接" if q.get("linked") else "通道未连接")
        else:
            qstate = "待登录"
            qlevel = "warn" if n.get("running") else "idle"
            qmeta = "账号 %s · %s" % (q.get("account"), "扫码后自动连接" if n.get("running") else "服务未启动")
        self.card_q.set_data(qstate, qmeta, qlevel)

        self.loginbar.set_data(
            bool(q.get("logged_in")),
            str(q.get("account") or self.st.account),
            q.get("quick_ready"),
            str(q.get("phase") or ""),
            str(n.get("webui_error") or ""),
            bool(n.get("running")),
        )
        self._update_events(a, n, q, level)
        self._update_recent_summary(a, n, q, o)

        if level == "ok":
            if not self._ok_since:
                self._ok_since = time.time()
            self._desired = True
        else:
            self._ok_since = 0.0
        if a.get("running") and n.get("running"):
            self._desired = True

        if not self._busy:
            self._apply_hero(s)

        self.footer.set_state(
            ("托盘守护中 · 状态正常" if level == "ok" else text),
            level,
        )
        self._update_tray_tooltip(s)

        if self._last_level and self._last_level != level and level == "ok":
            self.show_toast("QQ 已登录，AstrBot 通道已恢复", False)
        self._last_level = level

        if level == "warn" and not q.get("logged_in") and self.isHidden():
            self._tray_notify("QQ 需要登录", "服务已运行，右键托盘图标或打开控制台扫码。")

        self._maybe_auto_heal(s)

    def _apply_hero(self, s: dict):
        a = s.get("astrbot", {})
        n = s.get("napcat", {})
        q = s.get("qq", {})
        h = s.get("health", {})
        level = h.get("level", "idle")
        account = q.get("account") or self.st.account
        uptime = ""
        if self._ok_since:
            secs = int(time.time() - self._ok_since)
            if secs >= 60:
                uptime = " · 已守护 %02d:%02d:%02d" % (secs // 3600, secs % 3600 // 60, secs % 60)
        if level == "ok":
            self.hero.set_content(
                "一切就绪",
                "AstrBot、NapCat 与 QQ 已经连在一起",
                "账号 %s%s" % (account, uptime),
                "全部运行中",
                "ok",
            )
            self.hero.set_phase(3)
        elif q.get("logged_in") and not q.get("linked"):
            self.hero.set_content(
                "连接需要修复",
                "QQ 已登录，但 OneBot 反向连接还没有建立",
                "账号 %s · 点击一键修复自动重启 NapCat" % account,
                "一键修复",
                "warn",
            )
            self.hero.set_phase(2)
        elif a.get("running") and n.get("running") and not q.get("logged_in"):
            self.hero.set_content(
                "还差一步",
                "服务已经就绪，扫码登录 QQ 后就能开始聊天",
                "账号 %s · 首次扫码后自动保存凭证" % account,
                "扫码登录",
                "warn",
            )
            self.hero.set_phase(2)
        elif a.get("running") or n.get("running"):
            self.hero.set_content(
                "继续启动",
                "还有服务没有起来，点一下补齐并校验连接",
                h.get("text", ""),
                "继续启动",
                "start",
            )
            self.hero.set_phase(1 if a.get("running") else 0)
        else:
            self.hero.set_content(
                "开始今天的陪伴",
                "一键启动 AstrBot、NapCat，并快速登录 QQ",
                "账号 %s · 深海守护已就绪" % account,
                "一键启动",
                "start",
            )
            self.hero.set_phase(-1)

    def _update_tray_tooltip(self, s: dict):
        a = "●" if s.get("astrbot", {}).get("running") else "○"
        n = "●" if s.get("napcat", {}).get("running") else "○"
        q = "●" if s.get("qq", {}).get("linked") else "○"
        self.tray.setToolTip(
            "大肥鱼控制台\nAstrBot %s  NapCat %s  QQ %s\n%s"
            % (a, n, q, s.get("health", {}).get("text", ""))
        )

    def _update_recent_summary(self, a: dict, n: dict, q: dict, o: dict):
        if not n.get("running"):
            self.recent.set_summary("控制台已就绪 · 等待一键启动")
            return
        parts = []
        if n.get("gateway"):
            parts.append("网关 " + str(n.get("gateway")))
        parts.append("WebUI 就绪" if n.get("webui") else "WebUI 等待")
        if q.get("logged_in"):
            if q.get("linked"):
                parts.append("反向 WS %d 个" % int(o.get("clients") or 0))
            else:
                parts.append("等待反向 WS")
        else:
            parts.append("等待 QQ 登录")
        if q.get("quick_ready"):
            parts.append("凭证已保存")
        self.recent.set_summary(" · ".join(parts))

    def _update_events(self, a: dict, n: dict, q: dict, level: str):
        prev = self._prev
        if a.get("running") and prev.get("a") is not True:
            self._add_event("AstrBot 已就绪 · 面板 :%s" % a.get("port"), "ok")
        if n.get("running") and prev.get("n") is not True:
            self._add_event("NapCat 网关已就绪 · %s" % (n.get("gateway") or "WSL"), "ok")
        if q.get("logged_in") and prev.get("q") is not True:
            self._add_event("QQ %s 已登录" % (q.get("account") or ""), "ok")
        if q.get("linked") and prev.get("l") is not True:
            self._add_event("OneBot 反向连接已建立", "ok")
        if prev.get("l") is True and not q.get("linked"):
            self._add_event("OneBot 反向连接断开，正在等待重连", "warn")
        phase = str(q.get("phase") or "")
        if phase == "waiting_qrcode" and prev.get("phase") != phase and not q.get("logged_in"):
            self._add_event("等待扫码登录 QQ", "warn")
        prev.update(
            {
                "a": bool(a.get("running")),
                "n": bool(n.get("running")),
                "q": bool(q.get("logged_in")),
                "l": bool(q.get("linked")),
                "phase": phase,
            }
        )

    def _maybe_auto_heal(self, s: dict):
        if not self.st.auto_heal or not self._desired or self._busy or self._quitting:
            return
        now = time.time()
        if now - self._last_heal < 240:
            return
        a = s.get("astrbot", {}).get("running")
        n = s.get("napcat", {}).get("running")
        q = s.get("qq", {})
        need = False
        if not a or not n:
            need = True
        elif q.get("logged_in") and not q.get("linked"):
            need = True
        if need:
            self._last_heal = now
            self.show_toast("检测到服务掉线，正在自动恢复…", False)
            self._start_all(auto=True)

    # -- 动作 --------------------------------------------------------------
    def primary_action(self):
        if self._busy:
            return
        s = self._status or {}
        q = s.get("qq", {})
        a = s.get("astrbot", {}).get("running")
        n = s.get("napcat", {}).get("running")
        if a and n and not q.get("logged_in"):
            self.open_qr()
            return
        self._start_all()

    def _start_all(self, auto: bool = False):
        if self._busy:
            return
        if hasattr(self.service, "busy") and self.service.busy:
            return
        self._busy = True
        self._ok_since = 0.0
        self._progress_mark = -1
        self._add_event("开始一键启动", "info")
        self.hero.set_content(
            "正在启动…",
            "准备检查运行环境",
            "进度 0% · 请稍候",
            "正在启动",
            "busy",
            True,
        )
        self.hero.set_phase(0)
        self.titlebar.pill.set_state("启动中", "busy")
        if not auto:
            self.show_toast("开始一键启动…", False)
        self.service.start_all()

    def on_progress(self, pct: int, msg: str):
        self._busy = True
        for mark, note in ((20, "正在启动 AstrBot"), (58, "正在拉起 NapCat 网关"), (78, "正在快速登录 QQ")):
            if pct >= mark and self._progress_mark < mark:
                self._progress_mark = mark
                self._add_event(note, "info")
        self.hero.set_content(
            "正在启动…",
            msg,
            "进度 %d%% · 正在自动校准连接" % pct,
            "正在启动",
            "busy",
            True,
        )
        if pct < 42:
            self.hero.set_phase(0)
        elif pct < 80:
            self.hero.set_phase(1)
        else:
            self.hero.set_phase(2)
        self.titlebar.pill.set_state("启动中", "busy")

    def on_action_done(self, res: dict):
        self._busy = False
        ok = bool(res.get("ok"))
        msg = str(res.get("msg") or "")
        self._add_event(
            ("启动完成 · " + (msg.splitlines() or [msg])[0]) if ok else ("启动遇到问题 · " + (msg.splitlines() or [msg])[0][:60]),
            "ok" if ok else "warn",
        )
        if res.get("needs_qr"):
            self.show_toast("服务已启动，还需要扫码登录 QQ", False)
            self._desired = True
            self.open_qr(res.get("qr"))
        elif ok:
            self._desired = True
            first = (msg.splitlines() or [msg])[0]
            self.show_toast("✔ " + first, False)
        else:
            self._desired = False
            first = (msg.splitlines() or [msg])[0]
            self.show_toast("✘ " + first[:120], True)
            self.logs.set_target("console")
            if not self.logs._expanded:
                self.logs.toggle()
        self.service.refresh_status()
        self._request_log()

    def on_stop_done(self, res: dict):
        if self._quitting:
            self._do_quit()
        else:
            self._busy = False
            self.show_toast("已停止服务", bool(not res.get("ok")))
        self.service.refresh_status()

    def _request_quit(self):
        if self._quitting:
            return
        if self._busy:
            self.show_toast("还有任务在进行，请稍候再退出", True)
            return
        s = self._status or {}
        running = s.get("astrbot", {}).get("running") or s.get("napcat", {}).get("running")
        if not running:
            self._quitting = True
            self._do_quit()
            return
        dlg = ExitDialog(self)
        dlg.choice.connect(self._on_exit_choice)
        dlg.show()

    def _on_exit_choice(self, choice: str):
        if choice == "cancel":
            return
        if choice == "exit":
            self._quitting = True
            self._do_quit()
        elif choice == "exit_stop":
            self._quitting = True
            self._desired = False
            self.hero.set_content(
                "正在退出…",
                "正在停止 AstrBot 与 NapCat",
                "请稍候",
                "停止中",
                "busy",
                True,
            )
            self.service.stop_all()

    def _do_quit(self):
        self._allow_close = True
        try:
            self.tray.hide()
        except Exception:
            pass
        try:
            self.service.shutdown()
        except Exception:
            pass
        QApplication.quit()

    def _tray_stop(self):
        if self._busy:
            self.show_toast("任务进行中，请稍候", True)
            return
        self._desired = False
        self.service.stop_all()

    # -- 二维码 / 登录 -----------------------------------------------------
    def open_qr(self, payload=None):
        if self._qr_dialog is not None:
            try:
                self._qr_dialog.raise_()
                self._qr_dialog.activateWindow()
                if payload:
                    self._qr_dialog.set_payload(payload)
                else:
                    self._qr_dialog.refresh(force=False)
            except Exception:
                pass
            return
        dlg = QRDialog(self.service, self)
        dlg.logged_in.connect(self._on_logged_in)
        dlg.finished.connect(self._on_qr_closed)
        self._qr_dialog = dlg
        if payload:
            dlg.set_payload(payload)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _on_qr_closed(self, _):
        self._qr_dialog = None
        self.service.refresh_status()

    def _on_logged_in(self):
        self._add_event("扫码登录成功 · 正在建立反向连接", "ok")
        self.show_toast("QQ 登录成功，正在建立连接…", False)
        QTimer.singleShot(1200, self.service.refresh_status)

    def on_qr_ready(self, data: dict):
        if self._qr_dialog is not None:
            try:
                self._qr_dialog.set_payload(data)
            except Exception:
                pass
            return
        if not isinstance(data, dict):
            return
        if data.get("logged_in"):
            self.show_toast("QQ 已登录", False)
            return
        if data.get("matrix") or data.get("png") or data.get("error"):
            self.open_qr(data)

    # -- 日志 --------------------------------------------------------------
    def _on_log_target(self, target: str):
        self._log_target = target
        self._request_log()

    def _add_event(self, text: str, level: str = "info"):
        if not text:
            return
        stamp = time.strftime("%H:%M")
        if self._events and self._events[-1][1] == text:
            return
        self._events.append((stamp, text, level))
        self._events = self._events[-8:]
        self.recent.set_events(self._events[-4:])
        try:
            be = getattr(self.service, "backend", None)
            if be is not None:
                be.event(text)
        except Exception:
            pass

    def _expand_logs(self):
        if not self.logs._expanded:
            self.logs.toggle()
        self.logs.set_target("console")
        self.show_toast("已展开实时日志", False)

    def _on_log_expanded(self, expanded: bool):
        if expanded:
            self.recent.hide()
            self._log_timer.start()
            self._request_log()
        else:
            self._log_timer.stop()

            def show_recent():
                if not self.logs._expanded:
                    self.recent.show()

            QTimer.singleShot(230, show_recent)

    def _request_log(self):
        try:
            self.service.read_log(self._log_target)
        except Exception:
            pass

    def on_log_ready(self, target: str, text: str):
        if target == self._log_target:
            self.logs.set_text(text)

    # -- 设置 / 诊断 -------------------------------------------------------
    def open_settings(self):
        if self._settings_dialog is not None:
            self._settings_dialog.raise_()
            return
        dlg = SettingsDialog(self.st, self)
        dlg.saved.connect(self._on_settings_saved)
        dlg.diagnose_requested.connect(self.open_diagnose)
        dlg.finished.connect(lambda: setattr(self, "_settings_dialog", None))
        self._settings_dialog = dlg
        dlg.show()
        dlg.raise_()

    def _on_settings_saved(self, st: Settings):
        self.st = st
        self.service.apply_settings(st)
        self._add_event("设置已更新", "info")
        self.show_toast("设置已保存", False)
        QTimer.singleShot(300, self.service.refresh_status)

    def open_diagnose(self):
        if self._diag_dialog is not None:
            self._diag_dialog.raise_()
            return
        dlg = DiagnoseDialog(self.service, self)
        dlg.repair_requested.connect(self._start_all)
        dlg.finished.connect(lambda: setattr(self, "_diag_dialog", None))
        self._diag_dialog = dlg
        dlg.show()
        dlg.raise_()

    def open_logs(self):
        try:
            os.startfile(str(core.LOG_DIR))
        except Exception:
            pass

    # -- 托盘 / 窗口 -------------------------------------------------------
    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self._show_window()

    def _show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        try:
            self.setWindowOpacity(1.0)
        except Exception:
            pass

    def _tray_notify(self, title: str, text: str):
        try:
            self.tray.showMessage(title, text, app_icon(), 3500)
        except Exception:
            pass

    def show_toast(self, text: str, bad: bool = False):
        if not text:
            return
        try:
            self.toast.show_message(text, "bad" if bad else "ok")
        except Exception:
            pass

    def resizeEvent(self, e):
        super().resizeEvent(e)
        try:
            self.toast.reposition()
        except Exception:
            pass

    def changeEvent(self, e):
        super().changeEvent(e)

    def closeEvent(self, e):
        if self._allow_close:
            e.accept()
            return
        if self.st.minimize_to_tray and self.tray.isVisible():
            e.ignore()
            self.hide()
            if not self._tray_hint:
                self._tray_hint = True
                self._tray_notify(
                    "大肥鱼控制台",
                    "已最小化到托盘，服务继续运行。\n右键托盘图标可以「退出控制台」。",
                )
            return
        self._request_quit()
        e.ignore()

    def showEvent(self, e):
        super().showEvent(e)
        set_dwm_dark(self)
