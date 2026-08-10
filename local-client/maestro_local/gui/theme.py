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

    # Tipografia — o tema hacker troca por monoespaçada.
    font_family: str = ('"Inter", "Segoe UI", "Noto Sans", "Roboto", '
                        'system-ui, sans-serif')


# Paleta: accent teal + cinzas NEUTROS.
#
# Os cinzas antigos eram fortemente azulados (ex.: borda #B9BFD2 tinha 25 pontos
# a mais de azul que de vermelho), o que dava o ar datado — design systems
# modernos usam cinzas quase neutros. O accent teal também dá identidade própria,
# fugindo do azul/roxo que quase todo app usa.
LIGHT = ThemeColors(
    bg_primary="#FAFAFA",
    bg_secondary="#F5F5F5",
    bg_sidebar="#FFFFFF",
    bg_card="#FFFFFF",
    bg_input="#FFFFFF",
    bg_hover="#F5F5F5",
    bg_selected="#CCFBF1",
    bg_badge="#F5F5F5",
    bg_overlay="rgba(10,10,10,0.45)",

    text_primary="#171717",
    text_secondary="#404040",
    text_muted="#737373",
    text_on_accent="#FFFFFF",

    border="#E5E5E5",
    border_focus="#0D9488",
    border_light="#F5F5F5",

    accent="#0D9488",
    accent_hover="#0F766E",
    accent_pressed="#115E59",
    accent_light="#CCFBF1",

    danger="#DC2626",
    # Verde deslocado para longe do teal: como o accent já é verde-azulado, um
    # success próximo confundiria (ex.: etapa atual x concluída no FlowIndicator).
    success="#15803D",
    warning="#D97706",
    info="#0284C7",

    shadow="0 1px 2px rgba(10,10,10,0.06), 0 1px 3px rgba(10,10,10,0.04)",
    shadow_lg="0 4px 16px rgba(10,10,10,0.10)",
)

DARK = ThemeColors(
    bg_primary="#0A0A0A",
    bg_secondary="#171717",
    bg_sidebar="#0A0A0A",
    bg_card="#171717",
    bg_input="#171717",
    bg_hover="#262626",
    bg_selected="#042F2E",
    bg_badge="#262626",
    bg_overlay="rgba(0,0,0,0.6)",

    text_primary="#FAFAFA",
    text_secondary="#A3A3A3",
    text_muted="#737373",
    text_on_accent="#FFFFFF",

    border="#262626",
    border_focus="#2DD4BF",
    border_light="#1C1C1C",

    accent="#2DD4BF",
    accent_hover="#14B8A6",
    accent_pressed="#0D9488",
    accent_light="#042F2E",

    danger="#F87171",
    # Ver nota no LIGHT: verde bem separado do teal do accent.
    success="#4ADE80",
    warning="#FBBF24",
    info="#38BDF8",

    shadow="0 1px 3px rgba(0,0,0,0.4)",
    shadow_lg="0 8px 28px rgba(0,0,0,0.55)",
)


# Tema "hacker": preto com verde de fósforo e tipografia monoespaçada.
# O accent É verde, então `success` NÃO pode ser verde também — usa lima, que
# se distingue do verde-terminal. (Mesmo cuidado tomado no tema teal.)
HACKER = ThemeColors(
    bg_primary="#060A07",
    bg_secondary="#0C130E",
    bg_sidebar="#040706",
    bg_card="#0B110C",
    bg_input="#080D09",
    bg_hover="#15241A",
    bg_selected="#0B2E18",
    bg_badge="#15241A",
    bg_overlay="rgba(0,0,0,0.72)",

    text_primary="#CFF7D8",
    text_secondary="#7FCF95",
    text_muted="#4C8560",
    text_on_accent="#04140A",

    border="#1B3322",
    border_focus="#00E97A",
    border_light="#122419",

    accent="#00E97A",
    accent_hover="#00C765",
    accent_pressed="#00A554",
    accent_light="#0B2E18",

    danger="#FF6B6B",
    success="#A3E635",     # lima: separa do verde do accent
    warning="#FBBF24",
    info="#22D3EE",

    shadow="0 1px 3px rgba(0,0,0,0.6)",
    shadow_lg="0 8px 28px rgba(0,0,0,0.75)",
    font_family='"JetBrains Mono", "Fira Code", "Hack", "DejaVu Sans Mono", monospace',
)

