# -*- coding: utf-8 -*-
"""大肥鱼控制台 - 自绘组件。"""
from __future__ import annotations

import math
from typing import Iterable

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
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
    QPolygonF,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

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
    FONT_UI,
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


# ---------------------------------------------------------------------------
# 基础绘制
# ---------------------------------------------------------------------------
def mix(a: str | QColor, b: str | QColor, t: float) -> QColor:
    c1, c2 = QColor(a), QColor(b)
    t = max(0.0, min(1.0, t))
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
        int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
    )


LEVEL_COLOR = {
    "ok": GREEN,
    "warn": AMBER,
    "bad": RED,
    "idle": MUTED,
    "busy": ACCENT,
    "info": SKY,
}


def make_labels_transparent(root: QWidget) -> None:
    for lbl in root.findChildren(QLabel):
        if "background" in (lbl.styleSheet() or ""):
            continue
        lbl.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        lbl.setAutoFillBackground(False)


class Icon:
    """手绘小图标，避免 emoji 在不同机器上变样。"""

    @staticmethod
    def paint(p: QPainter, name: str, r: QRectF, color: QColor, width: float = 1.7):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        x, y, w, h = r.x(), r.y(), r.width(), r.height()
        cx, cy = x + w / 2, y + h / 2
        s = min(w, h)

        if name == "power":
            path = QPainterPath()
            path.arcMoveTo(QRectF(x + w * 0.16, y + h * 0.16, w * 0.68, h * 0.68), 55)
            path.arcTo(QRectF(x + w * 0.16, y + h * 0.16, w * 0.68, h * 0.68), 55, 250)
            p.drawPath(path)
            p.drawLine(QPointF(cx, y + h * 0.08), QPointF(cx, y + h * 0.44))
        elif name == "play":
            path = QPainterPath()
            path.moveTo(x + w * 0.32, y + h * 0.18)
            path.lineTo(x + w * 0.80, cy)
            path.lineTo(x + w * 0.32, y + h * 0.82)
            path.closeSubpath()
            p.setBrush(color)
            p.drawPath(path)
        elif name == "check":
            path = QPainterPath()
            path.moveTo(x + w * 0.16, y + h * 0.53)
            path.lineTo(x + w * 0.40, y + h * 0.76)
            path.lineTo(x + w * 0.84, y + h * 0.25)
            p.drawPath(path)
        elif name == "close":
            p.drawLine(QPointF(x + w * 0.28, y + h * 0.28), QPointF(x + w * 0.72, y + h * 0.72))
            p.drawLine(QPointF(x + w * 0.72, y + h * 0.28), QPointF(x + w * 0.28, y + h * 0.72))
        elif name == "minimize":
            p.drawLine(QPointF(x + w * 0.24, y + h * 0.62), QPointF(x + w * 0.76, y + h * 0.62))
        elif name == "settings":
            p.drawEllipse(QPointF(cx, cy), s * 0.16, s * 0.16)
            for i in range(8):
                a = math.radians(i * 45)
                p.drawLine(
                    QPointF(cx + math.cos(a) * s * 0.27, cy + math.sin(a) * s * 0.27),
                    QPointF(cx + math.cos(a) * s * 0.38, cy + math.sin(a) * s * 0.38),
                )
            p.drawEllipse(QPointF(cx, cy), s * 0.36, s * 0.36)
        elif name == "terminal":
            rr = QRectF(x + w * 0.10, y + h * 0.16, w * 0.80, h * 0.68)
            p.drawRoundedRect(rr, 3, 3)
            p.drawLine(QPointF(x + w * 0.22, y + h * 0.36), QPointF(x + w * 0.36, y + h * 0.48))
            p.drawLine(QPointF(x + w * 0.22, y + h * 0.60), QPointF(x + w * 0.36, y + h * 0.48))
            p.drawLine(QPointF(x + w * 0.44, y + h * 0.62), QPointF(x + w * 0.64, y + h * 0.62))
        elif name == "external":
            p.drawRoundedRect(QRectF(x + w * 0.14, y + h * 0.24, w * 0.56, h * 0.56), 2, 2)
            p.drawLine(QPointF(x + w * 0.48, y + h * 0.50), QPointF(x + w * 0.84, y + h * 0.14))
            p.drawLine(QPointF(x + w * 0.62, y + h * 0.14), QPointF(x + w * 0.84, y + h * 0.14))
            p.drawLine(QPointF(x + w * 0.84, y + h * 0.14), QPointF(x + w * 0.84, y + h * 0.36))
        elif name == "qr":
            for ox, oy in ((0.12, 0.12), (0.58, 0.12), (0.12, 0.58)):
                rr = QRectF(x + w * ox, y + h * oy, w * 0.30, h * 0.30)
                p.drawRoundedRect(rr, 2, 2)
                p.setBrush(color)
                p.drawRect(QRectF(x + w * (ox + 0.10), y + h * (oy + 0.10), w * 0.10, h * 0.10))
                p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(x + w * 0.62, y + h * 0.62, w * 0.10, h * 0.10))
            p.drawRect(QRectF(x + w * 0.76, y + h * 0.76, w * 0.10, h * 0.10))
            p.drawRect(QRectF(x + w * 0.62, y + h * 0.80, w * 0.10, h * 0.06))
        elif name == "key":
            p.drawEllipse(QPointF(x + w * 0.36, y + h * 0.42), s * 0.16, s * 0.16)
            p.drawLine(QPointF(x + w * 0.48, y + h * 0.54), QPointF(x + w * 0.82, y + h * 0.82))
            p.drawLine(QPointF(x + w * 0.66, y + h * 0.72), QPointF(x + w * 0.74, y + h * 0.64))
            p.drawLine(QPointF(x + w * 0.74, y + h * 0.80), QPointF(x + w * 0.82, y + h * 0.72))
        elif name == "refresh":
            path = QPainterPath()
            path.arcMoveTo(QRectF(x + w * 0.16, y + h * 0.16, w * 0.68, h * 0.68), 60)
            path.arcTo(QRectF(x + w * 0.16, y + h * 0.16, w * 0.68, h * 0.68), 60, 265)
            p.drawPath(path)
            p.drawLine(QPointF(x + w * 0.76, y + h * 0.10), QPointF(x + w * 0.86, y + h * 0.26))
            p.drawLine(QPointF(x + w * 0.76, y + h * 0.10), QPointF(x + w * 0.60, y + h * 0.20))
        elif name == "copy":
            p.drawRoundedRect(QRectF(x + w * 0.30, y + h * 0.10, w * 0.58, h * 0.58), 2, 2)
            p.drawRoundedRect(QRectF(x + w * 0.12, y + h * 0.32, w * 0.46, h * 0.46), 2, 2)
        elif name == "folder":
            path = QPainterPath()
            path.moveTo(x + w * 0.10, y + h * 0.30)
            path.lineTo(x + w * 0.40, y + h * 0.30)
            path.lineTo(x + w * 0.48, y + h * 0.40)
            path.lineTo(x + w * 0.90, y + h * 0.40)
            path.lineTo(x + w * 0.86, y + h * 0.82)
            path.lineTo(x + w * 0.14, y + h * 0.82)
            path.closeSubpath()
            p.drawPath(path)
        elif name == "chevron-down":
            p.drawLine(QPointF(x + w * 0.28, y + h * 0.40), QPointF(cx, y + h * 0.64))
            p.drawLine(QPointF(cx, y + h * 0.64), QPointF(x + w * 0.72, y + h * 0.40))
        elif name == "chevron-up":
            p.drawLine(QPointF(x + w * 0.28, y + h * 0.60), QPointF(cx, y + h * 0.36))
            p.drawLine(QPointF(cx, y + h * 0.36), QPointF(x + w * 0.72, y + h * 0.60))
        elif name == "bot":
            p.drawRoundedRect(QRectF(x + w * 0.18, y + h * 0.30, w * 0.64, h * 0.50), 7, 7)
            p.drawLine(QPointF(cx, y + h * 0.30), QPointF(cx, y + h * 0.14))
            p.setBrush(color)
            p.drawEllipse(QPointF(cx, y + h * 0.13), s * 0.055, s * 0.055)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(x + w * 0.38, y + h * 0.53), s * 0.045, s * 0.045)
            p.drawEllipse(QPointF(x + w * 0.62, y + h * 0.53), s * 0.045, s * 0.045)
            p.drawLine(QPointF(x + w * 0.40, y + h * 0.68), QPointF(x + w * 0.60, y + h * 0.68))
        elif name == "gateway":
            p.drawRoundedRect(QRectF(x + w * 0.34, y + h * 0.34, w * 0.32, h * 0.32), 4, 4)
            for dx, dy in ((0.18, 0.18), (0.82, 0.18), (0.18, 0.82), (0.82, 0.82)):
                p.drawLine(
                    QPointF(x + w * 0.42, y + h * 0.42),
                    QPointF(x + w * dx, y + h * dy),
                )
                p.setBrush(color)
                p.drawEllipse(QPointF(x + w * dx, y + h * dy), s * 0.055, s * 0.055)
                p.setBrush(Qt.BrushStyle.NoBrush)
        elif name == "chat":
            path = QPainterPath()
            path.addRoundedRect(QRectF(x + w * 0.12, y + h * 0.16, w * 0.76, h * 0.56), 9, 9)
            p.drawPath(path)
            path2 = QPainterPath()
            path2.moveTo(x + w * 0.34, y + h * 0.68)
            path2.lineTo(x + w * 0.26, y + h * 0.88)
            path2.lineTo(x + w * 0.50, y + h * 0.70)
            p.drawPath(path2)
            p.setBrush(color)
            for i in range(3):
                p.drawEllipse(QPointF(x + w * (0.34 + i * 0.16), y + h * 0.44), s * 0.035, s * 0.035)
        elif name == "warning":
            path = QPainterPath()
            path.moveTo(cx, y + h * 0.14)
            path.lineTo(x + w * 0.88, y + h * 0.82)
            path.lineTo(x + w * 0.12, y + h * 0.82)
            path.closeSubpath()
            p.drawPath(path)
            p.drawLine(QPointF(cx, y + h * 0.38), QPointF(cx, y + h * 0.60))
            p.setBrush(color)
            p.drawEllipse(QPointF(cx, y + h * 0.71), s * 0.035, s * 0.035)
        elif name == "info":
            p.drawEllipse(QPointF(cx, cy), s * 0.38, s * 0.38)
            p.drawLine(QPointF(cx, y + h * 0.45), QPointF(cx, y + h * 0.70))
            p.setBrush(color)
            p.drawEllipse(QPointF(cx, y + h * 0.32), s * 0.035, s * 0.035)
        elif name == "stop":
            p.drawRoundedRect(QRectF(x + w * 0.26, y + h * 0.26, w * 0.48, h * 0.48), 3, 3)
        elif name == "clock":
            p.drawEllipse(QPointF(cx, cy), s * 0.36, s * 0.36)
            p.drawLine(QPointF(cx, cy), QPointF(cx, y + h * 0.30))
            p.drawLine(QPointF(cx, cy), QPointF(x + w * 0.68, cy))
        elif name == "shield":
            path = QPainterPath()
            path.moveTo(cx, y + h * 0.10)
            path.lineTo(x + w * 0.82, y + h * 0.26)
            path.lineTo(x + w * 0.76, y + h * 0.58)
            path.quadTo(cx, y + h * 0.90, x + w * 0.24, y + h * 0.58)
            path.lineTo(x + w * 0.18, y + h * 0.26)
            path.closeSubpath()
            p.drawPath(path)
            p.drawLine(QPointF(x + w * 0.38, y + h * 0.48), QPointF(x + w * 0.47, y + h * 0.58))
            p.drawLine(QPointF(x + w * 0.47, y + h * 0.58), QPointF(x + w * 0.64, y + h * 0.38))
        elif name == "trash":
            p.drawRoundedRect(QRectF(x + w * 0.24, y + h * 0.28, w * 0.52, h * 0.56), 3, 3)
            p.drawLine(QPointF(x + w * 0.16, y + h * 0.24), QPointF(x + w * 0.84, y + h * 0.24))
            p.drawLine(QPointF(x + w * 0.40, y + h * 0.14), QPointF(x + w * 0.60, y + h * 0.14))
            p.drawLine(QPointF(x + w * 0.42, y + h * 0.40), QPointF(x + w * 0.42, y + h * 0.72))
            p.drawLine(QPointF(x + w * 0.58, y + h * 0.40), QPointF(x + w * 0.58, y + h * 0.72))
        elif name == "lock":
            p.drawRoundedRect(QRectF(x + w * 0.22, y + h * 0.44, w * 0.56, h * 0.42), 4, 4)
            path = QPainterPath()
            path.moveTo(x + w * 0.32, y + h * 0.46)
            path.lineTo(x + w * 0.32, y + h * 0.36)
            path.cubicTo(x + w * 0.32, y + h * 0.12, x + w * 0.68, y + h * 0.12, x + w * 0.68, y + h * 0.36)
            path.lineTo(x + w * 0.68, y + h * 0.46)
            p.drawPath(path)
        elif name == "user":
            p.drawEllipse(QPointF(cx, y + h * 0.34), s * 0.16, s * 0.16)
            path = QPainterPath()
            path.moveTo(x + w * 0.18, y + h * 0.86)
            path.cubicTo(x + w * 0.18, y + h * 0.60, x + w * 0.82, y + h * 0.60, x + w * 0.82, y + h * 0.86)
            p.drawPath(path)
        elif name == "spark":
            p.drawLine(QPointF(cx, y + h * 0.10), QPointF(cx, y + h * 0.90))
            p.drawLine(QPointF(x + w * 0.10, cy), QPointF(x + w * 0.90, cy))
            p.drawLine(QPointF(x + w * 0.24, y + h * 0.24), QPointF(x + w * 0.76, y + h * 0.76))
            p.drawLine(QPointF(x + w * 0.76, y + h * 0.24), QPointF(x + w * 0.24, y + h * 0.76))
        p.restore()


