from dataclasses import dataclass


@dataclass
class ThemeColors:
    # Background
    bg_primary: str
    bg_secondary: str
    bg_sidebar: str
    bg_card: str
    bg_input: str
    bg_hover: str
    bg_selected: str
    bg_badge: str
    bg_overlay: str

    # Text
    text_primary: str
    text_secondary: str
    text_muted: str
    text_on_accent: str

    # Border
    border: str
    border_focus: str
    border_light: str

    # Accent
    accent: str
    accent_hover: str
    accent_pressed: str
    accent_light: str

    # Semantic
    danger: str
    success: str
    warning: str
    info: str

    # Shadow
    shadow: str
    shadow_lg: str


LIGHT = ThemeColors(
    bg_primary="#EDEEF2",
    bg_secondary="#E4E5EB",
    bg_sidebar="#D9DBE3",
    bg_card="#F2F3F6",
    bg_input="#F0F1F5",
    bg_hover="#DDDEE6",
    bg_selected="#D0D4EE",
    bg_badge="#DDDEE6",
    bg_overlay="rgba(0,0,0,0.3)",

    text_primary="#1A1D2E",
    text_secondary="#3E4259",
    text_muted="#71758A",
    text_on_accent="#FFFFFF",

    border="#C5C8D4",
    border_focus="#4361EE",
    border_light="#D5D7E0",

    accent="#4361EE",
    accent_hover="#3651D9",
    accent_pressed="#2A42C4",
    accent_light="#DFE4FF",

    danger="#E5383B",
    success="#2D9F46",
    warning="#F4A100",
    info="#0CA5C2",

    shadow="0 1px 3px rgba(0,0,0,0.10)",
    shadow_lg="0 8px 30px rgba(0,0,0,0.14)",
)

DARK = ThemeColors(
    bg_primary="#13141F",
    bg_secondary="#0F1019",
    bg_sidebar="#0C0D15",
    bg_card="#1A1B2A",
    bg_input="#13141F",
    bg_hover="#24253A",
    bg_selected="#2C2D48",
    bg_badge="#24253A",
    bg_overlay="rgba(0,0,0,0.55)",

    text_primary="#E6E8F4",
    text_secondary="#9DA1BB",
    text_muted="#636780",
    text_on_accent="#FFFFFF",

    border="#252638",
    border_focus="#7B8DFF",
    border_light="#1E1F30",

    accent="#7B8DFF",
    accent_hover="#6A7CF0",
    accent_pressed="#596BE0",
    accent_light="#1F2038",

    danger="#FF6B7A",
    success="#5EC96A",
    warning="#FFB347",
    info="#4DB8D5",

    shadow="0 1px 3px rgba(0,0,0,0.35)",
    shadow_lg="0 8px 30px rgba(0,0,0,0.55)",
)


_current: ThemeColors = LIGHT


def current_theme() -> ThemeColors:
    return _current


def set_theme(theme: ThemeColors):
    global _current
    _current = theme


def is_dark() -> bool:
    return _current is DARK


