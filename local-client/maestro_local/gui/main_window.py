import logging

from PySide6.QtCore import QEvent, Qt, QTimer
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
    QStackedWidget,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from maestro_local.gui.theme import (
    PRIORITY_LABELS,  # noqa: F401 - exported for other modules
    build_stylesheet,
    current_theme,
    set_theme,
)
from maestro_local.config import get_active_workspace_id, get_workspace_db_path
from maestro_local.i18n import t
from maestro_local import features
from maestro_local.db.models import Todo, get_session, switch_db
from maestro_local.gui.views.board_view import BoardView
from maestro_local.gui.views.daily_view import DailyView
from maestro_local.gui.views.dashboard_view import DashboardView
from maestro_local.gui.views.chat_view import ChatView
from maestro_local.gui.views.transcricoes_view import TranscricoesView
from maestro_local.gui.views.tools_hub_view import ToolsHubView
from maestro_local.gui.views.settings_view import SettingsView
from maestro_local.gui.views.projects_view import ProjectsView
from maestro_local.gui.views.study_view import StudyView
from maestro_local.gui.views.home_view import HomeView, SECOES
# Telas raramente abertas (vault/library/apitester/kb/memory/english/translate/
# skills/guide): import E CONSTRUÇÃO tardios (ver _ensure_view). Nenhuma delas é
# referenciada fora do dicionário de navegação, então adiar é seguro — a tela só
# custa memória/import quando o usuário de fato a abre.
from maestro_local.gui.workspace_selector import WorkspaceSelectorButton
from maestro_local.todos import todos_abertos

