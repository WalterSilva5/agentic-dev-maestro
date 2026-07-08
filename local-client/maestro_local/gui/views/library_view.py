"""Biblioteca do desenvolvedor: snippets & prompts, runbooks de comandos e
importação de TODO/FIXME do código para o board."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from maestro_local.db.models import (
    BoardColumn,
    Comment,
    Project,
    Runbook,
    Snippet,
    Task,
    TimeLog,
    get_session,
)
from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t as _t


def _clip(text: str):
    from PySide6.QtWidgets import QApplication
    QApplication.clipboard().setText(text or "")


# ---------------------------------------------------------------------------
# Diálogos de edição
# ---------------------------------------------------------------------------
class SnippetDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle(_t("Snippet / Prompt"))
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)

        self.title = QLineEdit((data or {}).get("title", ""))
        self.title.setPlaceholderText(_t("Título"))
        lay.addWidget(self.title)

        row = QHBoxLayout()
        self.kind = QComboBox()
        self.kind.addItem(_t("Snippet"), "SNIPPET")
        self.kind.addItem(_t("Prompt"), "PROMPT")
        if data and data.get("kind") == "PROMPT":
            self.kind.setCurrentIndex(1)
        row.addWidget(self.kind)
        self.language = QLineEdit((data or {}).get("language", ""))
        self.language.setPlaceholderText(_t("Linguagem (ex.: bash, python)"))
        row.addWidget(self.language, 1)
        lay.addLayout(row)

        self.tags = QLineEdit((data or {}).get("tags", ""))
        self.tags.setPlaceholderText(_t("Tags separadas por vírgula"))
        lay.addWidget(self.tags)

        self.content = QPlainTextEdit((data or {}).get("content", ""))
        self.content.setPlaceholderText(_t("Conteúdo..."))
        self.content.setMinimumHeight(180)
        lay.addWidget(self.content, 1)

        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Save).setText(_t("Salvar"))
        bb.button(QDialogButtonBox.Cancel).setText(_t("Cancelar"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def data(self):
        return {
            "title": self.title.text().strip(),
            "kind": self.kind.currentData(),
            "language": self.language.text().strip(),
            "tags": self.tags.text().strip(),
            "content": self.content.toPlainText(),
        }


class RunbookDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle(_t("Runbook / Comando"))
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)

        self.title = QLineEdit((data or {}).get("title", ""))
        self.title.setPlaceholderText(_t("Título"))
        lay.addWidget(self.title)

        self.category = QLineEdit((data or {}).get("category", ""))
        self.category.setPlaceholderText(_t("Categoria (ex.: setup, deploy)"))
        lay.addWidget(self.category)

        self.command = QPlainTextEdit((data or {}).get("command", ""))
        self.command.setPlaceholderText(_t("Comando(s)..."))
        self.command.setMinimumHeight(90)
        lay.addWidget(self.command)

        self.description = QPlainTextEdit((data or {}).get("description", ""))
        self.description.setPlaceholderText(_t("Descrição (opcional)"))
        self.description.setMinimumHeight(70)
        lay.addWidget(self.description)

        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Save).setText(_t("Salvar"))
        bb.button(QDialogButtonBox.Cancel).setText(_t("Cancelar"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def data(self):
        return {
            "title": self.title.text().strip(),
            "category": self.category.text().strip(),
            "command": self.command.toPlainText(),
            "description": self.description.toPlainText(),
        }


# ---------------------------------------------------------------------------
# View principal (abas)
# ---------------------------------------------------------------------------
class LibraryView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(_t("Biblioteca"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel(_t("Snippets, prompts, comandos e importação de TODO/FIXME"))
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_snippets_tab(), _t("Snippets & Prompts"))
        self.tabs.addTab(self._build_runbooks_tab(), _t("Runbooks"))
        self.tabs.addTab(self._build_import_tab(), _t("Importar do código"))
        self.tabs.addTab(self._build_triage_tab(), _t("Triagem de bugs"))
        self.tabs.addTab(self._build_review_tab(), _t("Code review"))
        self.tabs.addTab(self._build_git_tab(), _t("Git"))
        self.tabs.addTab(self._build_time_tab(), _t("Tempo"))
        layout.addWidget(self.tabs, 1)

        self.refresh()

    def refresh(self):
        self._reload_snippets()
        self._reload_runbooks()
        self._reload_projects()

    # ---- Snippets tab ----
    def _build_snippets_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)

        top = QHBoxLayout()
        self.snip_search = QLineEdit()
        self.snip_search.setPlaceholderText(_t("Buscar..."))
        self.snip_search.textChanged.connect(self._reload_snippets)
        top.addWidget(self.snip_search, 1)
        self.snip_filter = QComboBox()
        self.snip_filter.addItem(_t("Todos"), "")
        self.snip_filter.addItem(_t("Snippet"), "SNIPPET")
        self.snip_filter.addItem(_t("Prompt"), "PROMPT")
        self.snip_filter.currentIndexChanged.connect(self._reload_snippets)
        top.addWidget(self.snip_filter)
        add = QPushButton(_t("+ Novo"))
        add.setCursor(Qt.PointingHandCursor)
        add.clicked.connect(self._add_snippet)
        top.addWidget(add)
        lay.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self.snip_container = QWidget()
        self.snip_layout = QVBoxLayout(self.snip_container)
        self.snip_layout.setSpacing(6)
        self.snip_layout.setContentsMargins(0, 0, 0, 0)
        self.snip_layout.addStretch()
        scroll.setWidget(self.snip_container)
        lay.addWidget(scroll, 1)
        return w

    def _reload_snippets(self):
        while self.snip_layout.count() > 1:
            item = self.snip_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        q = self.snip_search.text().lower().strip()
        kind = self.snip_filter.currentData()
        s = get_session()
        try:
            query = s.query(Snippet)
            if kind:
                query = query.filter(Snippet.kind == kind)
            rows = query.order_by(Snippet.updated_at.desc()).all()
            for r in rows:
                hay = f"{r.title} {r.content} {r.tags} {r.language}".lower()
                if q and q not in hay:
                    continue
                self.snip_layout.insertWidget(
                    self.snip_layout.count() - 1, self._snippet_card(r))
        finally:
            s.close()

    def _snippet_card(self, r):
        t = current_theme()
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {t.bg_card}; border: 1px solid {t.border}; "
            f"border-radius: 8px; padding: 8px; }}")
        cl = QVBoxLayout(card)
        cl.setSpacing(4)
        head = QHBoxLayout()
        badge = "🧩" if r.kind == "SNIPPET" else "💬"
        lbl = QLabel(f"{badge} {r.title}")
        lbl.setStyleSheet("font-weight: 600;")
        head.addWidget(lbl, 1)
        meta = " · ".join(x for x in [r.language, r.tags] if x)
        if meta:
            m = QLabel(meta)
            m.setObjectName("subtitle")
            head.addWidget(m)
        cl.addLayout(head)

        preview = (r.content or "").strip().splitlines()
        prev = QLabel(preview[0][:80] + ("…" if preview and len(preview[0]) > 80 else "")
                      if preview else "")
        prev.setObjectName("subtitle")
        cl.addWidget(prev)

        btns = QHBoxLayout()
        btns.addStretch()
        copy = QPushButton(_t("Copiar"))
        copy.setCursor(Qt.PointingHandCursor)
        copy.clicked.connect(lambda _, rid=r.id, c=r.content: self._copy_snippet(rid, c))
        edit = QPushButton("✎")
        edit.setFixedWidth(30)
        edit.setCursor(Qt.PointingHandCursor)
        edit.clicked.connect(lambda _, rid=r.id: self._edit_snippet(rid))
        dele = QPushButton("✕")
        dele.setFixedWidth(30)
        dele.setCursor(Qt.PointingHandCursor)
        dele.clicked.connect(lambda _, rid=r.id: self._delete_snippet(rid))
        for b in (copy, edit, dele):
            btns.addWidget(b)
        cl.addLayout(btns)
        return card

    def _copy_snippet(self, rid, content):
        _clip(content)
        s = get_session()
        try:
            row = s.get(Snippet, rid)
            if row:
                row.use_count = (row.use_count or 0) + 1
                s.commit()
        finally:
            s.close()

    def _add_snippet(self):
        dlg = SnippetDialog(self)
        if dlg.exec() == QDialog.Accepted:
            d = dlg.data()
            if not d["title"]:
                return
            s = get_session()
            try:
                s.add(Snippet(title=d["title"], content=d["content"], kind=d["kind"],
                              language=d["language"], tags=d["tags"]))
                s.commit()
            finally:
                s.close()
            self._reload_snippets()

    def _edit_snippet(self, rid):
        s = get_session()
        try:
            row = s.get(Snippet, rid)
            if not row:
                return
            data = {"title": row.title, "content": row.content, "kind": row.kind,
                    "language": row.language, "tags": row.tags}
        finally:
            s.close()
        dlg = SnippetDialog(self, data)
        if dlg.exec() == QDialog.Accepted:
            d = dlg.data()
            if not d["title"]:
                return
            s = get_session()
            try:
                row = s.get(Snippet, rid)
                row.title, row.content = d["title"], d["content"]
                row.kind, row.language, row.tags = d["kind"], d["language"], d["tags"]
                s.commit()
            finally:
                s.close()
            self._reload_snippets()

    def _delete_snippet(self, rid):
        if QMessageBox.question(self, _t("Excluir"), _t("Excluir este item?")) != QMessageBox.Yes:
            return
        s = get_session()
        try:
            row = s.get(Snippet, rid)
            if row:
                s.delete(row)
                s.commit()
        finally:
            s.close()
        self._reload_snippets()

    # ---- Runbooks tab ----
    def _build_runbooks_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)

        top = QHBoxLayout()
        self.rb_search = QLineEdit()
        self.rb_search.setPlaceholderText(_t("Buscar..."))
        self.rb_search.textChanged.connect(self._reload_runbooks)
        top.addWidget(self.rb_search, 1)
        add = QPushButton(_t("+ Novo"))
        add.setCursor(Qt.PointingHandCursor)
        add.clicked.connect(self._add_runbook)
        top.addWidget(add)
        lay.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self.rb_container = QWidget()
        self.rb_layout = QVBoxLayout(self.rb_container)
        self.rb_layout.setSpacing(6)
        self.rb_layout.setContentsMargins(0, 0, 0, 0)
        self.rb_layout.addStretch()
        scroll.setWidget(self.rb_container)
        lay.addWidget(scroll, 1)
        return w

    def _reload_runbooks(self):
        while self.rb_layout.count() > 1:
            item = self.rb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        q = self.rb_search.text().lower().strip()
        s = get_session()
        try:
            rows = s.query(Runbook).order_by(
                Runbook.sort_order.asc(), Runbook.updated_at.desc()).all()
            for r in rows:
                hay = f"{r.title} {r.command} {r.description} {r.category}".lower()
                if q and q not in hay:
                    continue
                self.rb_layout.insertWidget(
                    self.rb_layout.count() - 1, self._runbook_card(r))
        finally:
            s.close()

    def _runbook_card(self, r):
        t = current_theme()
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {t.bg_card}; border: 1px solid {t.border}; "
            f"border-radius: 8px; padding: 8px; }}")
        cl = QVBoxLayout(card)
        cl.setSpacing(4)
        head = QHBoxLayout()
        lbl = QLabel(f"⚙️ {r.title}")
        lbl.setStyleSheet("font-weight: 600;")
        head.addWidget(lbl, 1)
        if r.category:
            m = QLabel(r.category)
            m.setObjectName("subtitle")
            head.addWidget(m)
        cl.addLayout(head)
        cmd = QLabel(f"<code>{(r.command or '').strip()[:120]}</code>")
        cmd.setObjectName("subtitle")
        cmd.setWordWrap(True)
        cl.addWidget(cmd)

        btns = QHBoxLayout()
        btns.addStretch()
        copy = QPushButton(_t("Copiar comando"))
        copy.setCursor(Qt.PointingHandCursor)
        copy.clicked.connect(lambda _, rid=r.id, c=r.command: self._copy_runbook(rid, c))
        edit = QPushButton("✎")
        edit.setFixedWidth(30)
        edit.setCursor(Qt.PointingHandCursor)
        edit.clicked.connect(lambda _, rid=r.id: self._edit_runbook(rid))
        dele = QPushButton("✕")
        dele.setFixedWidth(30)
        dele.setCursor(Qt.PointingHandCursor)
        dele.clicked.connect(lambda _, rid=r.id: self._delete_runbook(rid))
        for b in (copy, edit, dele):
            btns.addWidget(b)
        cl.addLayout(btns)
        return card

    def _copy_runbook(self, rid, cmd):
        _clip(cmd)
        s = get_session()
        try:
            row = s.get(Runbook, rid)
            if row:
                row.use_count = (row.use_count or 0) + 1
                s.commit()
        finally:
            s.close()

    def _add_runbook(self):
        dlg = RunbookDialog(self)
        if dlg.exec() == QDialog.Accepted:
            d = dlg.data()
            if not d["title"]:
                return
            s = get_session()
            try:
                s.add(Runbook(title=d["title"], command=d["command"],
                              description=d["description"], category=d["category"]))
                s.commit()
            finally:
                s.close()
            self._reload_runbooks()

    def _edit_runbook(self, rid):
        s = get_session()
        try:
            row = s.get(Runbook, rid)
            if not row:
                return
            data = {"title": row.title, "command": row.command,
                    "description": row.description, "category": row.category}
        finally:
            s.close()
        dlg = RunbookDialog(self, data)
        if dlg.exec() == QDialog.Accepted:
            d = dlg.data()
            if not d["title"]:
                return
            s = get_session()
            try:
                row = s.get(Runbook, rid)
                row.title, row.command = d["title"], d["command"]
                row.description, row.category = d["description"], d["category"]
                s.commit()
            finally:
                s.close()
            self._reload_runbooks()

    def _delete_runbook(self, rid):
        if QMessageBox.question(self, _t("Excluir"), _t("Excluir este item?")) != QMessageBox.Yes:
            return
        s = get_session()
        try:
            row = s.get(Runbook, rid)
            if row:
                s.delete(row)
                s.commit()
        finally:
            s.close()
        self._reload_runbooks()

    # ---- Import tab ----
    def _build_import_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(8)

        info = QLabel(_t("Varre uma pasta por TODO/FIXME/HACK/XXX e cria tarefas no projeto escolhido."))
        info.setObjectName("subtitle")
        info.setWordWrap(True)
        lay.addWidget(info)

        row = QHBoxLayout()
        self.imp_path = QLineEdit()
        self.imp_path.setPlaceholderText(_t("Pasta do repositório..."))
        row.addWidget(self.imp_path, 1)
        pick = QPushButton(_t("Escolher..."))
        pick.setCursor(Qt.PointingHandCursor)
        pick.clicked.connect(self._pick_folder)
        row.addWidget(pick)
        scan = QPushButton(_t("Varrer"))
        scan.setCursor(Qt.PointingHandCursor)
        scan.clicked.connect(self._scan)
        row.addWidget(scan)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel(_t("Projeto:")))
        self.imp_project = QComboBox()
        row2.addWidget(self.imp_project, 1)
        self.imp_btn = QPushButton(_t("Importar selecionados"))
        self.imp_btn.setCursor(Qt.PointingHandCursor)
        self.imp_btn.clicked.connect(self._import)
        row2.addWidget(self.imp_btn)
        lay.addLayout(row2)

        self.imp_list = QListWidget()
        self.imp_list.setSelectionMode(QListWidget.MultiSelection)
        lay.addWidget(self.imp_list, 1)

        self.imp_status = QLabel("")
        self.imp_status.setObjectName("subtitle")
        lay.addWidget(self.imp_status)
        return w

    def _reload_projects(self):
        s = get_session()
        try:
            projects = s.query(Project).order_by(Project.name).all()
            combos = [self.imp_project]
            if hasattr(self, "tri_project"):
                combos.append(self.tri_project)
            for combo in combos:
                combo.clear()
                for p in projects:
                    combo.addItem(f"{p.key} — {p.name}", p.id)
        finally:
            s.close()

    def _pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, _t("Escolher pasta"))
        if d:
            self.imp_path.setText(d)

    def _scan(self):
        from maestro_local.api.app import _scan_code_markers
        path = self.imp_path.text().strip()
        if not path:
            return
        self.imp_list.clear()
        try:
            items = _scan_code_markers(path, ["TODO", "FIXME", "HACK", "XXX"], 500)
        except Exception as e:  # noqa: BLE001
            self.imp_status.setText(_t("Erro ao varrer") + f": {e}")
            return
        for it in items:
            label = f"[{it['marker']}] {it['file']}:{it['line']} — {it['text']}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, it)
            item.setSelected(True)
            self.imp_list.addItem(item)
        self.imp_status.setText(_t("Encontrados") + f": {len(items)}")

    def _import(self):
        pid = self.imp_project.currentData()
        if not pid:
            self.imp_status.setText(_t("Selecione um projeto"))
            return
        selected = [self.imp_list.item(i).data(Qt.UserRole)
                    for i in range(self.imp_list.count())
                    if self.imp_list.item(i).isSelected()]
        if not selected:
            self.imp_status.setText(_t("Nada selecionado"))
            return
        s = get_session()
        try:
            project = s.get(Project, pid)
            column = (s.query(BoardColumn)
                      .filter(BoardColumn.project_id == project.id)
                      .order_by(BoardColumn.order.asc()).first())
            created = 0
            for it in selected:
                marker = (it.get("marker") or "TODO").upper()
                text = (it.get("text") or "").strip() or "(sem descrição)"
                project.task_seq = (project.task_seq or 0) + 1
                s.add(Task(
                    project_id=project.id,
                    column_id=column.id if column else None,
                    number=project.task_seq,
                    title=f"[{marker}] {text}"[:255],
                    description=f"Importado de `{it.get('file', '')}:{it.get('line', '')}`",
                    type="BUG" if marker == "FIXME" else "CHORE",
                ))
                created += 1
            s.commit()
        finally:
            s.close()
        self.imp_status.setText(_t("Tarefas criadas") + f": {created}")
        self.imp_list.clear()

    # ---- Triage tab ----
    def _build_triage_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(8)

        info = QLabel(_t("Cole um stacktrace/relato. A IA classifica e você cria uma tarefa BUG."))
        info.setObjectName("subtitle")
        info.setWordWrap(True)
        lay.addWidget(info)

        self.tri_input = QPlainTextEdit()
        self.tri_input.setPlaceholderText(_t("Cole aqui o stacktrace ou a descrição do problema..."))
        self.tri_input.setMinimumHeight(120)
        lay.addWidget(self.tri_input)

        row = QHBoxLayout()
        tri_btn = QPushButton(_t("Triar com IA"))
        tri_btn.setCursor(Qt.PointingHandCursor)
        tri_btn.clicked.connect(self._run_triage)
        row.addWidget(tri_btn)
        row.addStretch()
        lay.addLayout(row)

        self.tri_result = QLabel("")
        self.tri_result.setWordWrap(True)
        self.tri_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.tri_result)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel(_t("Projeto:")))
        self.tri_project = QComboBox()
        row2.addWidget(self.tri_project, 1)
        self.tri_create = QPushButton(_t("Criar tarefa BUG"))
        self.tri_create.setCursor(Qt.PointingHandCursor)
        self.tri_create.setEnabled(False)
        self.tri_create.clicked.connect(self._create_bug_task)
        row2.addWidget(self.tri_create)
        lay.addLayout(row2)

        self.tri_status = QLabel("")
        self.tri_status.setObjectName("subtitle")
        lay.addWidget(self.tri_status)
        lay.addStretch()
        self._last_triage = None
        return w

    def _run_triage(self):
        from maestro_local.triage import triage_bug
        text = self.tri_input.toPlainText().strip()
        if not text:
            return
        self.tri_status.setText(_t("Triando..."))
        self.tri_result.setText("")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            triage = triage_bug(text)
        except Exception as e:  # noqa: BLE001
            self.tri_status.setText(_t("Erro na triagem") + f": {e}")
            self._last_triage = None
            self.tri_create.setEnabled(False)
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._last_triage = triage
        steps = "".join(f"<li>{s}</li>" for s in triage.get("steps", []))
        self.tri_result.setText(
            f"<b>{triage['title']}</b><br>"
            f"<b>{_t('Severidade')}:</b> {triage['severity']} · "
            f"<b>{_t('Prioridade')}:</b> {triage['priority']}<br>"
            f"<b>{_t('Resumo')}:</b> {triage.get('summary', '')}<br>"
            + (f"<b>{_t('Causa provável')}:</b> {triage['probable_cause']}<br>" if triage.get("probable_cause") else "")
            + (f"<b>{_t('Passos')}:</b><ul>{steps}</ul>" if steps else "")
        )
        self.tri_status.setText("")
        self.tri_create.setEnabled(True)

    # ---- Code review tab ----
    def _build_review_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(8)

        info = QLabel(_t("Aponte um repositório e uma base (branch/ref). A IA revisa o diff."))
        info.setObjectName("subtitle")
        info.setWordWrap(True)
        lay.addWidget(info)

        row = QHBoxLayout()
        self.rev_path = QLineEdit()
        self.rev_path.setPlaceholderText(_t("Pasta do repositório..."))
        row.addWidget(self.rev_path, 1)
        pick = QPushButton(_t("Escolher..."))
        pick.setCursor(Qt.PointingHandCursor)
        pick.clicked.connect(lambda: self.rev_path.setText(
            QFileDialog.getExistingDirectory(self, _t("Escolher pasta")) or self.rev_path.text()))
        row.addWidget(pick)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        self.rev_base = QLineEdit()
        self.rev_base.setPlaceholderText(_t("Base (ex.: main, HEAD~1) — vazio = alterações locais"))
        row2.addWidget(self.rev_base, 1)
        self.rev_task = QLineEdit()
        self.rev_task.setPlaceholderText(_t("Tarefa (ex.: PROJ-1)"))
        self.rev_task.setFixedWidth(140)
        row2.addWidget(self.rev_task)
        lay.addLayout(row2)

        row3 = QHBoxLayout()
        rev_btn = QPushButton(_t("Revisar com IA"))
        rev_btn.setCursor(Qt.PointingHandCursor)
        rev_btn.clicked.connect(lambda: self._run_review(post=False))
        row3.addWidget(rev_btn)
        rev_post = QPushButton(_t("Revisar e comentar na tarefa"))
        rev_post.setCursor(Qt.PointingHandCursor)
        rev_post.clicked.connect(lambda: self._run_review(post=True))
        row3.addWidget(rev_post)
        row3.addStretch()
        self.rev_status = QLabel("")
        self.rev_status.setObjectName("subtitle")
        row3.addWidget(self.rev_status)
        lay.addLayout(row3)

        self.rev_result = QPlainTextEdit()
        self.rev_result.setReadOnly(True)
        lay.addWidget(self.rev_result, 1)
        return w

    def _run_review(self, post=False):
        from maestro_local.codereview import get_git_diff, review_diff, review_to_markdown
        path = self.rev_path.text().strip()
        if not path:
            self.rev_status.setText(_t("Informe o caminho do repositório"))
            return
        self.rev_status.setText(_t("Revisando..."))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            diff = get_git_diff(path, self.rev_base.text().strip())
            review = review_diff(diff)
        except Exception as e:  # noqa: BLE001
            self.rev_status.setText(_t("Erro") + f": {e}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        lines = []
        if review.get("summary"):
            lines.append(review["summary"] + "\n")
        if review.get("issues"):
            lines.append(_t("Problemas") + ":")
            for it in review["issues"]:
                loc = f" {it['file']}" if it.get("file") else ""
                lines.append(f"  [{it['severity']}]{loc} — {it['note']}")
        if review.get("suggestions"):
            lines.append("\n" + _t("Sugestões") + ":")
            lines += [f"  - {sug}" for sug in review["suggestions"]]
        if review.get("truncated"):
            lines.append("\n" + _t("(diff truncado para revisão)"))
        self.rev_result.setPlainText("\n".join(lines))
        self.rev_status.setText("")

        if post:
            code = self.rev_task.text().strip()
            if not code:
                self.rev_status.setText(_t("Informe a tarefa"))
                return
            s = get_session()
            try:
                from maestro_local.api.app import _resolve_task
                task = _resolve_task(code, s)
                s.add(Comment(task_id=task.id, body=review_to_markdown(review), type="CODE_REVIEW"))
                s.commit()
                self.rev_status.setText(_t("Comentário postado na tarefa"))
            except Exception as e:  # noqa: BLE001
                self.rev_status.setText(_t("Erro") + f": {e}")
            finally:
                s.close()

    # ---- Git cockpit tab ----
    def _build_git_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(8)

        info = QLabel(_t("Estado do repositório: branch, mudanças, commits e PRs (via gh)."))
        info.setObjectName("subtitle")
        info.setWordWrap(True)
        lay.addWidget(info)

        row = QHBoxLayout()
        self.git_path = QLineEdit()
        self.git_path.setPlaceholderText(_t("Pasta do repositório..."))
        row.addWidget(self.git_path, 1)
        pick = QPushButton(_t("Escolher..."))
        pick.setCursor(Qt.PointingHandCursor)
        pick.clicked.connect(lambda: self.git_path.setText(
            QFileDialog.getExistingDirectory(self, _t("Escolher pasta")) or self.git_path.text()))
        row.addWidget(pick)
        refresh = QPushButton(_t("Atualizar"))
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.clicked.connect(self._load_git)
        row.addWidget(refresh)
        lay.addLayout(row)

        self.git_status_lbl = QLabel("")
        self.git_status_lbl.setObjectName("subtitle")
        lay.addWidget(self.git_status_lbl)

        self.git_result = QPlainTextEdit()
        self.git_result.setReadOnly(True)
        lay.addWidget(self.git_result, 1)
        return w

    def _load_git(self):
        from maestro_local.gittools import git_status, gh_prs
        path = self.git_path.text().strip()
        if not path:
            self.git_status_lbl.setText(_t("Informe o caminho do repositório"))
            return
        try:
            st = git_status(path)
        except Exception as e:  # noqa: BLE001
            self.git_status_lbl.setText(_t("Erro") + f": {e}")
            self.git_result.clear()
            return
        prs = gh_prs(path)
        self.git_status_lbl.setText(
            f"🌿 {st['branch']}  ↑{st['ahead']} ↓{st['behind']}  "
            + (_t("Limpo") if st["clean"] else _t("Com alterações")))
        lines = []
        if st["staged"]:
            lines.append(_t("Staged") + ":")
            lines += [f"  {x}" for x in st["staged"]]
        if st["unstaged"]:
            lines.append(_t("Não-staged") + ":")
            lines += [f"  {x}" for x in st["unstaged"]]
        if st["untracked"]:
            lines.append(_t("Não rastreados") + ":")
            lines += [f"  {x}" for x in st["untracked"]]
        if prs:
            lines.append("\n" + _t("Pull requests") + ":")
            lines += [f"  #{p['number']} {p['title']} ({p['branch']})" for p in prs]
        lines.append("\n" + _t("Commits recentes") + ":")
        lines += [f"  {c['hash']} {c['subject']} — {c['author']}, {c['when']}"
                  for c in st["commits"]]
        self.git_result.setPlainText("\n".join(lines))

    # ---- Time tracking tab ----
    def _build_time_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(8)

        info = QLabel(_t("Cronômetro e registro de tempo por tarefa. Total da semana e por tarefa."))
        info.setObjectName("subtitle")
        info.setWordWrap(True)
        lay.addWidget(info)

        top = QHBoxLayout()
        self.time_task = QLineEdit()
        self.time_task.setPlaceholderText(_t("Tarefa (ex.: PROJ-1)"))
        self.time_task.setFixedWidth(140)
        top.addWidget(self.time_task)
        self.time_note = QLineEdit()
        self.time_note.setPlaceholderText(_t("Nota (opcional)"))
        top.addWidget(self.time_note, 1)
        lay.addLayout(top)

        ctrl = QHBoxLayout()
        self.time_display = QLabel("0m00s")
        self.time_display.setStyleSheet("font-size: 22px; font-family: monospace;")
        ctrl.addWidget(self.time_display)
        self.time_btn = QPushButton(_t("Iniciar"))
        self.time_btn.setCursor(Qt.PointingHandCursor)
        self.time_btn.clicked.connect(self._toggle_timer)
        ctrl.addWidget(self.time_btn)
        ctrl.addWidget(QLabel("|"))
        self.time_minutes = QLineEdit()
        self.time_minutes.setPlaceholderText(_t("min"))
        self.time_minutes.setFixedWidth(60)
        ctrl.addWidget(self.time_minutes)
        manual = QPushButton(_t("Registrar manual"))
        manual.setCursor(Qt.PointingHandCursor)
        manual.clicked.connect(self._log_manual)
        ctrl.addWidget(manual)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self.time_week = QLabel("")
        self.time_week.setStyleSheet("font-weight: 600;")
        lay.addWidget(self.time_week)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self.time_container = QWidget()
        self.time_layout = QVBoxLayout(self.time_container)
        self.time_layout.setSpacing(4)
        self.time_layout.addStretch()
        scroll.setWidget(self.time_container)
        lay.addWidget(scroll, 1)

        self._timer_seconds = 0
        self._timer_running = False
        self._qtimer = QTimer(self)
        self._qtimer.setInterval(1000)
        self._qtimer.timeout.connect(self._tick)
        self._reload_time()
        return w

    @staticmethod
    def _fmt_dur(sec):
        h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
        return f"{h}h{m:02d}" if h else f"{m}m{s:02d}s"

    def _tick(self):
        self._timer_seconds += 1
        self.time_display.setText(self._fmt_dur(self._timer_seconds))

    def _toggle_timer(self):
        if self._timer_running:
            self._qtimer.stop()
            self._timer_running = False
            self.time_btn.setText(_t("Iniciar"))
            if self._timer_seconds > 0:
                self._save_time(self._timer_seconds)
            self._timer_seconds = 0
            self.time_display.setText("0m00s")
        else:
            self._timer_running = True
            self.time_btn.setText(_t("Parar e registrar"))
            self._qtimer.start()

    def _log_manual(self):
        try:
            mins = int(self.time_minutes.text().strip())
        except ValueError:
            return
        if mins <= 0:
            return
        self._save_time(mins * 60)
        self.time_minutes.clear()

    def _save_time(self, seconds):
        from datetime import datetime as _dt
        code = self.time_task.text().strip()
        task_id = None
        s = get_session()
        try:
            if code:
                from maestro_local.api.app import _resolve_task
                try:
                    task = _resolve_task(code, s)
                    task_id = task.id
                    code = f"{task.project.key}-{task.number}"
                except Exception:  # noqa: BLE001
                    pass
            s.add(TimeLog(task_id=task_id, task_code=code, seconds=seconds,
                          note=self.time_note.text().strip(), started_at=_dt.now()))
            s.commit()
        finally:
            s.close()
        self._reload_time()

    def _reload_time(self):
        from datetime import datetime as _dt, timedelta
        while self.time_layout.count() > 1:
            item = self.time_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        s = get_session()
        try:
            week_start = _dt.now() - timedelta(days=7)
            week = s.query(TimeLog).filter(TimeLog.created_at >= week_start).all()
            total = sum(t.seconds or 0 for t in week)
            by_task = {}
            for t in week:
                k = t.task_code or "—"
                by_task[k] = by_task.get(k, 0) + (t.seconds or 0)
            parts = ", ".join(f"{k}: {self._fmt_dur(v)}" for k, v in
                              sorted(by_task.items(), key=lambda kv: -kv[1]))
            self.time_week.setText(_t("Esta semana") + f": {self._fmt_dur(total)}"
                                   + (f"  ({parts})" if parts else ""))
            logs = s.query(TimeLog).order_by(TimeLog.created_at.desc()).limit(50).all()
            for l in logs:
                self.time_layout.insertWidget(self.time_layout.count() - 1, self._time_row(l))
        finally:
            s.close()

    def _time_row(self, l):
        row = QFrame()
        h = QHBoxLayout(row)
        h.setContentsMargins(2, 2, 2, 2)
        txt = self._fmt_dur(l.seconds or 0)
        if l.task_code:
            txt += f" · {l.task_code}"
        if l.note:
            txt += f" — {l.note}"
        lbl = QLabel(txt)
        h.addWidget(lbl, 1)
        dele = QPushButton("✕")
        dele.setFixedWidth(28)
        dele.setCursor(Qt.PointingHandCursor)
        dele.clicked.connect(lambda _, lid=l.id: self._delete_time(lid))
        h.addWidget(dele)
        return row

    def _delete_time(self, lid):
        s = get_session()
        try:
            row = s.get(TimeLog, lid)
            if row:
                s.delete(row)
                s.commit()
        finally:
            s.close()
        self._reload_time()

    def _create_bug_task(self):
        from maestro_local.triage import build_task_description
        if not self._last_triage:
            return
        pid = self.tri_project.currentData()
        if not pid:
            self.tri_status.setText(_t("Selecione um projeto"))
            return
        text = self.tri_input.toPlainText().strip()
        triage = self._last_triage
        s = get_session()
        try:
            project = s.get(Project, pid)
            column = (s.query(BoardColumn)
                      .filter(BoardColumn.project_id == project.id)
                      .order_by(BoardColumn.order.asc()).first())
            project.task_seq = (project.task_seq or 0) + 1
            number = project.task_seq
            s.add(Task(
                project_id=project.id,
                column_id=column.id if column else None,
                number=number,
                title=triage["title"],
                description=build_task_description(text, triage),
                type="BUG",
                priority=triage["priority"],
                requires_human=True,
            ))
            s.commit()
            code = f"{project.key}-{number}"
        finally:
            s.close()
        self.tri_status.setText(_t("Tarefa criada") + f": {code}")
        self.tri_create.setEnabled(False)