# Ordem do rodízio do botão da barra lateral.
TEMAS = {"light": LIGHT, "dark": DARK, "hacker": HACKER}
NOMES_TEMAS = ("light", "dark", "hacker")
ROTULOS_TEMAS = {"light": "Claro", "dark": "Escuro", "hacker": "Hacker"}


def nome_do_tema(t: ThemeColors) -> str:
    for nome, tema in TEMAS.items():
        if tema is t:
            return nome
    return "light"


def proximo_tema(nome: str) -> str:
    i = NOMES_TEMAS.index(nome) if nome in NOMES_TEMAS else 0
    return NOMES_TEMAS[(i + 1) % len(NOMES_TEMAS)]


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
    font-family: {t.font_family};
    font-size: 13px;
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
QListWidget#navList {{
    background-color: transparent;
    border: none;
    padding: 2px;
    outline: none;
}}
QListWidget#navList::item {{
    /* Densidade: com os grupos, 13 linhas precisam caber sem rolagem. */
    padding: 6px 12px;
    margin: 2px 6px;
    border-radius: 8px;
    border: none;
    /* Fundo próprio para separar cada item do painel — sem borda, para não
       voltar ao aspecto de "caixinha" que envelhecia o menu. */
    background-color: {t.bg_secondary};
    color: {t.text_secondary};
    font-size: 13px;
    font-weight: 500;
}}
QListWidget#navList::item:hover {{
    background-color: {t.bg_hover};
    color: {t.text_primary};
}}
QListWidget#navList::item:selected,
QListWidget#navList::item:selected:!active {{
    background-color: {t.accent_light};
    color: {t.accent};
    font-weight: 600;
}}
/* Cabeçalho de grupo: item sem flags (não clicável), por isso :disabled. */
QListWidget#navList::item:disabled {{
    color: {t.text_muted};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    background: transparent;
    padding: 10px 12px 2px;
    margin: 0 6px;
}}
QLabel#navSection {{
    color: {t.text_muted};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    background: transparent;
    border: none;
    padding: 6px 0 2px;
}}
QPushButton {{
    background-color: {t.accent};
    color: {t.text_on_accent};
    border: none;
    border-radius: 10px;
    padding: 8px 18px;
    min-height: 20px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover {{ background-color: {t.accent_hover}; }}
QPushButton:pressed {{ background-color: {t.accent_pressed}; }}
QPushButton:disabled {{
    /* Cinza NEUTRO: bg_selected é tingido do accent e fazia o botão
       desabilitado parecer selecionado/ativo, em vez de indisponível. */
    background-color: {t.bg_badge};
    color: {t.text_muted};
    border-color: {t.border_light};
}}
QPushButton:focus {{
    outline: none;
    border: 2px solid {t.border_focus};
    padding: 6px 16px;
}}
QPushButton[flat="true"], QPushButton#flatBtn {{
    background-color: {t.bg_card};
    color: {t.text_secondary};
    font-weight: 600;
    border: 1px solid {t.border_light};
    border-radius: 10px;
    padding: 8px 16px;
}}
QPushButton[flat="true"]:hover, QPushButton#flatBtn:hover {{
    background-color: {t.bg_hover};
    color: {t.text_primary};
    border-color: {t.accent};
}}
QPushButton[flat="true"]:pressed, QPushButton#flatBtn:pressed {{
    background-color: {t.bg_selected};
}}
QToolButton {{
    background-color: {t.bg_card};
    color: {t.text_secondary};
    border: 1px solid {t.border_light};
    border-radius: 10px;
    padding: 6px 12px;
    font-weight: 600;
}}
QToolButton:hover {{
    background-color: {t.bg_hover};
    color: {t.text_primary};
    border-color: {t.accent};
}}
QToolButton:pressed, QToolButton:checked {{
    background-color: {t.bg_selected};
}}
QToolButton::menu-indicator {{ image: none; width: 0; }}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {t.bg_input};
    color: {t.text_primary};
    border: 1px solid {t.border_light};
    border-radius: 10px;
    padding: 8px 11px;
    selection-background-color: {t.accent};
    selection-color: {t.text_on_accent};
    font-size: 13px;
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover,
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {t.border_focus};
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
    width: 11px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {t.border};
    border-radius: 5px;
    min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t.accent};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 11px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {t.border};
    border-radius: 5px;
    min-width: 40px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {t.accent};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
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
    font-size: 18px;
    font-weight: 800;
    color: {t.text_primary};
    letter-spacing: -0.3px;
    margin-bottom: 2px;
    border: none;
    background: transparent;
}}
QLabel#subtitle {{
    color: {t.text_muted};
    font-size: 12px;
    border: none;
    background: transparent;
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
QCheckBox {{ spacing: 7px; }}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
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
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
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
    border-radius: 12px;
    padding: 8px;
}}
/* Qt: uma vez que um QFrame ancestral tem `border`/`background` via seletor de
   classe, ele entra no modo "estilizado" e QLabels descendentes sem regra
   própria herdam um fundo calculado da paleta em vez de ficarem transparentes
   — aparece como uma faixa cinza atrás do texto. Cobre qualquer QLabel dentro
   de um card, mesmo sem objectName/class (ex.: rótulos simples como
   "Transcrição:"), sem precisar estilizar cada label individualmente. */
