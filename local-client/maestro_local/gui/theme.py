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
    bg_primary="#FFFFFF",
    bg_secondary="#F8F9FC",
    bg_sidebar="#F0F2F8",
    bg_card="#FFFFFF",
    bg_input="#FFFFFF",
    bg_hover="#EBEDF5",
    bg_selected="#E3E8FF",
    bg_badge="#EBEDF5",
    bg_overlay="rgba(0,0,0,0.3)",

    text_primary="#1A1D2E",
    text_secondary="#4A4F65",
    text_muted="#8B90A0",
    text_on_accent="#FFFFFF",

    border="#DFE1EA",
    border_focus="#4C6EF5",
    border_light="#ECEEF5",

    accent="#4C6EF5",
    accent_hover="#3D5BD6",
    accent_pressed="#2F4BC7",
    accent_light="#EEF1FF",

    danger="#DC3545",
    success="#28A745",
    warning="#F59F00",
    info="#17A2B8",

    shadow="0 1px 3px rgba(0,0,0,0.08)",
    shadow_lg="0 8px 30px rgba(0,0,0,0.12)",
)

DARK = ThemeColors(
    bg_primary="#1A1B2E",
    bg_secondary="#151625",
    bg_sidebar="#111220",
    bg_card="#1E1F34",
    bg_input="#151625",
    bg_hover="#2A2B42",
    bg_selected="#2E2F4A",
    bg_badge="#2A2B42",
    bg_overlay="rgba(0,0,0,0.5)",

    text_primary="#E2E4F0",
    text_secondary="#A0A3B8",
    text_muted="#6B6E82",
    text_on_accent="#FFFFFF",

    border="#2A2B42",
    border_focus="#7C8CFF",
    border_light="#232438",

    accent="#7C8CFF",
    accent_hover="#6B7BF0",
    accent_pressed="#5A6AE0",
    accent_light="#252640",

    danger="#FF6B7A",
    success="#6BCB77",
    warning="#FFB347",
    info="#5BC0DE",

    shadow="0 1px 3px rgba(0,0,0,0.3)",
    shadow_lg="0 8px 30px rgba(0,0,0,0.5)",
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
    font-family: "Segoe UI", "Noto Sans", "Roboto", sans-serif;
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
    border-radius: 6px;
    padding: 7px 16px;
    min-height: 20px;
    font-weight: 600;
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
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {t.accent};
    selection-color: {t.text_on_accent};
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
    background: transparent;
    height: 6px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {t.bg_badge};
    border-radius: 3px;
    min-width: 30px;
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
    font-size: 18px;
    font-weight: 600;
    color: {t.text_primary};
}}
QLabel#subtitle {{
    color: {t.text_muted};
    font-size: 12px;
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
    "board": "░",
    "projects": "❐",
    "labels": "❖",
    "metrics": "▓",
    "skills": "⚙",
}