class FishLogo(QWidget):
    def __init__(self, size: int = 30, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._phase = 0.0

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, qcolor(ACCENT))
        g.setColorAt(1, qcolor(SKY))
        path = QPainterPath()
        path.moveTo(r.x() + r.width() * 0.06, r.y() + r.height() * 0.50)
        path.cubicTo(
            r.x() + r.width() * 0.26,
            r.y() + r.height() * 0.20,
            r.x() + r.width() * 0.66,
            r.y() + r.height() * 0.20,
            r.x() + r.width() * 0.80,
            r.y() + r.height() * 0.50,
        )
        path.cubicTo(
            r.x() + r.width() * 0.66,
            r.y() + r.height() * 0.80,
            r.x() + r.width() * 0.26,
            r.y() + r.height() * 0.80,
            r.x() + r.width() * 0.06,
            r.y() + r.height() * 0.50,
        )
        tail = QPainterPath()
        tail.moveTo(r.x() + r.width() * 0.10, r.y() + r.height() * 0.50)
        tail.lineTo(r.x() + r.width() * 0.00, r.y() + r.height() * 0.28)
        tail.lineTo(r.x() + r.width() * 0.00, r.y() + r.height() * 0.72)
        tail.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawPath(path)
        p.setBrush(QColor(ACCENT))
        p.drawPath(tail)
        p.setBrush(QColor(BG0))
        p.drawEllipse(QPointF(r.x() + r.width() * 0.64, r.y() + r.height() * 0.43), r.width() * 0.045, r.height() * 0.045)
        p.setBrush(qcolor("#FFFFFF", 110))
        p.drawEllipse(QPointF(r.x() + r.width() * 0.655, r.y() + r.height() * 0.415), r.width() * 0.015, r.height() * 0.015)