QFrame[class="card"] QLabel {{
    background: transparent;
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


# Cores categóricas (badges e barras de gráfico, sempre com texto branco por
# cima). Atualizadas junto com a paleta: as antigas eram saturadas e escuras
# demais, destoando dos cinzas neutros. Todas mantêm contraste com branco.
TYPE_COLORS = {
    "FEATURE": "#2563EB",
    "BUG": "#DC2626",
    "TECH_DEBT": "#EA580C",
    "IMPROVEMENT": "#16A34A",
    "CHORE": "#71717A",
}

TYPE_LABELS = {
    "FEATURE": "Feature",
    "BUG": "Bug",
    "TECH_DEBT": "Tech Debt",
    "IMPROVEMENT": "Melhoria",
    "CHORE": "Tarefa",
}

PRIORITY_COLORS = {
    "LOW": "#71717A",
    "MEDIUM": "#2563EB",
    "HIGH": "#EA580C",
    "URGENT": "#DC2626",
}

PRIORITY_LABELS = {
    "LOW": "Baixa",
    "MEDIUM": "Media",
    "HIGH": "Alta",
    "URGENT": "Urgente",
}

# Emojis por tela. A navegação lateral NÃO usa mais isto — passou a usar
# ícones SVG monocromáticos (gui/icons.py), que se colorem com o tema.
# Mantido para telas que ainda exibem o emoji junto do título.
NAV_ICONS = {
    "dashboard": "📊",
    "daily": "📅",
    "todos": "✅",
    "study": "📚",
    "board": "🗂️",
    "projects": "📁",
    "labels": "🏷️",
    "metrics": "📈",
    "skills": "🧩",
    "chat": "💬",
    "transcricoes": "🎙️",
    "vault": "🔒",
    "library": "📇",
    "apitester": "🛰️",
    "kb": "🧠",
    "ferramentas": "🧰",
    "english": "🗣️",
    "translate": "🌐",
    "guide": "❓",
    "settings": "⚙️",
}