def build_stylesheet(t: ThemeColors) -> str:
    return f"""
QMainWindow, QWidget {{
    background-color: {t.bg_primary};
    color: {t.text_primary};
    font-family: "Inter", "Segoe UI", "Noto Sans", "Roboto", system-ui, sans-serif;
    font-size: 13px;
}}
QMenuBar {{
    background-color: {t.bg_sidebar};
    color: {t.text_primary};
    border-bottom: 1px solid {t.border};
    padding: 2px 0;
}}
QMenuBar::item {{
    padding: 4px 10px;
    border-radius: 3px;
}}
QMenuBar::item:selected {{ background-color: {t.bg_hover}; }}
QMenu {{
    background-color: {t.bg_card};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 3px;
}}
QMenu::item:selected {{ background-color: {t.bg_hover}; }}
QMenu::separator {{
    height: 1px;
    background: {t.border_light};
    margin: 4px 8px;
}}
QListWidget, QTreeWidget, QTableWidget {{
    background-color: {t.bg_secondary};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 2px;
    outline: none;
}}
QListWidget::item, QTreeWidget::item {{
    padding: 6px 8px;
    border-radius: 4px;
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {t.bg_selected};
    color: {t.text_primary};
}}
QListWidget::item:hover, QTreeWidget::item:hover {{
    background-color: {t.bg_hover};
}}
QPushButton {{
    background-color: {t.accent};
    color: {t.text_on_accent};
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    min-height: 22px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover {{ background-color: {t.accent_hover}; }}
QPushButton:pressed {{ background-color: {t.accent_pressed}; }}
QPushButton:focus {{
    outline: none;
    border: 2px solid {t.border_focus};
}}
QPushButton[flat="true"], QPushButton#flatBtn {{
    background-color: transparent;
    color: {t.text_secondary};
    font-weight: normal;
    border: none;
}}
QPushButton[flat="true"]:hover, QPushButton#flatBtn:hover {{
    background-color: {t.bg_hover};
    color: {t.text_primary};
}}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {t.bg_input};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 8px 12px;
    selection-background-color: {t.accent};
    selection-color: {t.text_on_accent};
    font-size: 13px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {t.border_focus};
}}
QLineEdit#globalSearch {{
    background-color: {t.bg_secondary};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
}}
QLineEdit#globalSearch:focus {{
    border-color: {t.border_focus};
    background-color: {t.bg_card};
}}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{
    background-color: {t.bg_card};
    color: {t.text_primary};
    selection-background-color: {t.bg_selected};
    border: 1px solid {t.border};
    border-radius: 6px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {t.bg_badge};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t.text_muted};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {t.bg_secondary};
    height: 14px;
    margin: 0;
    border-radius: 7px;
}}
QScrollBar::handle:horizontal {{
    background: {t.bg_badge};
    border-radius: 7px;
    min-width: 40px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {t.text_muted};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QTabWidget::pane {{
    border: 1px solid {t.border};
    border-top: none;
    border-radius: 0 0 6px 6px;
}}
QTabBar {{
    border-bottom: 2px solid {t.border_light};
}}
QTabBar::tab {{
    background-color: transparent;
    color: {t.text_muted};
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    margin-right: 4px;
}}
QTabBar::tab:selected {{
    color: {t.accent};
    border-bottom: 2px solid {t.accent};
}}
QTabBar::tab:hover:!selected {{
    color: {t.text_primary};
    border-bottom: 2px solid {t.border};
}}
QLabel#sectionTitle {{
    font-size: 20px;
    font-weight: 700;
    color: {t.text_primary};
    letter-spacing: -0.3px;
}}
QLabel#subtitle {{
    color: {t.text_muted};
    font-size: 13px;
}}
QProgressBar {{
    background-color: {t.bg_secondary};
    border: 1px solid {t.border_light};
    border-radius: 3px;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {t.accent};
    border-radius: 3px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {t.border};
    background-color: {t.bg_input};
}}
QCheckBox::indicator:checked {{
    background-color: {t.accent};
    border-color: {t.accent};
}}
QCheckBox::indicator:hover {{
    border-color: {t.border_focus};
}}
QSplitter::handle {{ background: {t.border_light}; }}
QGroupBox {{
    border: 1px solid {t.border};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}
QDialog {{
    background-color: {t.bg_card};
    color: {t.text_primary};
    border-radius: 8px;
}}
QToolTip {{
    background-color: {t.bg_card};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
}}
QMessageBox {{
    background-color: {t.bg_card};
}}
QMessageBox QLabel {{
    color: {t.text_primary};
    font-size: 13px;
}}
QMessageBox QPushButton {{
    min-width: 80px;
    padding: 6px 16px;
}}
"""


TYPE_COLORS = {
    "FEATURE": "#4C6EF5",
    "BUG": "#E03131",
    "TECH_DEBT": "#E8590C",
    "IMPROVEMENT": "#2F9E44",
    "CHORE": "#868E96",
}

TYPE_LABELS = {
    "FEATURE": "Feature",
    "BUG": "Bug",
    "TECH_DEBT": "Tech Debt",
    "IMPROVEMENT": "Melhoria",
    "CHORE": "Tarefa",
}

PRIORITY_COLORS = {
    "LOW": "#868E96",
    "MEDIUM": "#4C6EF5",
    "HIGH": "#E8590C",
    "URGENT": "#E03131",
}

PRIORITY_LABELS = {
    "LOW": "Baixa",
    "MEDIUM": "Media",
    "HIGH": "Alta",
    "URGENT": "Urgente",
}

NAV_ICONS = {
    "daily": "◰",
    "board": "◫",
    "projects": "◈",
    "labels": "◉",
    "metrics": "◧",
    "skills": "⚙",
    "guide": "?",
}