class StatusDot(QWidget):
    def __init__(self, size: int = 10, parent=None):
        super().__init__(parent)
        self.setFixedSize(size + 10, size + 10)
        self._size = size
        self._level = "idle"
        self._phase = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(1800)
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._tick)
        self._anim.start()

    def _tick(self, v):
        self._phase = float(v)
        self.update()

    def set_level(self, level: str):
        if level != self._level:
            self._level = level
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = qcolor(LEVEL_COLOR.get(self._level, MUTED))
        cx, cy = self.width() / 2, self.height() / 2
        radius = self._size / 2
        pulse = 1.0 + 0.9 * self._phase
        glow = QColor(c)
        glow.setAlpha(int(58 * (1.0 - self._phase)))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QPointF(cx, cy), radius * pulse, radius * pulse)
        p.setBrush(c)
        p.drawEllipse(QPointF(cx, cy), radius, radius)
        p.setBrush(qcolor("#FFFFFF", 150))
        p.drawEllipse(QPointF(cx - radius * 0.3, cy - radius * 0.3), radius * 0.28, radius * 0.28)


class GlassCard(QFrame):
    def __init__(self, radius: int = 16, accent: str | None = None, parent=None):
        super().__init__(parent)
        self.radius = radius
        self.accent = accent
        self._hover = 0.0
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(180)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.valueChanged.connect(self._on_hover)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _on_hover(self, v):
        self._hover = float(v)
        self.update()

    def enterEvent(self, e):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, self.radius, self.radius)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0.0, qcolor("#122433", 235))
        g.setColorAt(0.55, qcolor("#0D1B29", 235))
        g.setColorAt(1.0, qcolor("#0A1622", 235))
        p.fillPath(path, QBrush(g))
        if self.accent:
            ag = QRadialGradient(QPointF(r.left() + 30, r.top() + 4), r.width() * 0.75)
            ag.setColorAt(0.0, qcolor(self.accent, int(30 + 24 * self._hover)))
            ag.setColorAt(1.0, qcolor(self.accent, 0))
            p.fillPath(path, QBrush(ag))
        border = mix(qcolor(LINE), qcolor(self.accent or ACCENT), 0.55 * self._hover)
        border.setAlpha(int(120 + 80 * self._hover))
        p.setPen(QPen(border, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        if self.accent:
            p.setPen(QPen(qcolor(self.accent, int(60 + 100 * self._hover)), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(r.left() + self.radius, r.top() + 0.8), QPointF(r.right() - self.radius, r.top() + 0.8))


class CardIcon(QWidget):
    def __init__(self, name: str, color: str = ACCENT, size: int = 38, parent=None):
        super().__init__(parent)
        self.name = name
        self.color = color
        self.setFixedSize(size, size)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(r, 11, 11)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, qcolor(self.color, 46))
        g.setColorAt(1, qcolor(self.color, 12))
        p.fillPath(path, QBrush(g))
        p.setPen(QPen(qcolor(self.color, 70), 1))
        p.drawPath(path)
        Icon.paint(p, self.name, QRectF(9, 9, self.width() - 18, self.height() - 18), qcolor(self.color), 1.6)


class StatCard(GlassCard):
    def __init__(self, title: str, icon: str, color: str = ACCENT, parent=None):
        super().__init__(radius=15, accent=color, parent=parent)
        self.setFixedHeight(112)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 13, 14, 13)
        lay.setSpacing(11)
        self.icon = CardIcon(icon, color, 38)
        lay.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(2)
        self.title = QLabel(title)
        self.title.setFont(font(10, 600, spacing=1.2))
        self.title.setStyleSheet("color: %s;" % DIM)
        self.state = QLabel("检测中…")
        self.state.setFont(font(16, 700))
        self.state.setStyleSheet("color: %s;" % TEXT)
        self.meta = QLabel("")
        self.meta.setFont(font(10, 400))
        self.meta.setStyleSheet("color: %s;" % DIM)
        self.meta.setWordWrap(False)
        col.addWidget(self.title)
        col.addSpacing(1)
        col.addWidget(self.state)
        col.addWidget(self.meta)
        col.addStretch(1)
        lay.addLayout(col, 1)
        self.dot = StatusDot(9)
        lay.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignTop)

    def set_data(self, state: str, meta: str, level: str):
        self.state.setText(state)
        self.meta.setText(meta)
        color = LEVEL_COLOR.get(level, MUTED)
        self.state.setStyleSheet("color: %s;" % (color if level in ("ok", "warn", "bad") else TEXT))
        self.dot.set_level(level)
        self.setToolTip(meta)


