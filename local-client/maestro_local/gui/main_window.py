from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
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
from maestro_local.gui.views.board_view import BoardView
from maestro_local.gui.views.labels_view import LabelsView
from maestro_local.gui.views.metrics_view import MetricsView
from maestro_local.gui.views.projects_view import ProjectsView
from maestro_local.gui.views.skills_view import SkillsView


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


class MainWindow(QMainWindow):
    def __init__(self, api_port: int = 9777):
        super().__init__()
        self.api_port = api_port
        self.setWindowTitle("Maestro Local")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(220)
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        # Logo section
        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(16, 16, 16, 16)
        logo_layout.setSpacing(10)

        self.logo_badge = QLabel("M")
        self.logo_badge.setFixedSize(32, 32)
        self.logo_badge.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(self.logo_badge)

        self.logo_text = QLabel("Maestro")
        logo_layout.addWidget(self.logo_text)
        logo_layout.addStretch()

        self.logo_container = logo_container
        sb_layout.addWidget(logo_container)

        # Navigation list
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        nav_items = [
            ("Board", "board"),
            ("Projetos", "projects"),
            ("Labels", "labels"),
            ("Metricas", "metrics"),
            ("Skills", "skills"),
        ]
        for label, key in nav_items:
            icon = NAV_ICONS.get(key, "")
            item = QListWidgetItem(f"  {icon}   {label}")
            item.setData(Qt.UserRole, key)
            self.nav_list.addItem(item)

        self.nav_list.currentRowChanged.connect(self._on_nav)
        sb_layout.addWidget(self.nav_list)
        sb_layout.addStretch()

        # Theme toggle
        self.theme_btn = QPushButton("Tema escuro")
        self.theme_btn.setProperty("flat", True)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        sb_layout.addWidget(self.theme_btn)

        # API label
        self.api_label = QLabel(f"  API: localhost:{api_port}")
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
        self.search_bar.setPlaceholderText("Buscar tarefas... (Ctrl+K)")
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
        self.board_view = BoardView()
        self.projects_view = ProjectsView()
        self.labels_view = LabelsView()
        self.metrics_view = MetricsView()
        self.skills_view = SkillsView()

        self.stack.addWidget(self.board_view)
        self.stack.addWidget(self.projects_view)
        self.stack.addWidget(self.labels_view)
        self.stack.addWidget(self.metrics_view)
        self.stack.addWidget(self.skills_view)

        content_layout.addWidget(self.stack)
        layout.addWidget(content_widget)

        # Connections
        self.projects_view.project_selected.connect(self._open_board)
        self.board_view.task_changed.connect(self._refresh_all)

        # Default to Projects view
        self.nav_list.setCurrentRow(1)

        # Status bar
        self.status = QStatusBar()
        self.status.showMessage(f"API rodando em http://127.0.0.1:{api_port}")
        self.setStatusBar(self.status)

        # Toast notification
        self.toast = ToastWidget(self)

        # --- Keyboard shortcuts ---
        search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        search_shortcut.activated.connect(self._toggle_search)

        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self._close_search)

        for i in range(5):
            shortcut = QShortcut(QKeySequence(f"Alt+{i + 1}"), self)
            shortcut.activated.connect(lambda idx=i: self.nav_list.setCurrentRow(idx))

        self._apply_theme()

    def _apply_theme(self):
        t = current_theme()
        self.setStyleSheet(build_stylesheet(t))

        self.sidebar.setStyleSheet(
            f"background-color: {t.bg_sidebar}; border-right: 1px solid {t.border};"
        )
        self.logo_container.setStyleSheet(
            f"background-color: {t.bg_sidebar}; "
            f"border-bottom: 1px solid {t.border_light};"
        )
        self.logo_badge.setStyleSheet(
            f"background-color: {t.accent}; color: {t.text_on_accent}; "
            f"font-size: 16px; font-weight: 700; border-radius: 8px;"
        )
        self.logo_text.setStyleSheet(
            f"font-size: 17px; font-weight: 700; color: {t.text_primary}; "
            f"background: transparent;"
        )
        self.nav_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent; border: none; padding: 8px 6px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px 12px; border-radius: 6px; margin: 1px 6px;
                color: {t.text_secondary}; font-size: 13px;
            }}
            QListWidget::item:selected {{
                background-color: {t.bg_selected}; color: {t.text_primary};
                border-left: 3px solid {t.accent};
            }}
            QListWidget::item:hover:!selected {{
                background-color: {t.bg_hover};
            }}
        """)
        self.theme_btn.setStyleSheet(
            f"color: {t.text_muted}; font-size: 12px; padding: 8px 16px; "
            f"text-align: left; border: none; background: transparent;"
        )
        self.theme_btn.setText("Tema escuro" if not is_dark() else "Tema claro")
        self.api_label.setStyleSheet(
            f"color: {t.text_muted}; font-size: 11px; padding: 4px 16px;"
        )
        self.version_label.setStyleSheet(
            f"color: {t.text_muted}; font-size: 10px; padding: 2px 16px 12px 16px;"
        )
        self.status.setStyleSheet(
            f"background-color: {t.bg_sidebar}; color: {t.text_muted}; "
            f"border-top: 1px solid {t.border}; font-size: 12px; padding: 2px 8px;"
        )
        self.search_container.setStyleSheet(
            f"background-color: {t.bg_primary}; "
            f"border-bottom: 1px solid {t.border_light};"
        )
        self.search_results.setStyleSheet(f"""
            QListWidget {{
                background-color: {t.bg_card};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 4px;
                color: {t.text_primary};
            }}
            QListWidget::item:selected {{
                background-color: {t.bg_selected};
            }}
            QListWidget::item:hover {{
                background-color: {t.bg_hover};
            }}
        """)
        self.toast.setStyleSheet(
            f"background-color: {t.bg_card}; color: {t.text_primary}; "
            f"border: 1px solid {t.border}; border-radius: 8px; "
            f"padding: 8px 16px; font-size: 12px;"
        )

    def _toggle_theme(self):
        set_theme(DARK if not is_dark() else LIGHT)
        self._apply_theme()
        self._refresh_all()

    def _on_nav(self, row):
        self.stack.setCurrentIndex(row)
        w = self.stack.currentWidget()
        if hasattr(w, "refresh"):
            w.refresh()

    def _open_board(self, project_id):
        self.board_view.set_project(project_id)
        self.nav_list.setCurrentRow(0)

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
            self.nav_list.setCurrentRow(0)

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
