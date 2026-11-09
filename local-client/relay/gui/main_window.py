import logging

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from relay.gui.theme import (
    PRIORITY_LABELS,  # noqa: F401 - exported for other modules
    build_stylesheet,
    carregar_fontes,
    current_theme,
    is_dark,
    set_theme,
)
from relay.gui.efeitos import aplicar_sombras, sombra_topo
from relay.config import get_active_workspace_id, get_workspace_db_path
from relay.i18n import t
from relay import features
from relay.db.models import Project, Recording, Todo, get_session, switch_db
from relay.gui.views.board_view import BoardView
from relay.gui.views.daily_view import DailyView
from relay.gui.views.dashboard_view import DashboardView
from relay.gui.views.chat_view import ChatView
from relay.gui.views.transcricoes_view import TranscricoesView
from relay.gui.views.tools_hub_view import ToolsHubView
from relay.gui.views.settings_view import SettingsView
from relay.gui.views.projects_view import ProjectsView
from relay.gui.views.study_view import StudyView
# Telas raramente abertas (vault/library/apitester/kb/memory/english/translate/
# skills/guide): import E CONSTRUÇÃO tardios (ver _ensure_view). Nenhuma delas é
# referenciada fora do dicionário de navegação, então adiar é seguro — a tela só
# custa memória/import quando o usuário de fato a abre.
from relay.gui.workspace_selector import WorkspaceSelectorButton
from relay.todos import todos_abertos

logger = logging.getLogger("relay.gui.main_window")


class ResponsiveStack(QStackedWidget):
    """QStackedWidget cujo mínimo acompanha a página atual.

    O padrão usa o MÁXIMO dos mínimos de todas as páginas, então uma tela
    larga (ex.: Estudos) travava a largura mínima da janela inteira e o
    splitter nunca liberava espaço para aumentar o menu.
    """

    def minimumSizeHint(self):  # noqa: N802
        w = self.currentWidget()
        if w is not None:
            return w.minimumSizeHint()
        return super().minimumSizeHint()


def suggest_project_key(name: str) -> str:
    """Sugere KEY a partir do nome (igual ao formulário de Projetos)."""
    import re
    clean = re.sub(r"[^a-zA-Z0-9]", "", name or "").upper()
    return clean[:4] if len(clean) >= 4 else clean[:3]


def create_project_with_defaults(name: str, key: str | None = None) -> int | None:
    """Cria projeto com as colunas padrão. Devolve o id ou None se inválido.

    Chave duplicada ganha sufixo (-2, -3...) em vez de falhar.
    """
    from relay.db.models import DEFAULT_COLUMNS, BoardColumn, Project
    name = (name or "").strip()
    key = ((key or "").strip() or suggest_project_key(name)).upper()
    if not name or not key:
        return None
    s = get_session()
    try:
        base, n = key, 2
        while s.query(Project).filter(Project.key == key).first() is not None:
            key = f"{base}-{n}"
            n += 1
        p = Project(name=name, key=key)
        s.add(p)
        s.flush()
        for col_def in DEFAULT_COLUMNS:
            s.add(BoardColumn(
                project_id=p.id,
                name=col_def["name"],
                order=col_def["order"],
                is_done=col_def.get("is_done", False),
            ))
        s.commit()
        return p.id
    except Exception:
        s.rollback()
        return None
    finally:
        s.close()


class ToastWidget(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(36)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text, duration=2000):
        self.setText(f"  {text}  ")
        self.adjustSize()
        p = self.parent()
        if p:
            self.move(p.width() - self.width() - 20, p.height() - 60)
        self.show()
        self.raise_()
        self._timer.start(duration)


class TodoReminder(QFrame):
    """Banner de lembrete de TODOs pendentes (só na interface, canto inferior)."""

    def __init__(self, parent, on_view, on_snooze, on_dismiss):
        super().__init__(parent)
        self.hide()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 10, 10)
        lay.setSpacing(10)
        self._msg = QLabel("")
        lay.addWidget(self._msg)
        self._view = QPushButton(t("Ver"))
        self._view.setCursor(Qt.PointingHandCursor)
        self._view.clicked.connect(on_view)
        lay.addWidget(self._view)
        self._snooze = QPushButton(t("Adiar 10min"))
        self._snooze.setProperty("flat", True)
        self._snooze.setCursor(Qt.PointingHandCursor)
        self._snooze.clicked.connect(on_snooze)
        lay.addWidget(self._snooze)
        self._close = QPushButton("✕")
        self._close.setProperty("flat", True)
        self._close.setFixedSize(24, 24)
        self._close.setCursor(Qt.PointingHandCursor)
        self._close.clicked.connect(on_dismiss)
        lay.addWidget(self._close)

    def show_count(self, n):
        th = current_theme()
        self.setStyleSheet(
            f"TodoReminder {{ background: {th.bg_card}; border: 1px solid {th.warning}; "
            f"border-radius: 10px; }}"
        )
        self._msg.setText("⏰ " + t("{n} tarefa(s) pendente(s)").format(n=n))
        self._msg.setStyleSheet(f"color: {th.text_primary}; font-weight: 600; border: none;")
        self.adjustSize()
        p = self.parent()
        if p:
            self.move(p.width() - self.width() - 20, p.height() - self.height() - 20)
        self.show()
        self.raise_()


