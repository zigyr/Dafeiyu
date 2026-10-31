# -*- coding: utf-8 -*-
"""大肥鱼控制台 - 颜色、字体与全局样式。"""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication

# 深海夜色
BG0 = "#050A11"
BG1 = "#08131F"
BG2 = "#0B1A29"
CARD = "#0E1C2A"
CARD_HI = "#132638"
LINE = "#1C3247"
TEXT = "#E9F3FC"
TEXT_SOFT = "#C3D5E6"
DIM = "#8299AF"
MUTED = "#5A7188"

ACCENT = "#2DE2C5"
ACCENT_DEEP = "#12B8A6"
SKY = "#38BDF8"
BLUE = "#6366F1"
GREEN = "#3DDC97"
AMBER = "#F6C76B"
CORAL = "#FF8A7A"
RED = "#FF6B81"

FONT_UI = "Microsoft YaHei UI"
FONT_NUM = "Segoe UI Variable Display"
FONT_MONO = "Cascadia Mono"


def qcolor(value: str, alpha: int = 255) -> QColor:
    c = QColor(value)
    c.setAlpha(alpha)
    return c


def font(size: int, weight: int = 400, family: str = FONT_UI, spacing: float = 0) -> QFont:
    f = QFont(family)
    f.setPixelSize(max(8, int(size)))
    f.setWeight(QFont.Weight(weight))
    if spacing:
        f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return f


def num_font(size: int, weight: int = 600) -> QFont:
    f = QFont(FONT_NUM)
    f.setPixelSize(max(8, int(size)))
    f.setWeight(QFont.Weight(weight))
    f.setStyleHint(QFont.StyleHint.SansSerif)
    return f


def mono_font(size: int = 12) -> QFont:
    f = QFont(FONT_MONO)
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setPixelSize(size)
    return f


GLOBAL_QSS = f"""
* {{
    outline: none;
}}
QLabel {{
    background: transparent;
}}
QToolTip {{
    background: #101F2E;
    color: {TEXT};
    border: 1px solid {LINE};
    border-radius: 8px;
    padding: 6px 9px;
    font-size: 12px;
}}
QMenu {{
    background: #0D1A27;
    color: {TEXT};
    border: 1px solid {LINE};
    border-radius: 12px;
    padding: 7px;
    font-family: "{FONT_UI}";
    font-size: 12px;
}}
QMenu::item {{
    padding: 8px 28px 8px 30px;
    border-radius: 8px;
    margin: 1px 3px;
}}
QMenu::item:selected {{
    background: #163244;
    color: #FFFFFF;
}}
QMenu::item:disabled {{
    color: {MUTED};
}}
QMenu::separator {{
    height: 1px;
    background: {LINE};
    margin: 6px 10px;
}}
QLineEdit {{
    background: #0A1622;
    color: {TEXT};
    border: 1px solid {LINE};
    border-radius: 9px;
    padding: 8px 11px;
    selection-background-color: #1B4A54;
    font-family: "{FONT_UI}";
    font-size: 12px;
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT};
    background: #0C1A28;
}}
QLineEdit:disabled {{
    color: {MUTED};
    background: #0A131C;
}}
QComboBox {{
    background: #0A1622;
    color: {TEXT};
    border: 1px solid {LINE};
    border-radius: 9px;
    padding: 7px 10px;
    font-family: "{FONT_UI}";
    font-size: 12px;
}}
QComboBox:focus {{ border: 1px solid {ACCENT}; }}
QComboBox QAbstractItemView {{
    background: #0E1B28;
    color: {TEXT};
    border: 1px solid {LINE};
    selection-background-color: #173646;
    padding: 4px;
    outline: none;
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 9px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #244355;
    border-radius: 4px;
    min-height: 26px;
}}
QScrollBar::handle:vertical:hover {{ background: #2F5A6E; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{
    background: transparent; height: 9px; margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #244355; border-radius: 4px; min-width: 26px;
}}
QPlainTextEdit, QTextEdit {{
    background: transparent;
    color: #BED2E4;
    border: none;
    selection-background-color: #1B4A54;
    font-family: "{FONT_MONO}", "Consolas", monospace;
    font-size: 11px;
}}
QCheckBox {{
    color: {TEXT_SOFT};
    font-family: "{FONT_UI}";
    font-size: 12px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border-radius: 5px;
    border: 1px solid {LINE};
    background: #0A1622;
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
}}
QPushButton {{ font-family: "{FONT_UI}"; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(GLOBAL_QSS)
