from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from maestro_local.gui.theme import (
    DARK,
    LIGHT,
    NAV_ICONS,
    PRIORITY_LABELS,  # noqa: F401 - exported for other modules
    build_stylesheet,
    current_theme,
    is_dark,
    set_theme,
)
from maestro_local.config import get_active_workspace_id, get_workspace_db_path
from maestro_local.i18n import t
from maestro_local.db.models import Todo, get_session, switch_db
from maestro_local.gui.views.board_view import BoardView
from maestro_local.gui.views.daily_view import DailyView
from maestro_local.gui.views.dashboard_view import DashboardView
from maestro_local.gui.views.chat_view import ChatView
from maestro_local.gui.views.transcricoes_view import TranscricoesView
from maestro_local.gui.views.guide_view import GuideView
from maestro_local.gui.views.settings_view import SettingsView
from maestro_local.gui.views.projects_view import ProjectsView
from maestro_local.gui.views.skills_view import SkillsView
from maestro_local.gui.views.study_view import StudyView
from maestro_local.gui.widgets.transcricoes_quick import TranscricoesQuickWidget
from maestro_local.gui.workspace_selector import WorkspaceSelectorButton


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
        self.resize(960, 640)
        self.setMinimumSize(700, 450)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(180)
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        # Logo / branding section
        logo_container = QWidget()
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(12, 8, 12, 6)
        logo_layout.setSpacing(2)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)

        self.logo_badge = QLabel("A")
        self.logo_badge.setFixedSize(28, 28)
        self.logo_badge.setAlignment(Qt.AlignCenter)
        brand_row.addWidget(self.logo_badge)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        self.logo_text = QLabel("Agentic Dev")
        self.logo_subtitle = QLabel("Maestro")
        brand_text.addWidget(self.logo_text)
        brand_text.addWidget(self.logo_subtitle)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()

        logo_layout.addLayout(brand_row)

        self.logo_container = logo_container
        sb_layout.addWidget(logo_container)

        # Workspace selector (Obsidian-style)
        self.ws_selector = WorkspaceSelectorButton()
        self.ws_selector.workspace_changed.connect(self._on_workspace_changed)
        sb_layout.addWidget(self.ws_selector)

        # Section label: workspace
        self.section_label_work = QLabel("  " + t("WORKSPACE"))
        sb_layout.addWidget(self.section_label_work)

        # Navigation list
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        nav_items = [
            (t("Dashboard"), "dashboard"),
            (t("Meu Dia"), "daily"),
            (t("Estudos"), "study"),
            (t("Board"), "board"),
            (t("Assistente"), "chat"),
            (t("Reuniões"), "transcricoes"),
            (t("Projetos"), "projects"),
            (t("Skills"), "skills"),
            (t("Instruções"), "guide"),
            (t("Configurações"), "settings"),
        ]
        for label, key in nav_items:
            icon = NAV_ICONS.get(key, "")
            item = QListWidgetItem(f"  {icon}   {label}")
            item.setData(Qt.UserRole, key)
            self.nav_list.addItem(item)

        self.nav_list.currentRowChanged.connect(self._on_nav)
        sb_layout.addWidget(self.nav_list)

        # Transcrições — acesso rápido à gravação
        self.transcricoes_quick = TranscricoesQuickWidget()
        self.transcricoes_quick.toggle_requested.connect(self._transcricoes_quick_toggle)
        self.transcricoes_quick.open_requested.connect(lambda: self.nav_list.setCurrentRow(5))
        sb_layout.addWidget(self.transcricoes_quick)

        sb_layout.addSpacing(12)

        # Theme toggle
        self.theme_btn = QPushButton(t("Tema escuro"))
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        sb_layout.addWidget(self.theme_btn)

        # API label
        self.api_label = QLabel("  " + t("API: localhost:{port}").format(port=api_port))
        sb_layout.addWidget(self.api_label)

        # Version label
        self.version_label = QLabel("  v1.0.0")
        sb_layout.addWidget(self.version_label)

        layout.addWidget(self.sidebar)

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
        self.dashboard_view = DashboardView()
        self.daily_view = DailyView()
        self.study_view = StudyView()
        self.board_view = BoardView()
        self.chat_view = ChatView()
        self.transcricoes_view = TranscricoesView()
        self.projects_view = ProjectsView()
        self.skills_view = SkillsView()
        self.guide_view = GuideView()
        self.settings_view = SettingsView()
        self.settings_view.notification_changed.connect(self._setup_notification_timer)
        self.settings_view.ai_provider_changed.connect(self.chat_view.refresh)

        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.daily_view)
        self.stack.addWidget(self.study_view)
        self.stack.addWidget(self.board_view)
        self.stack.addWidget(self.chat_view)
        self.stack.addWidget(self.transcricoes_view)
        self.stack.addWidget(self.projects_view)
        self.stack.addWidget(self.skills_view)
        self.stack.addWidget(self.guide_view)
        self.stack.addWidget(self.settings_view)

        content_layout.addWidget(self.stack)
        layout.addWidget(content_widget)

        # Connections
        self.projects_view.project_selected.connect(self._open_board)
        self.board_view.project_opened.connect(self._open_board)
        self.board_view.task_changed.connect(self._refresh_all)
        self.dashboard_view.task_clicked.connect(self._open_task_from_dashboard)
        self.dashboard_view.project_clicked.connect(self._open_board)

        # Default to Meu Dia view
        self.nav_list.setCurrentRow(1)

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

        for i in range(10):
            shortcut = QShortcut(QKeySequence(f"Alt+{i + 1}" if i < 9 else "Alt+0"), self)
            shortcut.activated.connect(lambda idx=i: self.nav_list.setCurrentRow(idx))

        self._notif_timer = QTimer(self)
        self._notif_timer.timeout.connect(self._send_notification)
        self._setup_notification_timer()

        self._setup_global_hotkeys()

        # Atualiza o widget rápido de Transcrições (estado de gravação)
        self._transcricoes_poll = QTimer(self)
        self._transcricoes_poll.setInterval(1000)
        self._transcricoes_poll.timeout.connect(self._update_transcricoes_quick)
        self._transcricoes_poll.start()

        # Lembrete periódico de TODOs pendentes (só na interface)
        self.todo_reminder = TodoReminder(
            self, self._goto_todos, self._snooze_todos, self._dismiss_todos)
        self._pending_todo_ids = []
        self._todo_timer = QTimer(self)
        self._todo_timer.setInterval(60000)  # a cada 1 min
        self._todo_timer.timeout.connect(self._check_todo_reminders)
        self._todo_timer.start()
        QTimer.singleShot(4000, self._check_todo_reminders)

        self._apply_theme()

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
        finally:
            s.close()
        self._pending_todo_ids = ids
        if ids:
            self.todo_reminder.show_count(len(ids))  # reaparece a cada ciclo enquanto houver pendentes
        else:
            self.todo_reminder.hide()

    def _goto_todos(self):
        self.todo_reminder.hide()
        self.nav_list.setCurrentRow(0)  # Dashboard (aba TODOs fica lá)
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
        self.nav_list.setCurrentRow(5)
        self.transcricoes_view.toggle_record_external()

    def _update_transcricoes_quick(self):
        rec = self.transcricoes_view.is_recording()
        self.transcricoes_quick.set_recording(rec, self.transcricoes_view.elapsed_seconds())

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
        self.setStyleSheet(build_stylesheet(theme))

        self.sidebar.setStyleSheet(
            f"background-color: {theme.bg_sidebar}; border-right: 1px solid {theme.border};"
        )
        self.logo_container.setStyleSheet(
            f"background-color: {theme.bg_sidebar}; "
            f"border-bottom: 1px solid {theme.border_light};"
        )
        self.logo_badge.setStyleSheet(
            f"background-color: {theme.accent}; color: {theme.text_on_accent}; "
            f"font-size: 14px; font-weight: 800; border-radius: 7px;"
        )
        self.logo_text.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {theme.text_primary}; "
            f"background: transparent; letter-spacing: 0.3px;"
        )
        self.logo_subtitle.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {theme.accent}; "
            f"background: transparent; letter-spacing: 0.8px;"
        )
        self.section_label_work.setStyleSheet(
            f"color: {theme.text_muted}; font-size: 9px; font-weight: 700; "
            f"letter-spacing: 1.2px; padding: 6px 12px 2px 12px; background: transparent;"
        )
        self.nav_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent; border: none; padding: 2px 2px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 5px 10px; border-radius: 5px; margin: 1px 4px;
                color: {theme.text_secondary}; font-size: 12px;
            }}
            QListWidget::item:selected {{
                background-color: {theme.bg_selected}; color: {theme.text_primary};
                font-weight: 600;
            }}
            QListWidget::item:hover:!selected {{
                background-color: {theme.bg_hover};
            }}
        """)
        self.transcricoes_quick.apply_theme(theme)
        self.dashboard_view.pomodoro.apply_theme(theme)
        theme_icon = "☾" if not is_dark() else "☀"
        self.theme_btn.setText(f"  {theme_icon}   {t('Tema escuro') if not is_dark() else t('Tema claro')}")
        self.theme_btn.setStyleSheet(
            f"color: {theme.text_muted}; font-size: 11px; padding: 4px 12px; "
            f"text-align: left; border: 1px solid {theme.border}; background: transparent; "
            f"border-radius: 6px; margin: 2px 4px;"
        )
        self.api_label.setStyleSheet(
            f"color: {theme.text_muted}; font-size: 9px; padding: 2px 12px; background: transparent;"
        )
        self.version_label.setStyleSheet(
            f"color: {theme.text_muted}; font-size: 9px; padding: 1px 12px 8px 12px; background: transparent;"
        )
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

    def _toggle_theme(self):
        set_theme(DARK if not is_dark() else LIGHT)
        self._apply_theme()
        self.ws_selector.refresh_display()
        self._refresh_all()

    def _on_nav(self, row):
        self.stack.setCurrentIndex(row)
        w = self.stack.currentWidget()
        if hasattr(w, "refresh"):
            w.refresh()

    def _open_board(self, project_id):
        self.board_view.set_project(project_id)
        self.nav_list.setCurrentRow(3)

    def _open_task_from_dashboard(self, task_id):
        from maestro_local.gui.views.task_detail_dialog import TaskDetailDialog
        dlg = TaskDetailDialog(task_id, self)
        dlg.task_updated.connect(self._refresh_all)
        dlg.exec()

    def _on_workspace_changed(self, ws_id):
        db_path = get_workspace_db_path(ws_id)
        switch_db(db_path)
        self.board_view.set_project(None)
        self._refresh_all()
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
            self.nav_list.setCurrentRow(3)

    # --- Notifications ---

    def _setup_notification_timer(self):
        self._notif_timer.stop()
        settings = self.settings_view.get_notification_settings()
        if settings["enabled"] and settings["interval_minutes"] > 0:
            self._notif_timer.start(settings["interval_minutes"] * 60 * 1000)
        pomodoro_mins = self.settings_view.pomodoro_duration.value()
        self.dashboard_view.pomodoro.set_duration_minutes(pomodoro_mins)

    def _send_notification(self):
        settings = self.settings_view.get_notification_settings()
        if not settings["enabled"]:
            return
        msg = settings["message"] or t("Maestro — lembrete")
        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            from PySide6.QtGui import QIcon
            if not hasattr(self, "_tray_icon"):
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