class MainWindow(QMainWindow):
    # Atalhos vindos de fora (ex.: links relay://reunioes).
    VIEW_ALIASES = {
        "reunioes": "transcricoes",
        "transcricoes": "transcricoes",
        "vault": "vault",
        "senhas": "vault",
        "config": "settings",
        "settings": "settings",
        "board": "board",
    }

    def __init__(self, api_port: int = 9777, initial_view: str | None = None):
        super().__init__()
        carregar_fontes()   # Inter embutida (precisa vir antes de criar widgets)
        self.api_port = api_port
        self._initial_view = (initial_view or "").strip().lower()
        self.setWindowTitle("Relay")
        self.resize(1120, 720)
        self.setMinimumSize(720, 480)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Painel lateral ---
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(160)
        self.sidebar.setMaximumWidth(420)
        sb = QVBoxLayout(self.sidebar)
        sb.setContentsMargins(10, 14, 10, 12)
        sb.setSpacing(8)

        marca = QHBoxLayout()
        marca.setSpacing(10)
        self.logo_badge = QLabel("A")
        self.logo_badge.setFixedSize(30, 30)
        self.logo_badge.setAlignment(Qt.AlignCenter)
        marca.addWidget(self.logo_badge)
        marca_texto = QVBoxLayout()
        marca_texto.setSpacing(0)
        self.logo_text = QLabel("Agentic Dev")
        self.logo_text.setObjectName("brandName")
        self.logo_subtitle = QLabel("RELAY")
        self.logo_subtitle.setObjectName("brandSub")
        marca_texto.addWidget(self.logo_text)
        marca_texto.addWidget(self.logo_subtitle)
        marca.addLayout(marca_texto)
        marca.addStretch()
        sb.addLayout(marca)

        self.ws_selector = WorkspaceSelectorButton()
        self.ws_selector.workspace_changed.connect(self._on_workspace_changed)
        sb.addWidget(self.ws_selector)

        from relay.gui.no_wheel_combo import NoWheelComboBox
        self.project_selector = NoWheelComboBox()
        self.project_selector.setObjectName("sidebarCombo")
        self.project_selector.setToolTip(t("Projeto ativo"))
        self.project_selector.currentIndexChanged.connect(self._on_project_selected)
        proj_row = QHBoxLayout()
        proj_row.setContentsMargins(0, 0, 0, 0)
        proj_row.setSpacing(6)
        proj_row.addWidget(self.project_selector, 1)
        self.new_project_btn = QToolButton()
        self.new_project_btn.setObjectName("newProjectBtn")
        self.new_project_btn.setText("+")
        self.new_project_btn.setToolTip(t("Novo Projeto"))
        self.new_project_btn.setCursor(Qt.PointingHandCursor)
        self.new_project_btn.setFixedSize(30, 30)
        self.new_project_btn.clicked.connect(self._new_project)
        proj_row.addWidget(self.new_project_btn)
        proj_wrap = QWidget()
        proj_wrap.setLayout(proj_row)
        sb.addWidget(proj_wrap)

        # Navegação do app desktop: só o que é nativo (o resto vive na
        # versão web, aberta pelo botão do topo). Todo o resto continua
        # acessível reativando em Configurações → Funcionalidades.
        nav_groups = [
            (t("PRINCIPAL"), [
                (t("Reuniões"), "transcricoes"),
                (t("Assistente"), "chat"),
            ]),
            (t("FERRAMENTAS"), [
                (t("Senhas"), "vault"),
            ]),
            (t("SISTEMA"), [
                (t("Instruções"), "guide"),
                (t("Configurações"), "settings"),
            ]),
        ]
        # Só entra o que o usuário deixou ligado (ver relay/features).
        nav_groups = [(titulo, [(rot, k) for rot, k in itens
                                if features.habilitada(k)])
                      for titulo, itens in nav_groups]
        nav_groups = [(titulo, itens) for titulo, itens in nav_groups if itens]

        self._labels = {k: rot for _, itens in nav_groups for rot, k in itens}
        self._descricoes = {f.chave: t(f.descricao) for f in features.FUNCIONALIDADES}
        self._descricoes["settings"] = t("Idioma, provedores de IA e transcrições")
        self._descricoes["techlinks"] = t("Sites para acompanhar novidades de tecnologia")
        self._descricoes["goals"] = t("Objetivos com progresso e contagem regressiva")
        self._nav_keys: list[str] = []
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        for titulo, itens in nav_groups:
            header = QListWidgetItem(titulo)
            header.setFlags(Qt.NoItemFlags)   # rótulo, não é clicável
            self.nav_list.addItem(header)
            for rotulo, key in itens:
                item = QListWidgetItem(f"  {rotulo}")
                item.setData(Qt.UserRole, key)
                self.nav_list.addItem(item)
                self._nav_keys.append(key)
        self.nav_list.setIconSize(QSize(18, 18))
        self.nav_list.currentRowChanged.connect(self._on_nav)
        sb.addWidget(self.nav_list, 1)

        from PySide6.QtWidgets import QComboBox
        from relay.gui.theme import NOMES_TEMAS, ROTULOS_TEMAS
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("sidebarCombo")
        self.theme_combo.setCursor(Qt.PointingHandCursor)
        for nome in NOMES_TEMAS:
            self.theme_combo.addItem(t(ROTULOS_TEMAS[nome]), nome)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_selected)
        sb.addWidget(self.theme_combo)

        self.version_label = QLabel("v1.0.0")
        self.version_label.setObjectName("versionLabel")
        self.version_label.setAlignment(Qt.AlignCenter)
        sb.addWidget(self.version_label)

        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setHandleWidth(10)
        self._splitter.addWidget(self.sidebar)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        layout.addWidget(self._splitter)

        # --- Área de conteúdo ---
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Barra superior: título da tela + ações globais.
        self.topbar = QFrame()
        self.topbar.setObjectName("topBar")
        self.topbar.setFixedHeight(60)
        top = QHBoxLayout(self.topbar)
        top.setContentsMargins(22, 8, 18, 8)
        top.setSpacing(10)

        # Ocultar/mostrar o menu lateral (útil em tela cheia/secundária).
        self.menu_toggle_btn = QToolButton()
        self.menu_toggle_btn.setObjectName("menuToggle")
        self.menu_toggle_btn.setText("☰")
        self.menu_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.menu_toggle_btn.setToolTip(t("Ocultar menu (F9)"))
        self.menu_toggle_btn.setFixedSize(34, 34)
        self.menu_toggle_btn.clicked.connect(lambda: self._toggle_sidebar())
        top.addWidget(self.menu_toggle_btn)

        titulos = QVBoxLayout()
        titulos.setSpacing(0)
        self.page_title = QLabel(t("Dashboard"))
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel(t("Visão geral do seu trabalho"))
        self.page_subtitle.setObjectName("pageSubtitle")
        # Podem encolher: em janela estreita quem cede espaço é o texto do
        # topo, não o menu lateral nem o atalho "Abrir web".
        from PySide6.QtWidgets import QSizePolicy
        for _lbl in (self.page_title, self.page_subtitle):
            _lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            _lbl.setMinimumWidth(0)
        titulos.addWidget(self.page_title)
        titulos.addWidget(self.page_subtitle)
        top.addLayout(titulos)
        top.addStretch(1)

        # Versão web: o desktop fica com o mínimo (nativo); o resto vive na web.
        self.web_btn = QToolButton()
        self.web_btn.setObjectName("webShortcut")
        self.web_btn.setProperty("class", "primary")
        self.web_btn.setCursor(Qt.PointingHandCursor)
        self.web_btn.setToolTip(t("Abrir a versão web (board, métricas, reuniões...)"))
        self.web_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.web_btn.clicked.connect(self._open_web_version)
        self.web_btn.setMinimumHeight(34)
        top.addWidget(self.web_btn)

        # Gravação rápida (quando ligada em Funcionalidades).
        self.quick_record_btn = QToolButton()
        self.quick_record_btn.setProperty("class", "topIcon")
        self.quick_record_btn.setCursor(Qt.PointingHandCursor)
        self.quick_record_btn.setToolTip(t("Iniciar uma reunião"))
        self.quick_record_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.quick_record_btn.clicked.connect(self._transcricoes_quick_toggle)
        self.quick_record_btn.setVisible(features.habilitada("quick_record"))
        top.addWidget(self.quick_record_btn)

        # Busca global (Ctrl+K).
        self.search_btn = QToolButton()
        self.search_btn.setProperty("class", "topIcon")
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setToolTip(t("Buscar (Ctrl+K)"))
        self.search_btn.clicked.connect(self._toggle_search)
        top.addWidget(self.search_btn)

        # Notificações: sino com a contagem de TODOs pendentes.
        self.notif_btn = QToolButton()
        self.notif_btn.setProperty("class", "topIcon")
        self.notif_btn.setCursor(Qt.PointingHandCursor)
        self.notif_btn.clicked.connect(self._show_todo_menu)
        top.addWidget(self.notif_btn)
        self.notif_badge = QLabel("")
        self.notif_badge.setObjectName("badgeCount")
        self.notif_badge.hide()
        top.addWidget(self.notif_badge)

        content_layout.addWidget(self.topbar)

        # Global search bar
        search_container = QWidget()
        search_container.setObjectName("searchContainer")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(16, 10, 16, 10)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(t("Buscar tarefas... (Ctrl+K)"))
        self.search_bar.setObjectName("globalSearch")
        self.search_bar.textChanged.connect(self._on_search)
        self.search_bar.setVisible(False)
        search_layout.addWidget(self.search_bar)

        self.search_container = search_container
        search_container.setVisible(False)
        content_layout.addWidget(search_container)

        # Search results popup
        self.search_results = QListWidget(self)
        self.search_results.setWindowFlags(Qt.Popup)
        self.search_results.setObjectName("searchResults")
        self.search_results.itemClicked.connect(self._on_search_result)
        self.search_results.setVisible(False)

        # Stacked widget with views
        self.stack = ResponsiveStack()

        self.dashboard_view = DashboardView()
        self.daily_view = DailyView()
        self.study_view = StudyView()
        self.board_view = BoardView()
        self.chat_view = ChatView()
        self.transcricoes_view = TranscricoesView()
        self.transcricoes_view.workspace_change_requested.connect(self._on_workspace_changed)
        self.transcricoes_view.project_changed.connect(self._sync_project_selector)
        self.tools_hub_view = ToolsHubView(lambda key: self._open_key(key))
        self.projects_view = ProjectsView()
        self.settings_view = SettingsView()
        self.settings_view.notification_changed.connect(self._setup_notification_timer)
        self.settings_view.notification_changed.connect(self._setup_coach_timer)
        self.settings_view.ai_provider_changed.connect(self.chat_view.refresh)

        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.daily_view)
        self.stack.addWidget(self.study_view)
        self.stack.addWidget(self.board_view)
        self.stack.addWidget(self.chat_view)
        self.stack.addWidget(self.transcricoes_view)
        self.stack.addWidget(self.tools_hub_view)
        self.stack.addWidget(self.projects_view)
        self.stack.addWidget(self.settings_view)

        # Navegação por chave (o menu não mapeia mais 1:1 por posição no stack).
        # As telas abaixo são pouco acessadas (hub "Ferramentas"): entram como
        # FÁBRICA (lambda) em vez de instância — só são importadas/construídas
        # no primeiro _open_key, economizando import e memória de boot.
        self._view_by_key = {
            "dashboard": self.dashboard_view,
            "daily": self.daily_view,
            "study": self.study_view,
            "board": self.board_view,
            "chat": self.chat_view,
            "transcricoes": self.transcricoes_view,
            "ferramentas": self.tools_hub_view,
            "projects": self.projects_view,
            "settings": self.settings_view,
            "vault": self._lazy_factory("gui.views.vault_view", "VaultView"),
            "library": self._lazy_factory("gui.views.library_view", "LibraryView"),
            "apitester": self._lazy_factory("gui.views.api_tester_view", "ApiTesterView"),
            "kb": self._lazy_factory("gui.views.kb_view", "KBView"),
            "memory": self._lazy_factory("gui.views.memory_view", "MemoryView"),
            "english": self._lazy_factory("gui.views.english_view", "EnglishView"),
            "translate": self._lazy_factory("gui.views.translate_view", "TranslateView"),
            "skills": self._lazy_factory("gui.views.skills_view", "SkillsView"),
            "guide": self._lazy_factory("gui.views.guide_view", "GuideView"),
            "techlinks": self._lazy_factory("gui.views.tech_links_view", "TechLinksView"),
            "goals": self._lazy_factory("gui.views.goals_view", "GoalsView"),
        }

        content_layout.addWidget(self.stack)
        self._splitter.addWidget(content_widget)
        from relay.config import load_config
        _persistido = load_config().get("settings", {})
        _largura = int(_persistido.get("sidebar_width", 224) or 224)
        self._largura_sidebar_desejada = max(160, min(420, _largura))
        self._splitter.setSizes([self._largura_sidebar_desejada, 1200])
        # Menu lateral começa oculto se estava assim ao sair (útil em tela menor).
        self._sidebar_width = self._largura_sidebar_desejada
        if _persistido.get("sidebar_visible", True) is False:
            self.sidebar.hide()
            self.menu_toggle_btn.setToolTip(t("Mostrar menu (F9)"))
        else:
            self.menu_toggle_btn.setToolTip(t("Ocultar menu (F9)"))
        _tab = int(_persistido.get("dashboard_tab", 0) or 0)
        if hasattr(self.dashboard_view, "_tabs") and 0 <= _tab < self.dashboard_view._tabs.count():
            self.dashboard_view._tabs.setCurrentIndex(_tab)

        # Connections
        self.projects_view.project_selected.connect(self._open_board)
        self.board_view.project_opened.connect(self._open_board)
        self.board_view.back_requested.connect(self._board_back_to_projects)
        self.board_view.task_changed.connect(self._refresh_all)
        self.dashboard_view.task_clicked.connect(self._open_task_from_dashboard)
        self.dashboard_view.project_clicked.connect(self._open_board)

        # Tela inicial: deep link (--view), depois a última aberta (ou a
        # primeira do menu, que no desktop enxuto é Reuniões).
        _ultima = _persistido.get("last_screen")
        _alias = self.VIEW_ALIASES.get(self._initial_view or "")
        if _alias:
            _inicial = _alias
        else:
            _inicial = _ultima if _ultima in self._nav_keys else (self._nav_keys[0] if self._nav_keys else "settings")
        self._last_screen = _inicial
        self._open_key(_inicial)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Toast notification
        self.toast = ToastWidget(self)

        # --- Keyboard shortcuts ---
        search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        search_shortcut.activated.connect(self._toggle_search)

        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self._close_search)

        new_meeting_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_meeting_shortcut.activated.connect(self._nova_reuniao_atalho)

        new_todo_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        new_todo_shortcut.activated.connect(self._novo_todo_atalho)

        help_shortcut = QShortcut(QKeySequence("Ctrl+/"), self)
        help_shortcut.activated.connect(self._mostrar_atalhos)

        board_shortcut = QShortcut(QKeySequence("Ctrl+B"), self)
        board_shortcut.activated.connect(lambda: self._open_key("board"))

        sidebar_shortcut = QShortcut(QKeySequence("F9"), self)
        sidebar_shortcut.activated.connect(lambda: self._toggle_sidebar())

        # Alt+N abre a N-ésima TELA (os cabeçalhos de grupo não contam).
        for i, key in enumerate(self._nav_keys[:9]):
            shortcut = QShortcut(QKeySequence(f"Alt+{i + 1}"), self)
            shortcut.activated.connect(lambda k=key: self._open_key(k))

        self._notif_timer = QTimer(self)
        self._notif_timer.timeout.connect(self._send_notification)
        self._setup_notification_timer()

        self._setup_global_hotkeys()

        # Atualiza o botão de gravação do topo por EVENTO (a view avisa ao
        # iniciar/parar e a cada segundo enquanto grava) — sem poll de 1s ocioso.
        self._gravando = False
        self._gravando_seg = 0
        self.transcricoes_view.recording_state_changed.connect(
            self._on_recording_state)

        # Libera o modelo Whisper da RAM quando ocioso: ele fica residente após o
        # primeiro uso (o 'small' int8 são centenas de MB). Depois de ~4 min sem
        # gravar/transcrever, devolve essa memória ao sistema; recarrega sozinho.
        self._whisper_idle_ticks = 0
        self._whisper_idle_timer = QTimer(self)
        self._whisper_idle_timer.setInterval(120000)  # 2 min
        self._whisper_idle_timer.timeout.connect(self._maybe_release_whisper)
        self._whisper_idle_timer.start()

        # Lembrete periódico de TODOs pendentes (só na interface)
        self.todo_reminder = TodoReminder(
            self, self._goto_todos, self._snooze_todos, self._dismiss_todos)
        self._pending_todo_ids = []
        self._todo_timer = QTimer(self)
        self._todo_timer.setInterval(60000)  # a cada 1 min
        self._todo_timer.timeout.connect(self._check_todo_reminders)
        self._todo_timer.start()
        QTimer.singleShot(4000, self._check_todo_reminders)

        # Reunião em curso: segura a pausa para os olhos e avisa o sistema
        # operacional a cada 15 minutos (aviso do SO, não toast da interface).
        self._reuniao_em_curso = False
        self._meeting_notice_timer = QTimer(self)
        self._meeting_notice_timer.setInterval(15 * 60 * 1000)
        self._meeting_notice_timer.timeout.connect(self._notificar_reuniao_em_curso)

        # Pausa para os olhos: verifica de minuto em minuto (a precisão de um
        # lembrete de 20 min não precisa ser melhor que isso).
        self._eyecare_overlay = None
        self._eyecare_timer = QTimer(self)
        self._eyecare_timer.setInterval(60000)
        self._eyecare_timer.timeout.connect(self._maybe_show_eyecare)
        self._eyecare_timer.start()

        # Bandeja: adiar a pausa sem precisar trazer a janela para a frente.
        from relay.gui.icons import icone_do_app
        from relay.gui.tray import instalar as instalar_bandeja
        self.setWindowIcon(icone_do_app())
        self._tray = instalar_bandeja(self)
        self._force_quit = False

        # Coach proativo: dicas do agente ao longo do dia (opt-in em Configurações)
        from relay.gui.coach_widget import CoachTip
        self.coach_tip = CoachTip(self, lambda: self._open_key("chat"))
        self._coach_worker = None
        self._recent_tips: list[str] = []
        self._last_coach_monotonic = 0.0
        self._coach_timer = QTimer(self)
        self._coach_timer.timeout.connect(self._maybe_coach_tip)
        self._setup_coach_timer()
        # Gatilho por evento: reage a sinais fortes (tarefas paradas, WIP alto,
        # TODOs vencidos) sem esperar o ciclo periódico — com cooldown. Timer
        # próprio, folgado (5 min): não precisa de precisão e evita I/O à toa.
        self._coach_signal_timer = QTimer(self)
        self._coach_signal_timer.setInterval(300000)  # 5 min
        self._coach_signal_timer.timeout.connect(self._check_coach_signals)
        self._coach_signal_timer.start()

        # Lembrete de compactação do chat (só lembrete, compact é no opencode)
        self._chat_compact_timer = QTimer(self)
        self._chat_compact_timer.timeout.connect(self._send_chat_compact_reminder)
        self._setup_chat_compact_timer()
        self.settings_view.notification_changed.connect(self._setup_chat_compact_timer)

        self._populate_project_selector()
        self._atualizar_status()
        self._apply_theme()

    # ---- Coach proativo ----
    def _setup_coach_timer(self):
        from relay.config import get_coach_config
        cfg = get_coach_config()
        self._coach_timer.stop()
        if cfg.get("enabled"):
            self._coach_timer.setInterval(max(15, cfg.get("interval_min", 90)) * 60000)
            self._coach_timer.start()
            # Primeira dica pouco depois de abrir (não logo no boot).
            QTimer.singleShot(90000, self._maybe_coach_tip)

    def _maybe_coach_tip(self):
        import time

        from relay.config import get_active_ai_provider, get_coach_config
        if not get_coach_config().get("enabled"):
            return
        if self._coach_worker is not None:
            return
        if not get_active_ai_provider():
            return
        from relay.gui.coach_widget import CoachWorker
        # Marca o disparo (cooldown do gatilho por evento conta a partir daqui).
        self._last_coach_monotonic = time.monotonic()
        w = CoachWorker(self._recent_tips[-5:], self)
        w.done.connect(self._on_coach_tip)
        w.failed.connect(lambda *_: setattr(self, "_coach_worker", None))
        w.finished.connect(lambda: setattr(self, "_coach_worker", None))
        self._coach_worker = w
        w.start()

    def _check_coach_signals(self):
        """Dispara uma dica na hora se houver sinal forte (tarefa parada, WIP
        alto, TODO vencido), respeitando um cooldown para não ser intrusivo."""
        import time

        from relay.config import get_active_ai_provider, get_coach_config
        cfg = get_coach_config()
        if not cfg.get("enabled") or self._coach_worker is not None:
            return
        if not get_active_ai_provider():
            return
        cooldown = max(15, int(cfg.get("interval_min", 90)) // 2) * 60
        if time.monotonic() - self._last_coach_monotonic < cooldown:
            return
        from relay import coach
        s = get_session()
        try:
            strong = coach.has_strong_signal(s)
        finally:
            s.close()
        if strong:
            self._maybe_coach_tip()

    def _on_coach_tip(self, data: dict):
        self._coach_worker = None
        tip = (data or {}).get("tip", "").strip()
        if not tip:
            return
        self._recent_tips.append(tip)
        self.coach_tip.show_tip(tip, (data or {}).get("category", ""))

    # ---- Lembretes de TODOs ----
    def _check_todo_reminders(self):
        from datetime import datetime
        s = get_session()
        try:
            now = datetime.now()
            todos = s.query(Todo).filter(
                Todo.done.is_(False), Todo.due_at.isnot(None), Todo.due_at <= now
            ).all()
            ids = [td.id for td in todos if not (td.snoozed_until and td.snoozed_until > now)]
            abertos = s.query(Todo).filter(Todo.done.is_(False)).count()
        finally:
            s.close()
        self._pending_todo_ids = ids
        # O sino reflete o que está em aberto mesmo com o lembrete desligado.
        self._update_notif_badge(abertos)
        from relay import features
        if not features.habilitada("todo_reminder"):
            return
        if ids:
            self.todo_reminder.show_count(len(ids))  # reaparece a cada ciclo enquanto houver pendentes
        else:
            self.todo_reminder.hide()

    def _complete_todo(self, todo_id):
        """Conclui um TODO a partir do menu do sino e atualiza badge/telas."""
        from datetime import datetime
        s = get_session()
        try:
            td = s.get(Todo, todo_id)
            if td is not None and not td.done:
                td.done = True
                td.completed_at = datetime.utcnow()
                s.commit()
        finally:
            s.close()
        self._check_todo_reminders()
        self._refresh_all()

    def _update_notif_badge(self, n):
        """Sino do topo: contagem de TODOs pendentes (some quando zera)."""
        self.notif_badge.setText(str(n) if n else "")
        self.notif_badge.setVisible(bool(n))
        self.notif_btn.setToolTip(
            t("{n} TODO(s) pendente(s)").format(n=n) if n else t("Sem pendências"))

    def _show_todo_menu(self):
        """Menu do sino: conclui uma pendência ou abre as ações rápidas."""
        menu = QMenu(self)
        itens = todos_abertos(limite=12)
        if itens:
            for item in itens:
                acao = menu.addAction("✓  " + item["text"])
                acao.triggered.connect(
                    lambda _=False, tid=item["id"]: self._complete_todo(tid))
            menu.addSeparator()
        menu.addAction(t("Abrir TODOs"), self._goto_todos)
        if self._pending_todo_ids:
            menu.addAction(t("Adiar 10min"), self._snooze_todos)
        menu.exec(self.notif_btn.mapToGlobal(self.notif_btn.rect().bottomLeft()))

    def _goto_todos(self):
        self.todo_reminder.hide()
        self._open_key("dashboard")  # Dashboard (aba TODOs fica lá)
        w = self.stack.currentWidget()
        # tenta selecionar a aba TODOs no Dashboard
        tabs = getattr(w, "_tabs", None)
        if tabs is not None:
            for i in range(tabs.count()):
                if "TODO" in tabs.tabText(i).upper():
                    tabs.setCurrentIndex(i)
                    break

    def _snooze_todos(self):
        from datetime import datetime, timedelta
        if self._pending_todo_ids:
            s = get_session()
            try:
                until = datetime.now() + timedelta(minutes=10)
                for tid in self._pending_todo_ids:
                    td = s.query(Todo).get(tid)
                    if td:
                        td.snoozed_until = until
                s.commit()
            finally:
                s.close()
        self.todo_reminder.hide()

    def _dismiss_todos(self):
        # Esconde até o próximo ciclo (reaparece se ainda houver pendentes)
        self.todo_reminder.hide()

    def _open_web_version(self):
        """Abre a versão web no navegador. O desktop já serve a API na
        mesma porta, então a web funciona sem precisar subir nada além."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(f"http://127.0.0.1:{self.api_port}/"))

    def _transcricoes_quick_toggle(self):
        """Abre Reuniões. O botão do topo inicia a gravação, mas nunca encerra
        uma reunião em andamento — parar é ação explícita da tela de Reuniões."""
        self._open_key("transcricoes")
        if self.transcricoes_view.is_busy():
            return
        self.transcricoes_view.toggle_record_external()

    def _on_recording_state(self, gravando: bool, segundos: int = 0):
        """Espelha no botão do topo o estado da gravação rápida.

        Também controla o que depende de estar em reunião: a pausa para os
        olhos fica suspensa e o aviso de 15 em 15 minutos (no SO) liga/desliga.
        """
        self._gravando = bool(gravando)
        self._gravando_seg = int(segundos or 0)
        self._atualizar_icone_gravacao()

        self._reuniao_em_curso = bool(gravando)
        timer = getattr(self, "_meeting_notice_timer", None)
        if timer is not None:
            if gravando:
                if not timer.isActive():
                    timer.start()
            else:
                timer.stop()
        if gravando and self._eyecare_overlay is not None:
            # começou a reunião: a pausa sai da frente na hora
            self._suspender_pausa()

    def _atualizar_icone_gravacao(self):
        if not hasattr(self, "quick_record_btn"):
            return
        if getattr(self, "_gravando", False):
            m, s = divmod(int(getattr(self, "_gravando_seg", 0)), 60)
            self.quick_record_btn.setText(f"● {m:02d}:{s:02d}")
            self.quick_record_btn.setToolTip(t("Reunião em andamento — abrir Reuniões"))
        else:
            self.quick_record_btn.setText(t("Gravar"))
            self.quick_record_btn.setToolTip(t("Iniciar uma reunião"))

    def _maybe_release_whisper(self):
        """Libera o modelo Whisper após dois ciclos ociosos consecutivos (~4 min).
        Só quando não há gravação/transcrição em curso — senão o worker quebra."""
        if self.transcricoes_view.is_busy():
            self._whisper_idle_ticks = 0
            return
        self._whisper_idle_ticks += 1
        if self._whisper_idle_ticks < 2:
            return
        self._whisper_idle_ticks = 0
        from relay.transcricoes.transcriber import release_model
        release_model()

    def _setup_global_hotkeys(self):
        # Nos testes (e quando RELAY_DISABLE_HOTKEYS=1) não registra atalho
        # global: o pynput abre threads do X Record que derrubam a suíte com
        # segfault quando várias janelas são criadas na mesma sessão.
        import os
        import sys

        if os.environ.get("RELAY_DISABLE_HOTKEYS") or os.environ.get("MAESTRO_DISABLE_HOTKEYS") or "pytest" in sys.modules:
            self._hotkeys = None
            return
        try:
            from relay.transcricoes.constants import HOTKEY_TOGGLE_RECORDING
            from relay.transcricoes.hotkeys import GlobalHotkeys
            self._hotkeys = GlobalHotkeys()
            self._hotkeys.start({
                HOTKEY_TOGGLE_RECORDING: self.transcricoes_view.toggle_record_external,
            })
        except Exception:  # noqa: BLE001
            self._hotkeys = None

    def _apply_theme(self):
        theme = current_theme()
        from relay.gui.icons import clear_cache, nav_icon
        clear_cache()   # os ícones são coloridos pelo tema
        self.setStyleSheet(build_stylesheet(theme))

        # Ícones da barra superior: são pixmaps, então o QSS não os recolore.
        self.web_btn.setIcon(nav_icon("web", theme.text_on_accent, size=18))
        self.web_btn.setText(t("Abrir web"))
        self.search_btn.setIcon(nav_icon("search", theme.text_secondary, size=20))
        self.notif_btn.setIcon(nav_icon("bell", theme.text_secondary, size=20))
        self.quick_record_btn.setIcon(
            nav_icon("transcricoes", theme.text_secondary, size=18))
        self._atualizar_icone_gravacao()

        self.logo_badge.setStyleSheet(
            f"background: {theme.accent}; color: {theme.text_on_accent}; "
            f"font-size: 15px; font-weight: 800; border-radius: 8px;")
        self._refresh_nav_icons()
        sombra_topo(self.topbar, escuro=is_dark())
        aplicar_sombras(self, escuro=is_dark())
        self.dashboard_view.pomodoro.apply_theme(theme)
        from relay.gui.theme import nome_do_tema
        atual = nome_do_tema(theme)
        # Sem bloquear, reposicionar o select dispararia outra troca de tema.
        self.theme_combo.blockSignals(True)
        indice = self.theme_combo.findData(atual)
        if indice >= 0:
            self.theme_combo.setCurrentIndex(indice)
        self.theme_combo.blockSignals(False)
        self.status.setStyleSheet(
            f"background-color: {theme.bg_sidebar}; color: {theme.sidebar_muted}; "
            f"border-top: 1px solid {theme.sidebar_border}; font-size: 11px; padding: 2px 8px;"
        )
        self.search_container.setStyleSheet(
            f"background-color: {theme.bg_primary}; "
            f"border-bottom: 1px solid {theme.border_light};"
        )
        self.search_results.setStyleSheet(f"""
            QListWidget {{
                background-color: {theme.bg_card};
                border: 1px solid {theme.border};
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 4px;
                color: {theme.text_primary};
            }}
            QListWidget::item:selected {{
                background-color: {theme.bg_selected};
            }}
            QListWidget::item:hover {{
                background-color: {theme.bg_hover};
            }}
        """)
        self.toast.setStyleSheet(
            f"background-color: {theme.bg_card}; color: {theme.text_primary}; "
            f"border: 1px solid {theme.border_light}; border-radius: 10px; "
            f"padding: 10px 20px; font-size: 13px; font-weight: 500;"
        )

    def _on_theme_selected(self, _indice):
        self._aplicar_tema_por_nome(self.theme_combo.currentData())

    def _aplicar_tema_por_nome(self, novo: str):
        """Troca o tema e guarda a escolha."""
        from relay.config import set_theme_name
        from relay.gui.theme import TEMAS
        if novo not in TEMAS:
            return
        set_theme(TEMAS[novo])
        set_theme_name(novo)
        self._apply_theme()
        self.ws_selector.refresh_display()
        self._refresh_all()

    def _em_reuniao(self) -> bool:
        """Gravando ou transcrevendo — hora de não interromper."""
        if getattr(self, "_reuniao_em_curso", False):
            return True
        v = getattr(self, "transcricoes_view", None)
        try:
            return bool(v is not None and v.is_busy())
        except Exception:  # noqa: BLE001
            return False

    def _notificar_reuniao_em_curso(self):
        """Aviso do SO a cada 15 min enquanto a reunião estiver rodando."""
        if not self._em_reuniao():
            self._meeting_notice_timer.stop()
            return
        # "Reunião em progresso" é só para reunião; sessão de estudo não avisa
        view = getattr(self, "transcricoes_view", None)
        combo = getattr(view, "kind_combo", None)
        try:
            if combo is not None and combo.currentData() == "study":
                return
        except Exception:  # noqa: BLE001
            pass
        minutos = max(1, int(getattr(self, "_gravando_seg", 0) or 0) // 60)
        self._notificar_sistema(
            t("Reunião em progresso"),
            t("Em andamento há {n} min").format(n=minutos),
        )

    def _notificar_sistema(self, titulo: str, mensagem: str):
        """Notificação do sistema operacional — nunca o toast da interface."""
        try:
            from PySide6.QtWidgets import QSystemTrayIcon

            bandeja = getattr(self, "_tray", None) or getattr(self, "_tray_icon", None)
            if bandeja is not None and bandeja.supportsMessages():
                # 10s: o padrão de 5-6s some antes de a pessoa olhar para o canto
                bandeja.showMessage(titulo, mensagem, QSystemTrayIcon.Information, 10000)
                return
        except Exception:  # noqa: BLE001
            pass
        try:
            import subprocess

            subprocess.Popen(
                ["notify-send", "-a", "Relay", "-t", "10000", titulo, mensagem],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception:  # noqa: BLE001
            pass

    def _suspender_pausa(self):
        """Fecha a pausa aberta sem marcá-la como feita (a reunião começou)."""
        overlay = self._eyecare_overlay
        self._eyecare_overlay = None
        if overlay is None:
            return
        try:
            overlay.encerrar()
        except Exception:  # noqa: BLE001
            try:
                overlay.close()
            except Exception:  # noqa: BLE001
                pass

    def _maybe_show_eyecare(self):
        """Mostra a pausa se for devida e nada estiver segurando."""
        from relay import eyecare, features
        if not features.habilitada("eyecare"):
            return
        if self._eyecare_overlay is not None:
            return                      # já tem uma na tela
        if not eyecare.devida(em_reuniao=self._em_reuniao()):
            return
        self._mostrar_eyecare()

    def testar_eyecare(self):
        """Dispara a pausa na hora, ignorando ciclo e adiamento.

        É o que permite conferir a aparência e a duração sem esperar 20 min.
        Concluir/pular reinicia o ciclo normalmente, então testar não deixa uma
        pausa "atrasada" pronta para pular na cara logo em seguida.
        """
        if self._eyecare_overlay is not None:
            return
        self._mostrar_eyecare()

    def _mostrar_eyecare(self):
        from relay import eyecare
        from relay.gui.eyecare_break import EyecareBreak
        overlay = EyecareBreak(self, eyecare.config()["duracao_seg"],
                               dormir=eyecare.hora_de_dormir())
        overlay.concluida.connect(self._on_eyecare_concluida)
        overlay.adiada.connect(self._on_eyecare_adiada)
        self._eyecare_overlay = overlay
        overlay.iniciar()

    def _on_eyecare_concluida(self):
        from relay import eyecare
        eyecare.marcar_pausa_feita()
        self._eyecare_overlay = None

    def _on_eyecare_adiada(self):
        from relay import eyecare
        ate = eyecare.adiar()
        self._eyecare_overlay = None
        self.show_toast(t("Pausa adiada para {hora}").format(hora=ate.strftime("%H:%M")))

    def _lazy_factory(self, module_suffix: str, class_name: str):
        """Fábrica de tela: import + construção só acontecem no primeiro uso.

        `module_suffix` é relativo a `relay` (ex.: "gui.views.kb_view").
        """
        def factory():
            import importlib
            module = importlib.import_module(f"relay.{module_suffix}")
            return getattr(module, class_name)()
        return factory

    def _ensure_view(self, key):
        """Resolve a tela da chave, construindo-a agora se ainda for uma fábrica
        (lazy). Views já construídas voltam direto; novas entram no stack."""
        w = self._view_by_key.get(key)
        if w is None or isinstance(w, QWidget):
            return w
        widget = w()  # fábrica lazy: constrói agora
        self._view_by_key[key] = widget
        self.stack.addWidget(widget)
        return widget

    def _nav_row_for(self, key):
        for i in range(self.nav_list.count()):
            if self.nav_list.item(i).data(Qt.UserRole) == key:
                return i
        return None

    def _on_nav(self, row):
        item = self.nav_list.item(row)
        if item is None:
            return
        key = item.data(Qt.UserRole)
        if key:            # cabeçalhos de grupo não têm chave
            self._open_key(key)

    def _refresh_nav_icons(self):
        """Ícones da sidebar: o item ativo usa o accent, os demais o cinza."""
        from relay.gui.icons import nav_icon
        th = current_theme()
        atual = self.nav_list.currentRow()
        for i in range(self.nav_list.count()):
            item = self.nav_list.item(i)
            key = item.data(Qt.UserRole)
            if not key:
                continue
            cor = th.sidebar_active_text if i == atual else th.sidebar_muted
            item.setIcon(nav_icon(key, cor))

    def _toggle_sidebar(self, visivel=None):
        """Mostra/oculta o menu lateral. Estado persistido entre sessões."""
        if visivel is None:
            visivel = not self.sidebar.isVisible()
        if visivel:
            self.sidebar.show()
            largura = getattr(self, "_sidebar_width", None) or 224
            largura = max(160, min(420, int(largura)))
            total = max(600, self._splitter.width())
            self._splitter.setSizes([largura, max(300, total - largura)])
            self.menu_toggle_btn.setToolTip(t("Ocultar menu (F9)"))
        else:
            self._sidebar_width = self.sidebar.width()
            self.sidebar.hide()
            self.menu_toggle_btn.setToolTip(t("Mostrar menu (F9)"))
        try:
            from relay.config import load_config, save_config
            cfg = load_config()
            cfg.setdefault("settings", {})["sidebar_visible"] = bool(visivel)
            if visivel:
                cfg["settings"]["sidebar_width"] = int(self.sidebar.width())
            save_config(cfg)
        except Exception:  # noqa: BLE001
            pass

    def _open_key(self, key):
        """Troca a tela pela chave e sincroniza a sidebar e o título."""
        w = self._ensure_view(key)
        if w is None:
            return
        if key == "board" and not getattr(w, "project_id", None):
            # Vai direto ao kanban: usa o projeto ativo sem passar por Projetos.
            from relay.config import get_active_project_id
            pid = get_active_project_id()
            if pid and hasattr(w, "set_project"):
                w.set_project(pid)
        self._last_screen = key
        self.stack.setCurrentWidget(w)
        if hasattr(w, "refresh"):
            w.refresh()
        aplicar_sombras(w, escuro=is_dark())
        row = self._nav_row_for(key)
        if row is not None and row != self.nav_list.currentRow():
            self.nav_list.blockSignals(True)
            self.nav_list.setCurrentRow(row)
            self.nav_list.blockSignals(False)
        self.page_title.setText(self._labels.get(key, key))
        self.page_subtitle.setText(self._descricoes.get(key, ""))
        self._refresh_nav_icons()

    def _open_board(self, project_id):
        from relay.config import set_active_project_id
        set_active_project_id(project_id)
        self._populate_project_selector()
        self.board_view.set_project(project_id)
        self._atualizar_status()
        self._open_key("board")

    def _board_back_to_projects(self):
        """Voltar do kanban: limpa o projeto ativo e volta à lista do board.

        O desktop enxuto não tem Projetos no menu (padrao=False) — o seletor
        de projetos VIVE dentro do próprio Board (empty_widget). Voltar para
        \"projects\" quebraria quando a feature está desligada. Em vez disso,
        limpamos o projeto ativo e exibimos a lista interna do board.
        """
        from relay.config import set_active_project_id
        set_active_project_id(None)
        self._populate_project_selector()
        self.board_view.set_project(None)
        self._atualizar_status()
        self._open_key("board")

    def _open_task_from_dashboard(self, task_id):
        from relay.gui.views.task_detail_dialog import TaskDetailDialog
        dlg = TaskDetailDialog(task_id, self)
        dlg.task_updated.connect(self._refresh_all)
        dlg.exec()

    # ---- Projeto ativo (seletor do topo) ----
    def _populate_project_selector(self):
        """Lista os projetos do workspace ativo, marcando o projeto ativo."""
        from relay.config import get_active_project_id
        from relay.db.models import Project
        self._loading_projects = True
        try:
            self.project_selector.clear()
            self.project_selector.addItem(t("(nenhum projeto)"), None)
            s = get_session()
            try:
                for p in s.query(Project).order_by(Project.name).all():
                    self.project_selector.addItem(f"{p.key} · {p.name}", p.id)
            finally:
                s.close()
            active = get_active_project_id()
            idx = self.project_selector.findData(active) if active else -1
            self.project_selector.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self._loading_projects = False

    def _sync_project_selector(self, pid):
        """Reflete no topo o projeto escolhido em outra tela (sem redisparar)."""
        idx = self.project_selector.findData(pid)
        if idx >= 0 and idx != self.project_selector.currentIndex():
            self._loading_projects = True
            try:
                self.project_selector.setCurrentIndex(idx)
            finally:
                self._loading_projects = False
        self.board_view.set_project(pid)

    def _atualizar_status(self):
        """Barra de status: workspace · projeto ativo (contexto de onde salva)."""
        from relay.config import (
            get_active_project_id, get_active_workspace_id, list_workspaces)
        partes = []
        try:
            wid = get_active_workspace_id()
            ws = next((w for w in list_workspaces() if w.get("id") == wid), None)
            if ws and ws.get("name"):
                partes.append(ws["name"])
        except Exception:  # noqa: BLE001
            pass
        try:
            pid = get_active_project_id()
            if pid:
                s = get_session()
                try:
                    p = s.get(Project, pid)
                    if p is not None:
                        partes.append(f"{p.key} · {p.name}")
                finally:
                    s.close()
        except Exception:  # noqa: BLE001
            pass
        self.status.showMessage("   ·   ".join(partes))

    def _new_project(self):
        """Diálogo de novo projeto (nome + chave auto) a partir do seletor."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle(t("Novo Projeto"))
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        form.setSpacing(8)
        nome = QLineEdit()
        nome.setPlaceholderText(t("Nome do projeto"))
        form.addRow(t("Nome:"), nome)
        chave = QLineEdit()
        chave.setPlaceholderText("KEY")
        chave.setMaximumWidth(120)
        form.addRow(t("Chave:"), chave)
        nome.textChanged.connect(
            lambda txt: chave.setText(suggest_project_key(txt)) if not chave.hasFocus() else None)
        lay.addLayout(form)
        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(dlg.accept)
        botoes.rejected.connect(dlg.reject)
        lay.addWidget(botoes)
        if dlg.exec() != QDialog.Accepted:
            return
        pid = create_project_with_defaults(nome.text(), chave.text())
        if pid is None:
            return
        from relay.config import set_active_project_id
        set_active_project_id(pid)
        self._populate_project_selector()
        self.board_view.set_project(pid)
        if hasattr(self.transcricoes_view, "refresh"):
            self.transcricoes_view.refresh()
        self._refresh_all()
        self._atualizar_status()
        self.show_toast(t("Projeto ativo alterado"))

    def _on_project_selected(self):
        if getattr(self, "_loading_projects", False):
            return
        from relay.config import get_active_project_id, set_active_project_id
        pid = self.project_selector.currentData()
        if pid == get_active_project_id():
            return
        set_active_project_id(pid)
        # Reflete nas telas que dependem do projeto
        self.board_view.set_project(pid)
        if hasattr(self.transcricoes_view, "refresh"):
            self.transcricoes_view.refresh()
        self._refresh_all()
        self._atualizar_status()
        self.show_toast(t("Projeto ativo alterado"))

    def _on_workspace_changed(self, ws_id):
        db_path = get_workspace_db_path(ws_id)
        switch_db(db_path)
        self.board_view.set_project(None)
        self._refresh_all()
        self._populate_project_selector()  # projetos são por workspace
        self.ws_selector.refresh_display()
        self._atualizar_status()
        self.show_toast(t("Workspace alterado"))

    def _refresh_all(self):
        for i in range(self.stack.count()):
            w = self.stack.widget(i)
            if hasattr(w, "refresh"):
                w.refresh()

    # --- Search ---

    def _toggle_search(self):
        visible = not self.search_container.isVisible()
        self.search_container.setVisible(visible)
        self.search_bar.setVisible(visible)
        if visible:
            self.search_bar.setFocus()
            self.search_bar.selectAll()
        else:
            self._close_search()

    def _close_search(self):
        self.search_container.setVisible(False)
        self.search_bar.setVisible(False)
        self.search_bar.clear()
        self.search_results.setVisible(False)

    def _focus_search(self):
        self.search_container.setVisible(True)
        self.search_bar.setVisible(True)
        self.search_bar.setFocus()

    def _nova_reuniao_atalho(self):
        """Ctrl+N: abre Reuniões e começa uma do zero."""
        self._open_key("transcricoes")
        if hasattr(self.transcricoes_view, "_new_meeting"):
            self.transcricoes_view._new_meeting()

    def _novo_todo_atalho(self):
        """Ctrl+T: abre a aba TODOs e foca o campo de adicionar."""
        self._goto_todos()
        todo_view = getattr(self.dashboard_view, "_tab_todos", None)
        if todo_view is not None and hasattr(todo_view, "input"):
            todo_view.input.setFocus()

    def _mostrar_atalhos(self):
        """Ctrl+/: lista os atalhos de teclado."""
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, t("Atalhos de teclado"),
            "\n".join([
                "Ctrl+K   " + t("Busca global (tarefas, TODOs, projetos e reuniões)"),
                "Ctrl+N   " + t("Nova reunião"),
                "Ctrl+T   " + t("Novo TODO"),
                "Ctrl+B   " + t("Abrir o board"),
                "F9       " + t("Mostrar/ocultar menu"),
                "Ctrl+/   " + t("Esta ajuda"),
                "Alt+1…9  " + t("Abrir a N-ésima tela do menu"),
                "Esc      " + t("Fecha a busca"),
            ]))

    def _on_search(self, text):
        self.search_results.clear()
        if not text or len(text) < 2:
            self.search_results.setVisible(False)
            return

        query = text.lower()
        results = []

        # Tarefas do board (se houver projeto carregado)
        for task in getattr(self.board_view, "_tasks", []) or []:
            title = task.get("title", "")
            code = task.get("code", "")
            if query in title.lower() or query in code.lower():
                results.append({"kind": "task", "task": task,
                                "label": (f"{code}  {title}" if code else title),
                                "prefix": "🔧"})
                if len(results) >= 20:
                    break

        # TODOs
        if len(results) < 20:
            s = get_session()
            try:
                for td in s.query(Todo).all():
                    if query in (td.text or "").lower():
                        results.append({"kind": "todo", "text": td.text,
                                        "label": td.text, "prefix": "✅"})
                        if len(results) >= 20:
                            break
            finally:
                s.close()

        # Projetos
        if len(results) < 20:
            s = get_session()
            try:
                for p in s.query(Project).all():
                    if query in (p.name or "").lower() or query in (p.key or "").lower():
                        results.append({"kind": "project", "id": p.id,
                                        "label": f"{p.key} · {p.name}",
                                        "prefix": "📁"})
                        if len(results) >= 20:
                            break
            finally:
                s.close()

        # Reuniões (gravações)
        if len(results) < 20:
            s = get_session()
            try:
                for rec in s.query(Recording).filter(
                        Recording.archived_at == None  # noqa: E711
                    ).order_by(Recording.created_at.desc()).all():
                    if query in (rec.title or "").lower():
                        results.append({"kind": "meeting", "id": rec.id,
                                        "label": rec.title or t("(sem título)"),
                                        "prefix": "🎙"})
                        if len(results) >= 20:
                            break
            finally:
                s.close()

        if not results:
            self.search_results.setVisible(False)
            return

        for r in results:
            item = QListWidgetItem(f"{r['prefix']}  {r['label']}")
            item.setData(Qt.UserRole, r)
            self.search_results.addItem(item)

        # Position popup below search bar
        global_pos = self.search_bar.mapToGlobal(
            self.search_bar.rect().bottomLeft()
        )
        self.search_results.setFixedWidth(self.search_bar.width())
        self.search_results.setFixedHeight(
            min(len(results) * 36 + 10, 320)
        )
        self.search_results.move(global_pos)
        self.search_results.setVisible(True)

    def _on_search_result(self, item):
        r = item.data(Qt.UserRole)
        self.search_results.setVisible(False)
        self._close_search()
        if not r:
            return
        kind = r.get("kind")
        if kind == "task":
            if hasattr(self.board_view, "open_task_detail"):
                self.board_view.open_task_detail(r["task"])
                self._open_key("board")
        elif kind == "todo":
            self._goto_todos()
        elif kind == "project":
            self._open_board(r["id"])
        elif kind == "meeting":
            self._open_key("transcricoes")
            if hasattr(self.transcricoes_view, "abrir_gravacao"):
                self.transcricoes_view.abrir_gravacao(r["id"])

    # --- Notifications ---

    def _setup_notification_timer(self):
        self._notif_timer.stop()
        settings = self.settings_view.get_notification_settings()
        if settings["enabled"] and settings["interval_minutes"] > 0:
            self._notif_timer.start(settings["interval_minutes"] * 60 * 1000)
        pomodoro_mins = self.settings_view.pomodoro_duration.value()
        self.dashboard_view.pomodoro.set_duration_minutes(pomodoro_mins)

    def _setup_chat_compact_timer(self):
        self._chat_compact_timer.stop()
        try:
            from relay.config import get_chat_compact_config
            cfg = get_chat_compact_config()
        except Exception:
            return
        if cfg.get("enabled") and cfg.get("interval_min", 0) > 0:
            self._chat_compact_timer.start(max(5, int(cfg["interval_min"])) * 60 * 1000)

    def _send_chat_compact_reminder(self):
        try:
            from relay.config import get_chat_compact_config
            cfg = get_chat_compact_config()
        except Exception:
            return
        if not cfg.get("enabled"):
            return
        msg = t("Lembrete: hora de compactar o chat no opencode para economizar tokens (/compact)")
        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            from PySide6.QtGui import QIcon
            if getattr(self, "_tray", None) is not None:
                self._tray_icon = self._tray
            elif not hasattr(self, "_tray_icon"):
                self._tray_icon = QSystemTrayIcon(self)
                self._tray_icon.setIcon(QIcon.fromTheme("dialog-information"))
                self._tray_icon.show()
            if hasattr(self, "_tray_icon") and self._tray_icon.supportsMessages():
                self._tray_icon.showMessage("Relay", msg, QSystemTrayIcon.Information, 5000)
        except Exception:
            pass
        self.show_toast(msg)
        # Fallback notify-send se tray não suportar
        try:
            import subprocess
            if not getattr(self, "_tray_icon", None) or not self._tray_icon.supportsMessages():
                subprocess.Popen(
                    ["notify-send", "-a", "Relay", "Relay", msg],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except Exception:
            pass

    def _send_notification(self):
        settings = self.settings_view.get_notification_settings()
        if not settings["enabled"]:
            return
        msg = settings["message"] or t("Relay — lembrete")
        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            from PySide6.QtGui import QIcon
            if getattr(self, "_tray", None) is not None:
                self._tray_icon = self._tray      # uma bandeja só, não duas
            elif not hasattr(self, "_tray_icon"):
                self._tray_icon = QSystemTrayIcon(self)
                self._tray_icon.setIcon(QIcon.fromTheme("dialog-information"))
                self._tray_icon.show()
            if self._tray_icon.supportsMessages():
                self._tray_icon.showMessage("Relay", msg, QSystemTrayIcon.Information, 5000)
                return
        except Exception:
            pass
        import subprocess
        try:
            subprocess.Popen(
                ["notify-send", "-a", "Relay", "Relay", msg],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            self.show_toast(msg)

    # --- Toast ---

    def show_toast(self, msg, duration=2000):
        self.toast.show_message(msg, duration)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Barra superior responsiva: em janelas estreitas o seletor de projeto
        # some para dar lugar ao botão "Início" com texto (o projeto continua
        # acessível nas telas de Projetos/Reuniões).
        if hasattr(self, "project_selector"):
            self.project_selector.setVisible(self.width() >= 980)
        if self.toast.isVisible():
            self.toast.move(
                self.width() - self.toast.width() - 20,
                self.height() - 60,
            )
        if getattr(self, "coach_tip", None) is not None and self.coach_tip.isVisible():
            self.coach_tip.reposition()

    # --- Minimizar para bandeja ---

    def changeEvent(self, event):  # noqa: N802
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            tray = getattr(self, "_tray", None)
            if tray is not None:
                from PySide6.QtWidgets import QSystemTrayIcon
                if QSystemTrayIcon.isSystemTrayAvailable():
                    event.ignore()
                    QTimer.singleShot(0, self.hide)
                    return
        super().changeEvent(event)

    # --- Encerramento ---

    def showEvent(self, event):
        super().showEvent(event)
        # Restaura a largura exata da sidebar (o setSizes do __init__ é
        # proporcional; aqui a janela já tem largura real).
        if getattr(self, "_largura_sidebar_desejada", None) is not None:
            if self.sidebar.isVisible():
                w = self._largura_sidebar_desejada
                self._splitter.setSizes([w, max(300, self._splitter.width() - w)])
            self._largura_sidebar_desejada = None

    def closeEvent(self, event):
        """Encerra as threads antes de sair, senão o processo aborta.

        Sair com uma QThread em execução faz o destrutor do QThread disparar
        qFatal — o processo morre com SIGABRT e core dump (reproduzido). Isso
        acontecia ao fechar durante uma chamada de IA: o timeout é de 120s com
        retries, então um worker podia ficar vivo por minutos.

        QThread não tem cancelamento, então esperamos um tempo limitado; se
        ainda restar alguma thread viva, saímos SEM rodar os destrutores
        (os._exit), que é o único jeito de não abortar. Nesse ponto os dados já
        estão gravados: banco e config são escritos de forma síncrona.
        """
        # Persiste o estado da interface (largura e visibilidade da sidebar,
        # tela ativa).
        try:
            from relay.config import load_config, save_config
            cfg = load_config()
            cfg.setdefault("settings", {})["sidebar_width"] = int(
                getattr(self, "_sidebar_width", None) or self.sidebar.width())
            cfg["settings"]["sidebar_visible"] = bool(self.sidebar.isVisible())
            cfg.setdefault("settings", {})["last_screen"] = getattr(self, "_last_screen", "dashboard")
            tabs = getattr(self.dashboard_view, "_tabs", None)
            if tabs is not None:
                cfg.setdefault("settings", {})["dashboard_tab"] = tabs.currentIndex()
            save_config(cfg)
        except Exception:  # noqa: BLE001
            pass
        if not getattr(self, "_force_quit", False):
            tray = getattr(self, "_tray", None)
            if tray is not None:
                from PySide6.QtWidgets import QSystemTrayIcon
                if QSystemTrayIcon.isSystemTrayAvailable():
                    event.ignore()
                    self.hide()
                    return
        # Avisa se há reunião gravando: fechar aqui perderia a gravação.
        tv = getattr(self, "transcricoes_view", None)
        if tv is not None and tv.is_recording():
            from PySide6.QtWidgets import QMessageBox
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle(t("Reunião em andamento"))
            box.setText(t("Há uma reunião gravando. Fechar agora perderá a gravação."))
            salvar = box.addButton(t("Parar e salvar"), QMessageBox.AcceptRole)
            sair = box.addButton(t("Sair mesmo assim"), QMessageBox.DestructiveRole)
            box.addButton(t("Cancelar"), QMessageBox.RejectRole)
            box.exec()
            clicado = box.clickedButton()
            if clicado is salvar:
                try:
                    tv._stop_record()   # salva o áudio e inicia a transcrição
                except Exception:  # noqa: BLE001
                    pass
                event.ignore()          # fica aberto até a gravação ser salva
                return
            if clicado is not sair:
                event.ignore()          # "Cancelar"
                return
        all_stopped = True
        view = getattr(self, "transcricoes_view", None)
        if view is not None:
            try:
                all_stopped = view.shutdown()
            except Exception:  # noqa: BLE001
                all_stopped = False

        worker = getattr(self, "_coach_worker", None)
        if worker is not None and worker.isRunning():
            worker.wait(2000)
            if worker.isRunning():
                all_stopped = False

        # A gravação do provedor de IA espera a digitação parar; fechar antes
        # disso perderia a última edição.
        settings = getattr(self, "settings_view", None)
        if settings is not None and hasattr(settings, "_persistir_provedor_ai"):
            try:
                settings._persistir_provedor_ai()
            except Exception:  # noqa: BLE001
                logger.warning("Nao foi possivel gravar o provedor de IA ao sair.")

        tray = getattr(self, "_tray", None)
        if tray is not None:
            tray.hide()

        # A pausa agora é janela própria (e as coberturas dos outros monitores
        # não têm pai): sem fechar aqui, sair do Relay deixaria telas cheias
        # órfãs na área de trabalho.
        pausa = getattr(self, "_eyecare_overlay", None)
        if pausa is not None:
            pausa._encerrar()
            self._eyecare_overlay = None

        super().closeEvent(event)
        if not all_stopped:
            import os
            import sys
            logger.warning("Saindo com trabalho de IA em andamento (sem esperar).")
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(0)