logger = logging.getLogger("maestro.gui.main_window")


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
    def __init__(self, api_port: int = 9777):
        super().__init__()
        self.api_port = api_port
        self.setWindowTitle("Agentic Dev Maestro")
        self.resize(1120, 720)
        self.setMinimumSize(840, 540)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Barra superior ---
        # Sem painel lateral: marca, contexto, busca, notificações e tema no topo.
        self.topbar = QFrame()
        self.topbar.setObjectName("topBar")
        self.topbar.setFixedHeight(58)
        top = QHBoxLayout(self.topbar)
        top.setContentsMargins(16, 8, 16, 8)
        top.setSpacing(10)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        self.brand_name = QLabel("Agentic Dev")
        self.brand_name.setObjectName("brandName")
        self.brand_subtitle = QLabel("MAESTRO")
        self.brand_subtitle.setObjectName("brandSub")
        brand_text.addWidget(self.brand_name)
        brand_text.addWidget(self.brand_subtitle)
        top.addLayout(brand_text)

        # Início: volta para a home (lançador).
        self.home_btn = QToolButton()
        self.home_btn.setProperty("class", "topIcon")
        self.home_btn.setToolTip(t("Início"))
        self.home_btn.setCursor(Qt.PointingHandCursor)
        self.home_btn.clicked.connect(lambda: self._open_key("home"))
        top.addWidget(self.home_btn)

        top.addSpacing(8)

        # Contexto: para ONDE o trabalho vai (workspace + projeto).
        self.ws_selector = WorkspaceSelectorButton()
        self.ws_selector.setMinimumWidth(150)
        self.ws_selector.setMaximumWidth(210)
        self.ws_selector.workspace_changed.connect(self._on_workspace_changed)
        top.addWidget(self.ws_selector)

        # Seletor de projeto ativo. Ignora a roda do mouse: só troca clicando.
        from maestro_local.gui.no_wheel_combo import NoWheelComboBox
        self.project_selector = NoWheelComboBox()
        self.project_selector.setMinimumWidth(150)
        self.project_selector.setMaximumWidth(210)
        self.project_selector.setToolTip(t("Projeto ativo"))
        self.project_selector.currentIndexChanged.connect(self._on_project_selected)
        top.addWidget(self.project_selector)

        top.addStretch(1)

        # Gravação rápida (quando ligada em Funcionalidades).
        self.quick_record_btn = QToolButton()
        self.quick_record_btn.setProperty("class", "topIcon")
        self.quick_record_btn.setCursor(Qt.PointingHandCursor)
        self.quick_record_btn.setToolTip(t("Gravar reunião"))
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

        # Notificações: sino com a contagem de TODOs pendentes no topo.
        self.notif_btn = QToolButton()
        self.notif_btn.setProperty("class", "topIcon")
        self.notif_btn.setCursor(Qt.PointingHandCursor)
        self.notif_btn.clicked.connect(self._show_todo_menu)
        top.addWidget(self.notif_btn)
        self.notif_badge = QLabel("")
        self.notif_badge.setObjectName("badgeCount")
        self.notif_badge.hide()
        top.addWidget(self.notif_badge)

        # Seletor de tema: o select mostra todas as opções (um botão que cicla
        # esconderia as escolhas).
        from PySide6.QtWidgets import QComboBox
        from maestro_local.gui.theme import NOMES_TEMAS, ROTULOS_TEMAS
        self.theme_combo = QComboBox()
        self.theme_combo.setCursor(Qt.PointingHandCursor)
        for nome in NOMES_TEMAS:
            self.theme_combo.addItem(t(ROTULOS_TEMAS[nome]), nome)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_selected)
        top.addWidget(self.theme_combo)

        layout.addWidget(self.topbar)

        # Telas visíveis, na ordem das seções da home: base dos atalhos Alt+N e
        # dos testes de funcionalidades (features ligadas/desligadas).
        self._nav_keys: list[str] = [k for _, chaves in SECOES for k in chaves
                                     if features.habilitada(k)]

        # --- Content area ---
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

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
        self.stack = QStackedWidget()

        # Home (lançador): primeira tela, substitui o painel lateral.
        self.home_view = HomeView()
        self.home_view.open_key.connect(self._open_key)
        self.home_view.open_todos.connect(self._goto_todos)
        self.home_view.eyecare_test.connect(self.testar_eyecare)

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

        self.stack.addWidget(self.home_view)
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
            "home": self.home_view,
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
        }

        content_layout.addWidget(self.stack)
        layout.addWidget(content_widget)

        # Connections
        self.projects_view.project_selected.connect(self._open_board)
        self.board_view.project_opened.connect(self._open_board)
        self.board_view.task_changed.connect(self._refresh_all)
        self.dashboard_view.task_clicked.connect(self._open_task_from_dashboard)
        self.dashboard_view.project_clicked.connect(self._open_board)

        # Default to Home (lançador)
        self._open_key("home")

        # Status bar
        self.status = QStatusBar()
        self.status.showMessage(t("API rodando em http://127.0.0.1:{port}").format(port=api_port))
        self.setStatusBar(self.status)

        # Toast notification
        self.toast = ToastWidget(self)

        # --- Keyboard shortcuts ---
        search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        search_shortcut.activated.connect(self._toggle_search)

        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self._close_search)

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

        # Pausa para os olhos: verifica de minuto em minuto (a precisão de um
        # lembrete de 20 min não precisa ser melhor que isso).
        self._eyecare_overlay = None
        self._eyecare_timer = QTimer(self)
        self._eyecare_timer.setInterval(60000)
        self._eyecare_timer.timeout.connect(self._maybe_show_eyecare)
        self._eyecare_timer.start()

        # Bandeja: adiar a pausa sem precisar trazer a janela para a frente.
        from maestro_local.gui.icons import icone_do_app
        from maestro_local.gui.tray import instalar as instalar_bandeja
        self.setWindowIcon(icone_do_app())
        self._tray = instalar_bandeja(self)
        self._force_quit = False

        # Coach proativo: dicas do agente ao longo do dia (opt-in em Configurações)
        from maestro_local.gui.coach_widget import CoachTip
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
        self._apply_theme()

    # ---- Coach proativo ----
    def _setup_coach_timer(self):
        from maestro_local.config import get_coach_config
        cfg = get_coach_config()
        self._coach_timer.stop()
        if cfg.get("enabled"):
            self._coach_timer.setInterval(max(15, cfg.get("interval_min", 90)) * 60000)
            self._coach_timer.start()
            # Primeira dica pouco depois de abrir (não logo no boot).
            QTimer.singleShot(90000, self._maybe_coach_tip)

    def _maybe_coach_tip(self):
        import time

        from maestro_local.config import get_active_ai_provider, get_coach_config
        if not get_coach_config().get("enabled"):
            return
        if self._coach_worker is not None:
            return
        if not get_active_ai_provider():
            return
        from maestro_local.gui.coach_widget import CoachWorker
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

        from maestro_local.config import get_active_ai_provider, get_coach_config
        cfg = get_coach_config()
        if not cfg.get("enabled") or self._coach_worker is not None:
            return
        if not get_active_ai_provider():
            return
        cooldown = max(15, int(cfg.get("interval_min", 90)) // 2) * 60
        if time.monotonic() - self._last_coach_monotonic < cooldown:
            return
        from maestro_local import coach
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
        from maestro_local import features
        if not features.habilitada("todo_reminder"):
            return
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
        self._update_notif_badge(abertos)
        if ids:
            self.todo_reminder.show_count(len(ids))  # reaparece a cada ciclo enquanto houver pendentes
        else:
            self.todo_reminder.hide()

    def _update_notif_badge(self, n):
        """Sino do topo: contagem de TODOs pendentes (some quando zera)."""
        self.notif_badge.setText(str(n) if n else "")
        self.notif_badge.setVisible(bool(n))
        self.notif_btn.setToolTip(
            t("{n} TODO(s) pendente(s)").format(n=n) if n else t("Sem pendências"))

    def _show_todo_menu(self):
        """Menu do sino: lista as pendências e as ações rápidas."""
        menu = QMenu(self)
        itens = todos_abertos(limite=8)
        if itens:
            for item in itens:
                acao = menu.addAction(item["text"])
                acao.triggered.connect(self._goto_todos)
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

    def _transcricoes_quick_toggle(self):
        self._open_key("transcricoes")
        self.transcricoes_view.toggle_record_external()

    def _on_recording_state(self, gravando: bool, segundos: int = 0):
        """Espelha no botão do topo o estado da gravação rápida."""
        self._gravando = bool(gravando)
        self._gravando_seg = int(segundos or 0)
        self._atualizar_icone_gravacao()

    def _atualizar_icone_gravacao(self):
        if not hasattr(self, "quick_record_btn"):
            return
        if getattr(self, "_gravando", False):
            m, s = divmod(int(getattr(self, "_gravando_seg", 0)), 60)
            self.quick_record_btn.setText(f"■ {m:02d}:{s:02d}")
            self.quick_record_btn.setToolTip(t("Parar gravação"))
        else:
            self.quick_record_btn.setText(t("Gravar"))
            self.quick_record_btn.setToolTip(t("Gravar reunião"))

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
        from maestro_local.transcricoes.transcriber import release_model
        release_model()

    def _setup_global_hotkeys(self):
        try:
            from maestro_local.transcricoes.constants import HOTKEY_TOGGLE_RECORDING
            from maestro_local.transcricoes.hotkeys import GlobalHotkeys
            self._hotkeys = GlobalHotkeys()
            self._hotkeys.start({
                HOTKEY_TOGGLE_RECORDING: self.transcricoes_view.toggle_record_external,
            })
        except Exception:  # noqa: BLE001
            self._hotkeys = None

    def _apply_theme(self):
        theme = current_theme()
        from maestro_local.gui.icons import clear_cache, nav_icon
        clear_cache()   # os ícones são coloridos pelo tema
        self.setStyleSheet(build_stylesheet(theme))

        # Ícones da barra superior: são pixmaps, então o QSS não os recolore.
        self.home_btn.setIcon(nav_icon("home", theme.text_secondary, size=20))
        self.search_btn.setIcon(nav_icon("search", theme.text_secondary, size=20))
        self.notif_btn.setIcon(nav_icon("bell", theme.text_secondary, size=20))
        self.quick_record_btn.setIcon(
            nav_icon("transcricoes", theme.text_secondary, size=18))
        self._atualizar_icone_gravacao()

        self.home_view.apply_theme()
        self.dashboard_view.pomodoro.apply_theme(theme)
        from maestro_local.gui.theme import nome_do_tema
        atual = nome_do_tema(theme)
        # Sem bloquear, reposicionar o select dispararia outra troca de tema.
        self.theme_combo.blockSignals(True)
        indice = self.theme_combo.findData(atual)
        if indice >= 0:
            self.theme_combo.setCurrentIndex(indice)
        self.theme_combo.blockSignals(False)
        self.status.setStyleSheet(
            f"background-color: {theme.bg_sidebar}; color: {theme.text_muted}; "
            f"border-top: 1px solid {theme.border}; font-size: 12px; padding: 2px 8px;"
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
        from maestro_local.config import set_theme_name
        from maestro_local.gui.theme import TEMAS
        if novo not in TEMAS:
            return
        set_theme(TEMAS[novo])
        set_theme_name(novo)
        self._apply_theme()
        self.ws_selector.refresh_display()
        self._refresh_all()

    def _em_reuniao(self) -> bool:
        """Gravando ou transcrevendo — hora de não interromper."""
        v = getattr(self, "transcricoes_view", None)
        try:
            return bool(v is not None and v.is_busy())
        except Exception:  # noqa: BLE001
            return False

    def _maybe_show_eyecare(self):
        """Mostra a pausa se for devida e nada estiver segurando."""
        from maestro_local import eyecare, features
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
        from maestro_local import eyecare
        from maestro_local.gui.eyecare_break import EyecareBreak
        overlay = EyecareBreak(self, eyecare.config()["duracao_seg"],
                               dormir=eyecare.hora_de_dormir())
        overlay.concluida.connect(self._on_eyecare_concluida)
        overlay.adiada.connect(self._on_eyecare_adiada)
        self._eyecare_overlay = overlay
        overlay.iniciar()

    def _on_eyecare_concluida(self):
        from maestro_local import eyecare
        eyecare.marcar_pausa_feita()
        self._eyecare_overlay = None

    def _on_eyecare_adiada(self):
        from maestro_local import eyecare
        ate = eyecare.adiar()
        self._eyecare_overlay = None
        self.show_toast(t("Pausa adiada para {hora}").format(hora=ate.strftime("%H:%M")))

    def _lazy_factory(self, module_suffix: str, class_name: str):
        """Fábrica de tela: import + construção só acontecem no primeiro uso.

        `module_suffix` é relativo a `maestro_local` (ex.: "gui.views.kb_view").
        """
        def factory():
            import importlib
            module = importlib.import_module(f"maestro_local.{module_suffix}")
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

    def _open_key(self, key):
        """Troca a tela pela chave (home ou qualquer funcionalidade)."""
        w = self._ensure_view(key)
        if w is None:
            return
        self.stack.setCurrentWidget(w)
        if hasattr(w, "refresh"):
            w.refresh()

    def _open_board(self, project_id):
        self.board_view.set_project(project_id)
        self._open_key("board")

    def _open_task_from_dashboard(self, task_id):
        from maestro_local.gui.views.task_detail_dialog import TaskDetailDialog
        dlg = TaskDetailDialog(task_id, self)
        dlg.task_updated.connect(self._refresh_all)
        dlg.exec()

    # ---- Projeto ativo (seletor do topo) ----
    def _populate_project_selector(self):
        """Lista os projetos do workspace ativo, marcando o projeto ativo."""
        from maestro_local.config import get_active_project_id
        from maestro_local.db.models import Project
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

    def _on_project_selected(self):
        if getattr(self, "_loading_projects", False):
            return
        from maestro_local.config import get_active_project_id, set_active_project_id
        pid = self.project_selector.currentData()
        if pid == get_active_project_id():
            return
        set_active_project_id(pid)
        # Reflete nas telas que dependem do projeto
        self.board_view.set_project(pid)
        if hasattr(self.transcricoes_view, "refresh"):
            self.transcricoes_view.refresh()
        self.show_toast(t("Projeto ativo alterado"))

    def _on_workspace_changed(self, ws_id):
        db_path = get_workspace_db_path(ws_id)
        switch_db(db_path)
        self.board_view.set_project(None)
        self._refresh_all()
        self._populate_project_selector()  # projetos são por workspace
        self.ws_selector.refresh_display()
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

    def _on_search(self, text):
        self.search_results.clear()
        if not text or len(text) < 2:
            self.search_results.setVisible(False)
            return

        query = text.lower()
        results = []

        # Search in board_view tasks if available
        if hasattr(self.board_view, "_tasks"):
            for task in self.board_view._tasks:
                title = task.get("title", "")
                code = task.get("code", "")
                if query in title.lower() or query in code.lower():
                    results.append(task)
                    if len(results) >= 10:
                        break

        if not results:
            self.search_results.setVisible(False)
            return

        for task in results:
            code = task.get("code", "")
            title = task.get("title", "")
            item = QListWidgetItem(f"{code}  {title}" if code else title)
            item.setData(Qt.UserRole, task)
            self.search_results.addItem(item)

        # Position popup below search bar
        global_pos = self.search_bar.mapToGlobal(
            self.search_bar.rect().bottomLeft()
        )
        self.search_results.setFixedWidth(self.search_bar.width())
        self.search_results.setFixedHeight(
            min(len(results) * 36 + 10, 300)
        )
        self.search_results.move(global_pos)
        self.search_results.setVisible(True)

    def _on_search_result(self, item):
        task = item.data(Qt.UserRole)
        self.search_results.setVisible(False)
        self._close_search()
        if task and hasattr(self.board_view, "open_task_detail"):
            self.board_view.open_task_detail(task)
            self._open_key("board")

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
            from maestro_local.config import get_chat_compact_config
            cfg = get_chat_compact_config()
        except Exception:
            return
        if cfg.get("enabled") and cfg.get("interval_min", 0) > 0:
            self._chat_compact_timer.start(max(5, int(cfg["interval_min"])) * 60 * 1000)

    def _send_chat_compact_reminder(self):
        try:
            from maestro_local.config import get_chat_compact_config
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
                self._tray_icon.showMessage("Agentic Dev Maestro", msg, QSystemTrayIcon.Information, 5000)
        except Exception:
            pass
        self.show_toast(msg)
        # Fallback notify-send se tray não suportar
        try:
            import subprocess
            if not getattr(self, "_tray_icon", None) or not self._tray_icon.supportsMessages():
                subprocess.Popen(
                    ["notify-send", "-a", "Maestro", "Agentic Dev Maestro", msg],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except Exception:
            pass

    def _send_notification(self):
        settings = self.settings_view.get_notification_settings()
        if not settings["enabled"]:
            return
        msg = settings["message"] or t("Maestro — lembrete")
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
                self._tray_icon.showMessage("Agentic Dev Maestro", msg, QSystemTrayIcon.Information, 5000)
                return
        except Exception:
            pass
        import subprocess
        try:
            subprocess.Popen(
                ["notify-send", "-a", "Maestro", "Agentic Dev Maestro", msg],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            self.show_toast(msg)

    # --- Toast ---

    def show_toast(self, msg, duration=2000):
        self.toast.show_message(msg, duration)

    def resizeEvent(self, event):
        super().resizeEvent(event)
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
        if not getattr(self, "_force_quit", False):
            tray = getattr(self, "_tray", None)
            if tray is not None:
                from PySide6.QtWidgets import QSystemTrayIcon
                if QSystemTrayIcon.isSystemTrayAvailable():
                    event.ignore()
                    self.hide()
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
        # não têm pai): sem fechar aqui, sair do Maestro deixaria telas cheias
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