class Pill(QWidget):
    def __init__(self, text: str = "待启动", level: str = "idle", parent=None):
        super().__init__(parent)
        self._text = text
        self._level = level
        self.setFont(font(10, 600))
        self._recalc()

    def _recalc(self):
        fm = QFontMetrics(self.font())
        self.setFixedSize(fm.horizontalAdvance(self._text) + 32, 24)

    def set_state(self, text: str, level: str):
        self._text = text
        self._level = level
        self._recalc()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        c = qcolor(LEVEL_COLOR.get(self._level, MUTED))
        p.setBrush(qcolor(c, 24))
        p.setPen(QPen(qcolor(c, 80), 1))
        p.drawRoundedRect(r, 12, 12)
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(13, self.height() / 2), 3.2, 3.2)
        p.setPen(qcolor(c))
        p.setFont(self.font())
        p.drawText(QRectF(21, 0, self.width() - 25, self.height()), Qt.AlignmentFlag.AlignVCenter, self._text)


class PrimaryButton(QAbstractButton):
    def __init__(self, text: str = "一键启动", level: str = "start", parent=None):
        super().__init__(parent)
        self.setText(text)
        self.level = level
        self.busy = False
        self._hover = 0.0
        self._press = 0.0
        self._phase = 0.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(238, 64)
        self.setFont(font(14, 700))
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(160)
        self._hover_anim.valueChanged.connect(self._on_hover)
        self._timer = QTimer(self)
        self._timer.setInterval(32)
        self._timer.timeout.connect(self._spin)

    def _on_hover(self, v):
        self._hover = float(v)
        self.update()

    def _spin(self):
        self._phase = (self._phase + 0.08) % 1.0
        self.update()

    def enterEvent(self, e):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._press = 1.0
        self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._press = 0.0
        self.update()
        super().mouseReleaseEvent(e)

    def set_state(self, text: str, level: str, busy: bool = False):
        self.setText(text)
        self.level = level
        self.busy = busy
        self.setEnabled(not busy)
        if busy:
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _colors(self):
        if self.level == "ok":
            return GREEN, "#1AAE84"
        if self.level == "warn":
            return AMBER, "#E09A3E"
        if self.level == "off":
            return "#3B5369", "#263C4F"
        return ACCENT, SKY

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c1, c2 = self._colors()
        outer = QRectF(6, 6, self.width() - 12, self.height() - 12)
        # 外发光
        glow = QRadialGradient(outer.center(), outer.width() * 0.62)
        glow.setColorAt(0.0, qcolor(c1, int(46 + 40 * self._hover)))
        glow.setColorAt(0.55, qcolor(c2, int(18 + 28 * self._hover)))
        glow.setColorAt(1.0, qcolor(c2, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(outer.adjusted(-6, -4, 4, 6))
        # 主体
        btn = outer.adjusted(0, 0, 0, -self._press * 1.5)
        path = QPainterPath()
        path.addRoundedRect(btn, btn.height() / 2, btn.height() / 2)
        g = QLinearGradient(btn.topLeft(), btn.bottomRight())
        g.setColorAt(0.0, qcolor(c1))
        g.setColorAt(1.0, qcolor(c2))
        p.fillPath(path, QBrush(g))
        # 顶部高光
        hl = QLinearGradient(btn.topLeft(), btn.bottomLeft())
        hl.setColorAt(0.0, qcolor("#FFFFFF", 46))
        hl.setColorAt(0.5, qcolor("#FFFFFF", 0))
        p.fillPath(path, QBrush(hl))
        p.setPen(QPen(qcolor("#FFFFFF", 55), 1))
        p.drawPath(path)
        if self.busy:
            cx = btn.left() + 30
            cy = btn.center().y()
            p.setPen(QPen(qcolor("#FFFFFF", 210), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(cx - 7, cy - 7, 14, 14), int(-self._phase * 360 * 16), int(250 * 16))
            icon_rect = None
        else:
            icon_rect = QRectF(btn.left() + 22, btn.center().y() - 9, 18, 18)
            name = "check" if self.level == "ok" else ("qr" if self.level == "warn" else "power")
            Icon.paint(p, name, icon_rect, qcolor("#04231F"), 2.0)
        p.setPen(qcolor("#04231F"))
        p.setFont(self.font())
        text_rect = btn.adjusted(48 if icon_rect else 46, 0, -12, 0)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.text())
        # 内描边
        p.setPen(QPen(qcolor("#FFFFFF", 60), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)


class SecondaryButton(QAbstractButton):
    def __init__(self, text: str, icon: str | None = None, accent: str = ACCENT, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.icon_name = icon
        self.accent = accent
        self._hover = 0.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(font(11, 600))
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(150)
        self._anim.valueChanged.connect(self._on_hover)
        self._recalc()

    def _on_hover(self, v):
        self._hover = float(v)
        self.update()

    def _recalc(self):
        fm = QFontMetrics(self.font())
        w = fm.horizontalAdvance(self.text()) + (38 if self.icon_name else 28)
        self.setFixedSize(max(58, w), 30)

    def enterEvent(self, e):
        self._anim.stop(); self._anim.setStartValue(self._hover); self._anim.setEndValue(1.0); self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop(); self._anim.setStartValue(self._hover); self._anim.setEndValue(0.0); self._anim.start()
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.45)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        c = qcolor(self.accent)
        bg = mix(qcolor("#132536"), qcolor(self.accent), 0.12 * self._hover)
        bg.setAlpha(230)
        p.setBrush(bg)
        p.setPen(QPen(mix(qcolor(LINE), c, 0.5 * self._hover), 1))
        p.drawRoundedRect(r, 9, 9)
        x = 13
        if self.icon_name:
            Icon.paint(p, self.icon_name, QRectF(x, self.height() / 2 - 7, 14, 14), mix(qcolor(DIM), c, self._hover), 1.6)
            x += 20
        p.setPen(mix(qcolor(TEXT_SOFT), c, self._hover))
        p.setFont(self.font())
        p.drawText(QRectF(x, 0, self.width() - x - 8, self.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())


class IconButton(QAbstractButton):
    def __init__(self, icon: str, tooltip: str = "", danger: bool = False, size: int = 30, parent=None):
        super().__init__(parent)
        self.icon_name = icon
        self.danger = danger
        self._hover = 0.0
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(140)
        self._anim.valueChanged.connect(self._on_hover)

    def _on_hover(self, v):
        self._hover = float(v)
        self.update()

    def enterEvent(self, e):
        self._anim.stop(); self._anim.setStartValue(self._hover); self._anim.setEndValue(1.0); self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop(); self._anim.setStartValue(self._hover); self._anim.setEndValue(0.0); self._anim.start()
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._hover > 0.01:
            color = qcolor(RED, int(38 * self._hover)) if self.danger else qcolor("#FFFFFF", int(18 * self._hover))
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(2, 2, self.width() - 4, self.height() - 4))
        color = mix(qcolor(DIM), qcolor(RED if self.danger else TEXT), self._hover)
        Icon.paint(p, self.icon_name, QRectF(8, 8, self.width() - 16, self.height() - 16), color, 1.8)


class ToggleSwitch(QAbstractButton):
    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(42, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pos = 1.0 if checked else 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_pos)
        self.toggled.connect(self._animate)

    def _on_pos(self, v):
        self._pos = float(v)
        self.update()

    def _animate(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0.5, 4, self.width() - 1, self.height() - 8)
        off, on = qcolor("#1B3042"), qcolor(ACCENT, 210)
        bg = mix(off, on, self._pos)
        p.setBrush(bg)
        p.setPen(QPen(mix(qcolor(LINE), qcolor(ACCENT), self._pos), 1))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        knob_x = 4 + (self.width() - 8 - (r.height() - 4)) * self._pos
        p.setBrush(qcolor("#F4FAFF"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(knob_x, r.top() + 2, r.height() - 4, r.height() - 4))


class TabButton(QAbstractButton):
    def __init__(self, text: str, active: bool = False, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setChecked(active)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(font(10, 600))
        self._recalc()
        self._hover = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(120)
        self._anim.valueChanged.connect(lambda v: (setattr(self, "_hover", float(v)), self.update()))

    def _recalc(self):
        fm = QFontMetrics(self.font())
        self.setFixedSize(max(46, fm.horizontalAdvance(self.text()) + 20), 26)

    def enterEvent(self, e):
        if not self.isChecked():
            self._anim.stop(); self._anim.setStartValue(self._hover); self._anim.setEndValue(1.0); self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop(); self._anim.setStartValue(self._hover); self._anim.setEndValue(0.0); self._anim.start()
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0.5, 2.5, self.width() - 1, self.height() - 5)
        if self.isChecked():
            p.setBrush(qcolor(ACCENT, 25))
            p.setPen(QPen(qcolor(ACCENT, 70), 1))
            p.drawRoundedRect(r, 7, 7)
            color = qcolor(ACCENT)
        else:
            p.setBrush(qcolor("#FFFFFF", int(8 + 8 * self._hover)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(r, 7, 7)
            color = mix(qcolor(DIM), qcolor(TEXT), self._hover)
        p.setPen(color)
        p.setFont(self.font())
        p.drawText(QRectF(0, 0, self.width(), self.height()), Qt.AlignmentFlag.AlignCenter, self.text())


class StepBar(QWidget):
    def __init__(self, steps: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.steps = steps or ["AstrBot", "NapCat", "QQ"]
        self.active = -1
        self.setFixedHeight(30)

    def set_active(self, idx: int):
        if idx != self.active:
            self.active = idx
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        n = len(self.steps)
        w = self.width()
        gap = w / max(1, n)
        centers = [gap * (i + 0.5) for i in range(n)]
        y = 8
        p.setPen(QPen(qcolor(LINE), 1.2))
        for i in range(n - 1):
            p.drawLine(QPointF(centers[i] + 8, y), QPointF(centers[i + 1] - 8, y))
        for i, name in enumerate(self.steps):
            on = self.active >= i
            current = self.active == i
            c = qcolor(ACCENT if on else "#2B4356")
            p.setBrush(c if on else qcolor("#142634"))
            p.setPen(QPen(c, 1.2))
            p.drawEllipse(QPointF(centers[i], y), 4.5 if current else 3.6, 4.5 if current else 3.6)
            p.setPen(qcolor(ACCENT if on else MUTED))
            p.setFont(font(9, 700 if current else 500))
            p.drawText(QRectF(centers[i] - gap / 2, 15, gap, 14), Qt.AlignmentFlag.AlignCenter, name)


class HeroCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(radius=20, accent=ACCENT, parent=parent)
        self.setFixedHeight(150)
        self._phase = 0.0
        self._busy = False
        self._wave_timer = QTimer(self)
        self._wave_timer.setInterval(50)
        self._wave_timer.timeout.connect(self._tick)
        self._wave_timer.start()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 20, 22, 18)
        lay.setSpacing(18)

        left = QVBoxLayout()
        left.setSpacing(4)
        self.eyebrow = QLabel("DEEP SEA CONTROL")
        self.eyebrow.setFont(font(9, 700, spacing=1.8))
        self.eyebrow.setStyleSheet("color: %s;" % qcolor(ACCENT).name())
        self.title = QLabel("开始今天的陪伴")
        self.title.setFont(font(27, 700))
        self.title.setStyleSheet("color: %s;" % TEXT)
        self.subtitle = QLabel("一键启动 AstrBot、NapCat，并快速登录 QQ")
        self.subtitle.setFont(font(12, 400))
        self.subtitle.setStyleSheet("color: %s;" % DIM)
        self.meta = QLabel("账号 2960405592 · 深海守护已就绪")
        self.meta.setFont(font(10, 400))
        self.meta.setStyleSheet("color: %s;" % MUTED)
        left.addWidget(self.eyebrow)
        left.addSpacing(2)
        left.addWidget(self.title)
        left.addWidget(self.subtitle)
        left.addStretch(1)
        left.addWidget(self.meta)

        right = QVBoxLayout()
        right.setSpacing(4)
        right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.button = PrimaryButton("一键启动", "start")
        self.steps = StepBar()
        self.steps.setFixedWidth(232)
        right.addWidget(self.button, 0, Qt.AlignmentFlag.AlignRight)
        right.addWidget(self.steps, 0, Qt.AlignmentFlag.AlignRight)
        lay.addLayout(left, 1)
        lay.addLayout(right, 0)

    def _tick(self):
        if not self.isVisible():
            return
        self._phase = (self._phase + 0.008) % 1.0
        self.update()

    def set_content(self, title: str, subtitle: str, meta: str, button: str, level: str, busy: bool = False):
        self.title.setText(title)
        self.subtitle.setText(subtitle)
        self.meta.setText(meta)
        self._busy = busy
        self.button.set_state(button, level, busy)

    def set_phase(self, idx: int):
        self.steps.set_active(idx)

    def paintEvent(self, _):
        super().paintEvent(_)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setClipPath(self._card_path())
        # 背景光晕
        glow = QRadialGradient(QPointF(self.width() * 0.80, self.height() * 0.18), self.width() * 0.40)
        glow.setColorAt(0.0, qcolor(ACCENT, 26))
        glow.setColorAt(0.55, qcolor(SKY, 9))
        glow.setColorAt(1.0, qcolor(SKY, 0))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect())
        # 缓慢波纹
        for k in range(3):
            path = QPainterPath()
            base_y = self.height() - 10 + k * 3
            path.moveTo(-10, base_y)
            steps = 10
            for i in range(steps + 1):
                x = -10 + (self.width() + 20) * i / steps
                y = base_y + math.sin(self._phase * 2 * math.pi + i * 0.55 + k * 1.1) * (4 + k * 2)
                path.lineTo(x, y)
            p.setPen(QPen(qcolor(ACCENT if k == 0 else SKY, 20 - k * 5), 1.1))
            p.drawPath(path)
        # busy 时顶部流光
        if self._busy:
            band = QLinearGradient(0, 0, self.width(), 0)
            pos = self._phase
            band.setColorAt(max(0.0, pos - 0.12), qcolor(ACCENT, 0))
            band.setColorAt(min(1.0, pos), qcolor(ACCENT, 180))
            band.setColorAt(min(1.0, pos + 0.12), qcolor(ACCENT, 0))
            p.setPen(QPen(QBrush(band), 1.6))
            p.drawLine(QPointF(18, 1), QPointF(self.width() - 18, 1))

    def _card_path(self) -> QPainterPath:
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, self.radius, self.radius)
        return path


class LoginBar(GlassCard):
    def __init__(self, parent=None):
        super().__init__(radius=15, accent=SKY, parent=parent)
        self.setFixedHeight(56)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 12, 10)
        lay.setSpacing(10)
        self.icon = CardIcon("key", SKY, 34)
        lay.addWidget(self.icon)
        col = QVBoxLayout()
        col.setSpacing(1)
        self.title = QLabel("登录守护")
        self.title.setFont(font(9, 700, spacing=1.0))
        self.title.setStyleSheet("color: %s;" % MUTED)
        self.text = QLabel("检查登录状态…")
        self.text.setFont(font(12, 600))
        self.text.setStyleSheet("color: %s;" % TEXT)
        col.addWidget(self.title)
        col.addWidget(self.text)
        lay.addLayout(col, 1)
        self.chip = QLabel("2960405592")
        self.chip.setFont(num_font(11, 600))
        self.chip.setStyleSheet(
            "color: %s; background: rgba(56,189,248,22); border: 1px solid rgba(56,189,248,60);"
            " border-radius: 9px; padding: 4px 9px;" % SKY
        )
        lay.addWidget(self.chip, 0, Qt.AlignmentFlag.AlignVCenter)
        self.button = SecondaryButton("扫码登录", "qr", ACCENT)
        lay.addWidget(self.button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.dot = StatusDot(8)
        lay.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_data(self, logged: bool, account: str, quick_ready: bool | None, phase: str, error: str = "", running: bool = False):
        self.chip.setText(account or "未绑定")
        if logged:
            self.text.setText("已登录 · 登录凭证已保存")
            self.text.setStyleSheet("color: %s;" % GREEN)
            self.button.setText("查看登录")
            self.dot.set_level("ok")
            self.button.setEnabled(True)
        elif not running:
            self.text.setText("服务未启动 · 启动后扫码登录")
            self.text.setStyleSheet("color: %s;" % DIM)
            self.button.setText("扫码登录")
            self.dot.set_level("idle")
            self.button.setEnabled(False)
        elif error:
            self.text.setText("登录状态未知 · WebUI 未就绪")
            self.text.setStyleSheet("color: %s;" % AMBER)
            self.button.setText("扫码登录")
            self.dot.set_level("warn")
            self.button.setEnabled(True)
        else:
            if quick_ready:
                self.text.setText("待登录 · 下次启动可快速登录")
            else:
                self.text.setText("待登录 · 首次扫码后免扫码")
            self.text.setStyleSheet("color: %s;" % AMBER)
            self.button.setText("扫码登录")
            self.dot.set_level("warn")
            self.button.setEnabled(True)
        self.button._recalc()
        self.button.update()


class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(46)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 8, 12, 6)
        lay.setSpacing(9)
        self.logo = FishLogo(28)
        lay.addWidget(self.logo)
        self.title = QLabel("大肥鱼控制台")
        self.title.setFont(font(14, 700))
        self.title.setStyleSheet("color: %s;" % TEXT)
        lay.addWidget(self.title)
        sep = QLabel("·")
        sep.setStyleSheet("color: %s; padding: 0 2px;" % MUTED)
        lay.addWidget(sep)
        self.subtitle = QLabel("ASTRBOT / NAPCAT / QQ")
        self.subtitle.setFont(font(8, 600, spacing=1.3))
        self.subtitle.setStyleSheet("color: %s;" % MUTED)
        lay.addWidget(self.subtitle)
        lay.addStretch(1)
        self.pill = Pill("待启动", "idle")
        lay.addWidget(self.pill, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addSpacing(6)
        self.min_btn = IconButton("minimize", "最小化到任务栏")
        self.settings_btn = IconButton("settings", "设置")
        self.close_btn = IconButton("close", "最小化到托盘", danger=True)
        lay.addWidget(self.min_btn)
        lay.addWidget(self.settings_btn)
        lay.addWidget(self.close_btn)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(qcolor("#FFFFFF", 12), 1))
        p.drawLine(16, self.height() - 1, self.width() - 16, self.height() - 1)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            win = self.window()
            handle = win.windowHandle()
            if handle:
                handle.startSystemMove()
                return
        super().mousePressEvent(e)


class LogPanel(QWidget):
    target_changed = Signal(str)
    expanded_changed = Signal(bool)

    TABS = [("console", "控制台"), ("astrbot", "AstrBot"), ("napcat", "NapCat"), ("qq", "QQ")]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(42)
        self._expanded = False
        self._target = "console"
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(240)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.header = QWidget()
        self.header.setFixedHeight(42)
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(16, 6, 10, 6)
        hl.setSpacing(8)
        self.live = StatusDot(7)
        self.live.set_level("ok")
        hl.addWidget(self.live)
        cap = QLabel("实时日志")
        cap.setFont(font(11, 600))
        cap.setStyleSheet("color: %s;" % TEXT_SOFT)
        hl.addWidget(cap)
        hl.addSpacing(4)
        self.tabs: dict[str, TabButton] = {}
        for key, label in self.TABS:
            b = TabButton(label, key == self._target)
            b.clicked.connect(lambda _=False, k=key: self.set_target(k))
            self.tabs[key] = b
            hl.addWidget(b)
        hl.addStretch(1)
        self.copy_btn = IconButton("copy", "复制当前日志")
        self.clear_btn = IconButton("trash", "清空显示")
        self.toggle_btn = IconButton("chevron-down", "展开日志")
        hl.addWidget(self.copy_btn)
        hl.addWidget(self.clear_btn)
        hl.addWidget(self.toggle_btn)
        root.addWidget(self.header)

        self.body = QPlainTextEdit()
        self.body.setReadOnly(True)
        self.body.setFrameShape(QFrame.Shape.NoFrame)
        self.body.setFont(mono_font(11))
        self.body.setStyleSheet(
            "QPlainTextEdit { background: transparent; color: #AFC5D8; padding: 0 16px 10px 16px;"
            " selection-background-color: #1B4A54; }"
        )
        self.body.setMaximumBlockCount(3000)
        self.body.setVisible(False)
        root.addWidget(self.body, 1)

        self.toggle_btn.clicked.connect(self.toggle)
        self.copy_btn.clicked.connect(self._copy)
        self.clear_btn.clicked.connect(self.body.clear)

        self._indicator = QVariantAnimation(self)
        self._indicator.setDuration(1600)
        self._indicator.setLoopCount(-1)
        self._indicator.valueChanged.connect(self._indicator_tick)
        self._indicator.start()

    def _indicator_tick(self, _):
        self.live.update()

    def _on_anim(self, v):
        h = int(v)
        self.setFixedHeight(h)
        if h > 44:
            self.body.setVisible(True)

    def toggle(self):
        self._expanded = not self._expanded
        target = 200 if self._expanded else 42
        self._anim.stop()
        self._anim.setStartValue(self.height())
        self._anim.setEndValue(target)
        self._anim.start()
        self.toggle_btn.icon_name = "chevron-up" if self._expanded else "chevron-down"
        self.toggle_btn.setToolTip("收起日志" if self._expanded else "展开日志")
        self.toggle_btn.update()
        if not self._expanded:
            QTimer.singleShot(
                250,
                lambda: self.body.setVisible(False) if not self._expanded else None,
            )
        self.expanded_changed.emit(self._expanded)

    def set_target(self, key: str):
        self._target = key
        for k, b in self.tabs.items():
            b.setChecked(k == key)
        self.target_changed.emit(key)

    def target(self) -> str:
        return self._target

    def set_text(self, text: str):
        sb = self.body.verticalScrollBar()
        at_bottom = sb.value() >= sb.maximum() - 24
        if self.body.toPlainText() == text:
            return
        self.body.setPlainText(text or "(暂无日志)")
        if at_bottom:
            sb.setValue(sb.maximum())

    def _copy(self):
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.body.toPlainText())

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, 14, 14)
        p.setBrush(qcolor("#07111B", 210))
        p.setPen(QPen(qcolor("#FFFFFF", 14), 1))
        p.drawPath(path)
        if self._expanded:
            p.setPen(QPen(qcolor("#FFFFFF", 12), 1))
            p.drawLine(16, 42, self.width() - 16, 42)


class RecentEvents(GlassCard):
    """填补空白区域的最近动态；展开日志时自动让位。"""
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(radius=15, accent=BLUE, parent=parent)
        self.setMinimumHeight(96)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 8)
        lay.setSpacing(3)
        head = QHBoxLayout()
        head.setSpacing(7)
        dot = StatusDot(6)
        dot.set_level("info")
        head.addWidget(dot)
        title = QLabel("最近动态")
        title.setFont(font(10, 700, spacing=1.0))
        title.setStyleSheet("color: %s;" % TEXT_SOFT)
        head.addWidget(title)
        head.addStretch(1)
        hint = QLabel("点击查看完整日志  ›")
        hint.setFont(font(9, 500))
        hint.setStyleSheet("color: %s;" % MUTED)
        head.addWidget(hint)
        lay.addLayout(head)
        self.rows = QVBoxLayout()
        self.rows.setSpacing(4)
        lay.addLayout(self.rows, 1)
        self.hint = QLabel("控制台已就绪 · 等待一键启动")
        self.hint.setFont(font(9, 400))
        self.hint.setStyleSheet("color: %s;" % MUTED)
        self.hint.setVisible(True)
        lay.addWidget(self.hint)
        self._events = []

    def set_summary(self, text: str):
        if text and text != self.hint.text():
            self.hint.setText(text)

    def set_events(self, events):
        self._events = list(events)
        while self.rows.count():
            item = self.rows.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        if not events:
            empty = QLabel("暂无动态 · 启动后会显示关键事件")
            empty.setFont(font(10, 400))
            empty.setStyleSheet("color: %s;" % MUTED)
            self.rows.addWidget(empty)
            self.rows.addStretch(1)
            self.hint.setVisible(True)
            make_labels_transparent(self)
            return
        for t, text, level in events[-4:]:
            row = QWidget()
            hl = QHBoxLayout(row)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(8)
            tm = QLabel(t)
            tm.setFont(num_font(9, 500))
            tm.setStyleSheet("color: %s;" % MUTED)
            tm.setFixedWidth(44)
            hl.addWidget(tm)
            d = StatusDot(5)
            d.set_level(level)
            hl.addWidget(d, 0, Qt.AlignmentFlag.AlignVCenter)
            txt = QLabel(text)
            txt.setFont(font(10, 500))
            txt.setStyleSheet("color: %s;" % (TEXT_SOFT if level != "warn" else AMBER))
            txt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            txt.setToolTip(text)
            hl.addWidget(txt, 1)
            self.rows.addWidget(row)
        self.rows.addStretch(1)
        self.hint.setVisible(True)
        make_labels_transparent(self)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(e)


