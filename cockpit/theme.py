"""The single source of Wiki-Forge's visual style (the "Modern Dark" theme).

Centralizes all styling per DESIGN.md: one QSS string plus the bundled font, applied
once to the whole QApplication. Widgets are styled globally, so the shell and every
plugin are themed without per-widget code.
"""
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

FONT_PATH = Path(__file__).resolve().parent / "assets" / "fonts" / "Lexend-Light.ttf"

# --- Palette (DESIGN.md) ---------------------------------------------------
_BG = "rgb(30, 30, 30)"
_SURFACE = "rgb(38, 38, 38)"
_ACCENT = "#2B79C2"
_TEXT = "rgb(230, 230, 230)"
_TEXT_DIM = "rgb(150, 150, 150)"
_BTN = "rgba(60, 60, 60, 80)"
_BTN_HOVER = "rgba(30, 30, 30, 180)"

STYLESHEET = f"""
* {{
    color: {_TEXT};
    font-size: 13pt;
    selection-background-color: {_ACCENT};
    selection-color: {_TEXT};
}}

QMainWindow, QWidget, QDialog {{
    background-color: {_BG};
}}

QLabel {{
    color: {_ACCENT};
    font-size: 12pt;
    background: transparent;
}}

/* --- Tabs --------------------------------------------------------------- */
QTabWidget::pane {{
    border: 2px solid {_ACCENT};
    border-radius: 15px;
    top: -1px;
    background-color: {_SURFACE};
}}
QTabBar::tab {{
    color: {_TEXT_DIM};
    background-color: {_BTN};
    border: 2px solid transparent;
    border-top-left-radius: 15px;
    border-top-right-radius: 15px;
    padding: 8px 18px;
    margin-right: 4px;
    font-size: 14pt;
}}
QTabBar::tab:selected {{
    color: {_TEXT};
    border: 2px solid {_ACCENT};
    border-bottom-color: {_SURFACE};
}}
QTabBar::tab:hover {{
    color: {_TEXT};
}}

/* --- Buttons ------------------------------------------------------------ */
QPushButton {{
    color: {_TEXT};
    background-color: {_BTN};
    border: 2px solid {_ACCENT};
    border-radius: 15px;
    padding: 6px 16px;
    font-size: 14pt;
}}
QPushButton:hover {{
    background-color: {_BTN_HOVER};
    border: 2px solid {_TEXT};
}}
QPushButton:pressed {{
    background-color: {_ACCENT};
    color: {_BG};
}}
QPushButton:disabled {{
    color: {_TEXT_DIM};
    border-color: {_TEXT_DIM};
}}

/* --- Inputs ------------------------------------------------------------- */
QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {{
    background-color: {_SURFACE};
    border: 2px solid {_ACCENT};
    border-radius: 15px;
    padding: 5px 10px;
    font-size: 14pt;
}}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 3px solid {_ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {_SURFACE};
    border: 2px solid {_ACCENT};
    border-radius: 10px;
    selection-background-color: {_ACCENT};
    selection-color: {_TEXT};
    outline: none;
}}

/* --- Text + list panes -------------------------------------------------- */
QPlainTextEdit, QTextEdit, QListWidget {{
    background-color: {_SURFACE};
    border: 2px solid {_ACCENT};
    border-radius: 15px;
    padding: 6px;
    font-size: 13pt;
}}
QListWidget::item {{
    padding: 4px 6px;
    border-radius: 8px;
}}
QListWidget::item:selected {{
    background-color: {_ACCENT};
    color: {_TEXT};
}}
QListWidget::item:hover {{
    background-color: {_BTN_HOVER};
}}

/* --- Toolbar / menu / dock --------------------------------------------- */
QToolBar {{
    background-color: {_BG};
    border: none;
    spacing: 6px;
    padding: 4px;
}}
QToolBar QToolButton {{
    color: {_TEXT};
    background-color: {_BTN};
    border: 2px solid {_ACCENT};
    border-radius: 15px;
    padding: 6px 14px;
    font-size: 13pt;
}}
QToolBar QToolButton:hover {{
    background-color: {_BTN_HOVER};
    border: 2px solid {_TEXT};
}}
QToolBar QToolButton:pressed {{
    background-color: {_ACCENT};
    color: {_BG};
}}

QMenuBar {{
    background-color: {_BG};
    color: {_TEXT};
}}
QMenuBar::item:selected {{
    background-color: {_ACCENT};
    color: {_BG};
    border-radius: 8px;
}}
QMenu {{
    background-color: {_SURFACE};
    border: 2px solid {_ACCENT};
    border-radius: 10px;
}}
QMenu::item {{
    padding: 6px 22px;
}}
QMenu::item:selected {{
    background-color: {_ACCENT};
    color: {_BG};
}}

QDockWidget {{
    color: {_ACCENT};
    titlebar-close-icon: none;
}}
QDockWidget::title {{
    background-color: {_SURFACE};
    border: 2px solid {_ACCENT};
    border-radius: 10px;
    padding: 5px;
}}

/* --- Scrollbars --------------------------------------------------------- */
QScrollBar:vertical, QScrollBar:horizontal {{
    background: {_BG};
    border-radius: 7px;
    width: 12px;
    height: 12px;
}}
QScrollBar::handle {{
    background: {_BTN};
    border: 1px solid {_ACCENT};
    border-radius: 6px;
    min-height: 24px;
    min-width: 24px;
}}
QScrollBar::handle:hover {{
    background: {_ACCENT};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0px;
    width: 0px;
}}
"""


def _pick_family(families):
    """Prefer the explicit Light face when the font exposes several families."""
    for fam in families:
        if "Light" in fam:
            return fam
    return families[0] if families else None


def apply_theme(app) -> None:
    """Load the bundled font and apply the Modern Dark stylesheet to the app."""
    font_id = QFontDatabase.addApplicationFont(str(FONT_PATH))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id != -1 else []
    family = _pick_family(families)
    if family:
        font = QFont(family)
        font.setPointSize(11)
        app.setFont(font)
    app.setStyleSheet(STYLESHEET)
