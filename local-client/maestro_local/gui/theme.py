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
    bg_primary="#F5F6FA",
    bg_secondary="#EAECF2",
    bg_sidebar="#EEF0F6",
    bg_card="#FFFFFF",
    bg_input="#FFFFFF",
    bg_hover="#F0F3FF",
    bg_selected="#E0E5FF",
    bg_badge="#E6E8EF",
    bg_overlay="rgba(15,15,35,0.40)",

    text_primary="#0E1120",
    text_secondary="#2D3148",
    text_muted="#5F6478",
    text_on_accent="#FFFFFF",

    border="#CDD1DB",
    border_focus="#4C5FD0",
    border_light="#E3E5EC",

    accent="#4C5FD0",
    accent_hover="#3D4EB8",
    accent_pressed="#3140A0",
    accent_light="#E8EBFF",

    danger="#D1242F",
    success="#1E8A4A",
    warning="#C47D00",
    info="#0779B3",

    shadow="0 1px 3px rgba(0,0,0,0.08), 0 0 0 0.5px rgba(0,0,0,0.04)",
    shadow_lg="0 4px 16px rgba(0,0,0,0.10), 0 0 0 1px rgba(0,0,0,0.03)",
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
    font-size: 12px;
}}
QMenuBar {{
    background-color: {t.bg_sidebar};
    color: {t.text_primary};
    border-bottom: 1px solid {t.border_light};
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
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{ background-color: {t.bg_hover}; }}
QMenu::separator {{
    height: 1px;
    background: {t.border_light};
    margin: 4px 8px;
}}
QListWidget, QTreeWidget, QTableWidget {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 4px;
    outline: none;
}}
QListWidget::item, QTreeWidget::item {{
    padding: 5px 8px;
    border-radius: 5px;
    margin: 1px 0;
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
    padding: 5px 14px;
    min-height: 18px;
    font-weight: 600;
    font-size: 12px;
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
    padding: 5px 10px;
    selection-background-color: {t.accent};
    selection-color: {t.text_on_accent};
    font-size: 12px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {t.border_focus};
    background-color: {t.bg_card};
}}
QLineEdit#globalSearch {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
}}
QLineEdit#globalSearch:focus {{
    border-color: {t.border_focus};

}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {t.bg_card};
    color: {t.text_primary};
    selection-background-color: {t.bg_selected};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 4px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {t.border};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t.text_muted};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {t.border};
    border-radius: 4px;
    min-width: 40px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {t.text_muted};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QTabWidget::pane {{
    border: 1px solid {t.border};
    border-top: none;
    border-radius: 0 0 8px 8px;
}}
QTabBar {{
    border-bottom: 2px solid {t.border_light};
}}
QTabBar::tab {{
    background-color: transparent;
    color: {t.text_muted};
    padding: 10px 18px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    margin-right: 4px;
}}
QTabBar::tab:selected {{
    color: {t.accent};
    border-bottom: 2px solid {t.accent};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    color: {t.text_primary};
    border-bottom: 2px solid {t.border};
}}
QLabel#sectionTitle {{
    font-size: 16px;
    font-weight: 700;
    color: {t.text_primary};
    letter-spacing: -0.2px;
    margin-bottom: 2px;
}}
QLabel#subtitle {{
    color: {t.text_muted};
    font-size: 11px;
}}
QProgressBar {{
    background-color: {t.bg_badge};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {t.accent};
    border-radius: 4px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 2px solid {t.border};
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
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 18px;
    font-weight: 600;
    font-size: 13px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}}
QDialog {{
    background-color: {t.bg_card};
    color: {t.text_primary};
    border-radius: 10px;

}}
QToolTip {{
    background-color: {t.bg_card};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
}}
QMessageBox {{
    background-color: {t.bg_card};
}}
QMessageBox QLabel {{
    color: {t.text_primary};
    font-size: 13px;
    padding: 8px 0;
}}
QMessageBox QPushButton {{
    min-width: 80px;
    padding: 7px 18px;
}}
QFrame[class="card"] {{
    background: {t.bg_card};
    border: 1px solid {t.border_light};
    border-radius: 8px;
    padding: 6px;
}}
QLabel[class="cardTitle"] {{
    font-weight: 700;
    font-size: 13px;
    color: {t.text_primary};
    border: none;
    background: transparent;
}}
QLabel[class="hint"] {{
    color: {t.text_muted};
    font-size: 11px;
    border: none;
    background: transparent;
}}
QLabel[class="sectionLabel"] {{
    color: {t.text_secondary};
    font-weight: 600;
    font-size: 11px;
    border: none;
    background: transparent;
}}
QPushButton[class="secondary"] {{
    background: {t.bg_badge};
    color: {t.text_secondary};
    border: 1px solid {t.border};
    border-radius: 5px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}}
QPushButton[class="secondary"]:hover {{
    background: {t.bg_hover};
}}
QTextEdit[class="mono"] {{
    background: {t.bg_input};
    border: 1px solid {t.border_light};
    border-radius: 6px;
    padding: 8px;
    font-family: monospace;
    font-size: 12px;
    color: {t.text_primary};
}}
QTextBrowser[class="preview"] {{
    background: {t.bg_input};
    border: 1px solid {t.border_light};
    border-radius: 6px;
    padding: 8px;
    font-size: 12px;
    color: {t.text_primary};
}}
QDateEdit {{
    background-color: {t.bg_input};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 4px 8px;
}}
QLabel#summaryValue {{
    font-size: 22px;
    font-weight: 800;
    color: {t.text_primary};
    border: none;
    background: transparent;
}}
QPushButton[class="quickMove"] {{
    background: {t.bg_badge};
    color: {t.text_muted};
    border: 1px solid {t.border_light};
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 600;
    min-height: 18px;
}}
QPushButton[class="quickMove"]:hover {{
    background: {t.accent};
    color: {t.text_on_accent};
    border-color: {t.accent};
}}
"""


TYPE_COLORS = {
    "FEATURE": "#4050C8",
    "BUG": "#CC222B",
    "TECH_DEBT": "#D1550B",
    "IMPROVEMENT": "#1E7E3F",
    "CHORE": "#5E6273",
}

TYPE_LABELS = {
    "FEATURE": "Feature",
    "BUG": "Bug",
    "TECH_DEBT": "Tech Debt",
    "IMPROVEMENT": "Melhoria",
    "CHORE": "Tarefa",
}

PRIORITY_COLORS = {
    "LOW": "#5E6273",
    "MEDIUM": "#4050C8",
    "HIGH": "#D1550B",
    "URGENT": "#CC222B",
}

PRIORITY_LABELS = {
    "LOW": "Baixa",
    "MEDIUM": "Media",
    "HIGH": "Alta",
    "URGENT": "Urgente",
}

NAV_ICONS = {
    "dashboard": "◱",
    "daily": "◰",
    "todos": "✓",
    "study": "📚",
    "board": "◫",
    "projects": "◈",
    "labels": "◉",
    "metrics": "◧",
    "skills": "⚙",
    "chat": "✦",
    "cronista": "🎙",
    "guide": "?",
    "settings": "⚡",
}