class FooterBar(QWidget):
    dashboard_clicked = Signal()
    logs_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(22)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(7)
        self.dot = StatusDot(6)
        self.dot.set_level("idle")
        lay.addWidget(self.dot)
        self.state = QLabel("控制台在托盘运行")
        self.state.setFont(font(9, 500))
        self.state.setStyleSheet("color: %s;" % MUTED)
        lay.addWidget(self.state)
        lay.addStretch(1)
        self.dash = _Link("AstrBot 后台", "external")
        self.dash.clicked.connect(self.dashboard_clicked.emit)
        self.logs = _Link("日志目录", "folder")
        self.logs.clicked.connect(self.logs_clicked.emit)
        lay.addWidget(self.dash)
        lay.addWidget(self.logs)
        self.version = QLabel("v2.0")
        self.version.setFont(num_font(9, 500))
        self.version.setStyleSheet("color: %s;" % MUTED)
        lay.addWidget(self.version)

    def set_state(self, text: str, level: str = "idle"):
        self.state.setText(text)
        self.dot.set_level(level)


class _Link(QAbstractButton):
    def __init__(self, text: str, icon: str, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.icon_name = icon
        self._hover = 0.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(font(9, 500))
        fm = QFontMetrics(self.font())
        self.setFixedSize(fm.horizontalAdvance(text) + 26, 18)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(120)
        self._anim.valueChanged.connect(lambda v: (setattr(self, "_hover", float(v)), self.update()))

    def enterEvent(self, e):
        self._anim.stop(); self._anim.setStartValue(self._hover); self._anim.setEndValue(1.0); self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop(); self._anim.setStartValue(self._hover); self._anim.setEndValue(0.0); self._anim.start()
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = mix(qcolor(MUTED), qcolor(ACCENT), self._hover)
        Icon.paint(p, self.icon_name, QRectF(0, 3, 12, 12), c, 1.4)
        p.setPen(c)
        p.setFont(self.font())
        p.drawText(QRectF(16, 0, self.width() - 16, self.height()), Qt.AlignmentFlag.AlignVCenter, self.text())


class Toast(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._label = QLabel(self)
        self._label.setFont(font(11, 500))
        self._label.setStyleSheet("color: %s;" % TEXT)
        self._dot = StatusDot(7, self)
        self._level = "ok"
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide_animated)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(220)
        self._anim.valueChanged.connect(self._tick)
        self._phase = 0.0
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(0.0)
        self.hide()

    def show_message(self, text: str, level: str = "ok", ms: int = 3200):
        self._level = level
        self._dot.set_level(level)
        self._label.setText(text)
        fm = QFontMetrics(self._label.font())
        w = min(620, fm.horizontalAdvance(text) + 58)
        self.setFixedSize(w, 40)
        self._label.setGeometry(36, 0, w - 46, 40)
        self._dot.move(14, 13)
        self.reposition()
        self.show()
        self.raise_()
        self._timer.start(ms)
        self._phase = 0.0
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def reposition(self):
        if self.parent():
            pw, ph = self.parent().width(), self.parent().height()
            self.move(int((pw - self.width()) / 2), ph - 96 - int(10 * (1 - self._phase)))

    def _tick(self, v):
        self._phase = float(v)
        self._effect.setOpacity(self._phase)
        self.reposition()
        self.update()

    def hide_animated(self):
        self._anim.stop()
        self._anim.setStartValue(self._phase)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(lambda: self.hide())
        self._anim.start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setBrush(qcolor("#0F2030", 248))
        p.setPen(QPen(qcolor(LEVEL_COLOR.get(self._level, ACCENT), 90), 1))
        p.drawRoundedRect(r, 13, 13)


class QRWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.matrix = None
        self.pixmap = None
        self.placeholder = "正在获取二维码…"
        self.setFixedSize(272, 272)

    def set_placeholder(self, text: str):
        self.matrix = None
        self.pixmap = None
        self.placeholder = text
        self.update()

    def set_matrix(self, matrix):
        self.matrix = matrix
        self.pixmap = None
        self.update()

    def set_png(self, data: bytes):
        pm = QPixmap()
        if pm.loadFromData(data, "PNG"):
            self.pixmap = pm
            self.matrix = None
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())
        p.setBrush(qcolor("#FFFFFF"))
        p.setPen(QPen(qcolor("#FFFFFF"), 1))
        p.drawRoundedRect(r, 18, 18)
        inner = r.adjusted(18, 18, -18, -18)
        if self.matrix:
            n = len(self.matrix)
            if n:
                cell = inner.width() / n
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qcolor("#07101A"))
                for y, row in enumerate(self.matrix):
                    for x, on in enumerate(row):
                        if on:
                            p.drawRect(QRectF(inner.x() + x * cell, inner.y() + y * cell, cell + 0.35, cell + 0.35))
        elif self.pixmap:
            path = QPainterPath()
            path.addRoundedRect(inner, 10, 10)
            p.setClipPath(path)
            p.drawPixmap(inner.toRect(), self.pixmap)
        else:
            p.setPen(qcolor("#5C7285"))
            if self.placeholder.strip() in ("✓", "√"):
                p.setPen(qcolor(GREEN))
                p.setFont(font(54, 700))
                p.drawText(inner, Qt.AlignmentFlag.AlignCenter, "✓")
            else:
                p.setFont(font(12, 500))
                p.drawText(inner.adjusted(14, 0, -14, 0), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.placeholder)
