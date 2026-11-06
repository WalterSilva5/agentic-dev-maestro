"""Ficha simplificada do card.

Um card é só: título, texto, responsável, data alvo, coluna, sprint, épicos,
tags, vínculos com outros cards e comentários. Sem anexos, checklist,
subtarefas ou estimativas.
"""
from datetime import datetime

from PySide6.QtCore import QDate, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from maestro_local.db.models import (
    ActivityLog,
    BoardColumn,
    Comment,
    Epic,
    Label,
    Sprint,
    Task,
    TaskDependency,
    get_or_create_member,
    get_session,
    project_members,
)
from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t as _t


def _divisor(theme):
    linha = QFrame()
    linha.setFrameShape(QFrame.HLine)
    linha.setFixedHeight(1)
    linha.setStyleSheet(f"background: {theme.border_light}; border: none;")
    return linha


class TaskDetailDialog(QDialog):
    task_updated = Signal()

    def __init__(self, task_id: int, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.setWindowTitle(_t("Card"))
        self.resize(680, 720)
        self.setMinimumSize(520, 480)
        t = current_theme()

        self._desc_timer = QTimer(self)
        self._desc_timer.setSingleShot(True)
        self._desc_timer.setInterval(600)
        self._desc_timer.timeout.connect(self._salvar_descricao)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(20, 18, 20, 16)
        raiz.setSpacing(10)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        corpo = QWidget()
        lay = QVBoxLayout(corpo)
        lay.setContentsMargins(2, 2, 8, 2)
        lay.setSpacing(10)

        s = get_session()
        try:
            task = s.get(Task, task_id)
            if task is None:
                lay.addWidget(QLabel(_t("Card não encontrado")))
                self._scroll.setWidget(corpo)
                raiz.addWidget(self._scroll, 1)
                return
            projeto_id = task.project_id
            codigo = task.code

            # Linha 1: código + título
            cab = QHBoxLayout()
            cod = QLabel(codigo)
            cod.setStyleSheet(
                f"font-family: 'Fira Code', monospace; font-size: 14px; color: {t.text_muted};")
            cab.addWidget(cod)
            self.title_edit = QLineEdit(task.title)
            self.title_edit.setStyleSheet("font-size: 18px; font-weight: 700;")
            self.title_edit.editingFinished.connect(
                lambda: self._save_field("title", self.title_edit.text().strip()))
            cab.addWidget(self.title_edit, 1)
            lay.addLayout(cab)

            # Linha 2: coluna + sprint
            lin = QHBoxLayout()
            lin.setSpacing(10)
            lin.addWidget(QLabel(_t("Coluna:")))
            self.col_combo = QComboBox()
            for c in (s.query(BoardColumn)
                      .filter(BoardColumn.project_id == projeto_id)
                      .order_by(BoardColumn.order).all()):
                self.col_combo.addItem(c.name, c.id)
            idx = self.col_combo.findData(task.column_id)
            if idx >= 0:
                self.col_combo.setCurrentIndex(idx)
            self.col_combo.currentIndexChanged.connect(
                lambda: self._move(self.col_combo.currentData()))
            lin.addWidget(self.col_combo, 1)

            lin.addWidget(QLabel(_t("Sprint:")))
            self.sprint_combo = QComboBox()
            self.sprint_combo.addItem(_t("Backlog"), None)
            self.sprint_combo.addItem(_t("+ Nova sprint..."), "__nova__")
            for sp in (s.query(Sprint)
                       .filter(Sprint.project_id == projeto_id)
                       .order_by(Sprint.sort_order, Sprint.id).all()):
                self.sprint_combo.addItem(sp.name, sp.id)
            sidx = self.sprint_combo.findData(task.sprint_id) if task.sprint_id is not None else 0
            self.sprint_combo.setCurrentIndex(sidx if sidx >= 0 else 0)
            self.sprint_combo.currentIndexChanged.connect(self._trocar_sprint)
            lin.addWidget(self.sprint_combo, 1)
            lay.addLayout(lin)

            # Linha 3: responsável + data alvo
            lin2 = QHBoxLayout()
            lin2.setSpacing(10)
            lin2.addWidget(QLabel(_t("Responsável:")))
            self.assignee_combo = QComboBox()
            self.assignee_combo.setEditable(True)
            self.assignee_combo.addItem("", None)
            nomes = {
                td.assignee for td in s.query(Task).filter(
                    Task.project_id == projeto_id,
                    Task.assignee.isnot(None),
                    Task.deleted_at == None,  # noqa: E711
                ).all() if td.assignee
            }
            # A lista de responsáveis do projeto vem primeiro (fonte oficial);
            # nomes legados digitados à mão completam sem se perder.
            for n in sorted({m.name for m in project_members(s, projeto_id)} | nomes):
                self.assignee_combo.addItem(n, n)
            if task.assignee:
                ai = self.assignee_combo.findData(task.assignee)
                self.assignee_combo.setCurrentIndex(ai if ai >= 0 else 0)
                if ai < 0:
                    self.assignee_combo.setEditText(task.assignee)
            self.assignee_combo.currentTextChanged.connect(self._trocar_responsavel)
            lin2.addWidget(self.assignee_combo, 1)

            lin2.addWidget(QLabel(_t("Data alvo:")))
            self.due_edit = QDateEdit()
            self.due_edit.setCalendarPopup(True)
            self.due_edit.setDisplayFormat("dd/MM/yyyy")
            self.due_edit.setSpecialValueText(_t("Sem data"))
            if task.due_date:
                self.due_edit.setDate(QDate(task.due_date.year, task.due_date.month, task.due_date.day))
            else:
                self.due_edit.setDate(self.due_edit.minimumDate())
            self.due_edit.dateChanged.connect(self._save_due_date)
            lin2.addWidget(self.due_edit)
            lay.addLayout(lin2)

            lay.addWidget(_divisor(t))

            # Épicos
            self._epicos_box = QWidget()
            self._epicos_layout = QVBoxLayout(self._epicos_box)
            self._epicos_layout.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(self._epicos_box)
            self._rebuild_epicos()

            # Tags
            self._tags_box = QWidget()
            self._tags_layout = QVBoxLayout(self._tags_box)
            self._tags_layout.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(self._tags_box)
            self._rebuild_tags()

            lay.addWidget(_divisor(t))

            # Descrição
            rotulo_desc = QLabel(_t("Texto:"))
            rotulo_desc.setProperty("class", "sectionLabel")
            lay.addWidget(rotulo_desc)
            self.desc_edit = QTextEdit(task.description or "")
            self.desc_edit.setMinimumHeight(120)
            self.desc_edit.textChanged.connect(lambda: self._desc_timer.start())
            lay.addWidget(self.desc_edit)

            lay.addWidget(_divisor(t))

            # Vinculados
            self._vinculos_box = QWidget()
            self._vinculos_layout = QVBoxLayout(self._vinculos_box)
            self._vinculos_layout.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(self._vinculos_box)
            self._rebuild_vinculos()

            lay.addWidget(_divisor(t))

            # Comentários
            self._comentarios_box = QWidget()
            self._comentarios_layout = QVBoxLayout(self._comentarios_box)
            self._comentarios_layout.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(self._comentarios_box)
            self._rebuild_comentarios()

            lay.addStretch(1)
        finally:
            s.close()

        self._scroll.setWidget(corpo)
        raiz.addWidget(self._scroll, 1)

        rodape = QHBoxLayout()
        excluir = QPushButton(_t("Excluir card"))
        excluir.setStyleSheet(f"background-color: {t.danger};")
        excluir.clicked.connect(self._delete)
        rodape.addWidget(excluir)
        rodape.addStretch()
        fechar = QPushButton(_t("Fechar"))
        fechar.clicked.connect(self.accept)
        rodape.addWidget(fechar)
        raiz.addLayout(rodape)

    # ------------------------------------------------------------------
    # Persistência de campos
    # ------------------------------------------------------------------
    def _save_field(self, campo, valor):
        s = get_session()
        try:
            task = s.get(Task, self.task_id)
            if task is not None:
                setattr(task, campo, valor)
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()

    def _salvar_descricao(self):
        self._save_field("description", self.desc_edit.toPlainText())

    def _save_due_date(self, qdate):
        s = get_session()
        try:
            task = s.get(Task, self.task_id)
            if task is not None:
                if qdate == self.due_edit.minimumDate():
                    task.due_date = None
                else:
                    task.due_date = datetime(qdate.year(), qdate.month(), qdate.day())
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()

    def _trocar_responsavel(self, texto):
        """Atribui o responsável; nome novo entra na lista do projeto."""
        nome = (texto or "").strip() or None
        s = get_session()
        try:
            task = s.get(Task, self.task_id)
            if task is None:
                return
            if nome and task.project_id:
                get_or_create_member(s, task.project_id, nome)
            task.assignee = nome
            s.commit()
            self.task_updated.emit()
        finally:
            s.close()

    def _trocar_sprint(self):
        if self.sprint_combo.currentData() == "__nova__":
            nome, ok = QInputDialog.getText(self, _t("Nova sprint"), _t("Nome da sprint:"))
            nome = (nome or "").strip()
            if not ok or not nome:
                self.sprint_combo.setCurrentIndex(0)
                return
            s = get_session()
            try:
                task = s.get(Task, self.task_id)
                if task is None:
                    return
                ordem = (s.query(Sprint).filter(
                    Sprint.project_id == task.project_id).count())
                sp = Sprint(project_id=task.project_id, name=nome[:120],
                            sort_order=ordem)
                s.add(sp)
                s.commit()
                self.sprint_combo.addItem(sp.name, sp.id)
                self.sprint_combo.setCurrentIndex(
                    self.sprint_combo.findData(sp.id))
            finally:
                s.close()
            return
        self._save_field("sprint_id", self.sprint_combo.currentData())

    def _move(self, column_id):
        if column_id is None:
            return
        s = get_session()
        try:
            task = s.get(Task, self.task_id)
            if task is not None and task.column_id != column_id:
                antiga = task.column.name if task.column else "?"
                nova = s.get(BoardColumn, column_id)
                task.column_id = column_id
                s.add(ActivityLog(entity_type="task", entity_id=self.task_id,
                                  action="moved",
                                  detail=f"{antiga} -> {nova.name if nova else '?'}"))
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()

    # ------------------------------------------------------------------
    # Épicos
    # ------------------------------------------------------------------
    def _rebuild_epicos(self):
        _limpar(self._epicos_layout)
        t = current_theme()
        linha = QWidget()
        row = QHBoxLayout(linha)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        rotulo = QLabel(_t("Épicos:"))
        rotulo.setProperty("class", "sectionLabel")
        row.addWidget(rotulo)

        s = get_session()
        try:
            task = s.get(Task, self.task_id)
            aplicados = set()
            for ep in (task.epics if task else []):
                aplicados.add(ep.id)
                chip = QLabel(f" {ep.name} ✕ ")
                cor = ep.color or t.accent
                chip.setStyleSheet(
                    f"background: {cor}; color: white; border-radius: 10px; "
                    f"padding: 2px 8px; font-size: 11px;")
                chip.setCursor(Qt.PointingHandCursor)
                eid = ep.id
                chip.mousePressEvent = lambda ev, x=eid: self._remover_epico(x)
                row.addWidget(chip)

            combo = QComboBox()
            combo.addItem(_t("+ Épico..."), None)
            combo.addItem(_t("+ Novo épico..."), "__novo__")
            for ep in (s.query(Epic)
                       .filter(Epic.project_id == task.project_id)
                       .order_by(Epic.name).all()):
                if ep.id not in aplicados:
                    combo.addItem(ep.name, ep.id)
            combo.currentIndexChanged.connect(
                lambda: self._adicionar_epico(combo.currentData(), combo))
            row.addWidget(combo)
            row.addStretch()
        finally:
            s.close()
        self._epicos_layout.addWidget(linha)

    def _adicionar_epico(self, epic_id, combo):
        if epic_id == "__novo__":
            nome, ok = QInputDialog.getText(self, _t("Novo épico"), _t("Nome do épico:"))
            nome = (nome or "").strip()
            if not ok or not nome:
                combo.setCurrentIndex(0)
                return
            s = get_session()
            try:
                task = s.get(Task, self.task_id)
                ep = Epic(project_id=task.project_id if task else None, name=nome[:120])
                s.add(ep)
                s.commit()
                epic_id = ep.id
                self.task_updated.emit()
            finally:
                s.close()
            self._rebuild_epicos()
            return
        if epic_id is None:
            return
        s = get_session()
        try:
            task = s.get(Task, self.task_id)
            ep = s.get(Epic, epic_id)
            if task is not None and ep is not None and ep not in task.epics:
                task.epics.append(ep)
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()
        self._rebuild_epicos()

    def _remover_epico(self, epic_id):
        s = get_session()
        try:
            task = s.get(Task, self.task_id)
            ep = s.get(Epic, epic_id)
            if task is not None and ep is not None and ep in task.epics:
                task.epics.remove(ep)
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()
        self._rebuild_epicos()

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------
    def _rebuild_tags(self):
        _limpar(self._tags_layout)
        t = current_theme()
        linha = QWidget()
        row = QHBoxLayout(linha)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        rotulo = QLabel(_t("Tags:"))
        rotulo.setProperty("class", "sectionLabel")
        row.addWidget(rotulo)

        s = get_session()
        try:
            task = s.get(Task, self.task_id)
            aplicadas = set()
            for lbl in (task.labels if task else []):
                aplicadas.add(lbl.id)
                chip = QLabel(f" {lbl.name} ✕ ")
                cor = lbl.color or t.accent
                chip.setStyleSheet(
                    f"background: {cor}; color: white; border-radius: 10px; "
                    f"padding: 2px 8px; font-size: 11px;")
                chip.setCursor(Qt.PointingHandCursor)
                lid = lbl.id
                chip.mousePressEvent = lambda ev, x=lid: self._remover_tag(x)
                row.addWidget(chip)

            combo = QComboBox()
            combo.setEditable(True)
            combo.addItem(_t("+ Tag..."), None)
            for lbl in s.query(Label).order_by(Label.name).all():
                if lbl.id not in aplicadas:
                    combo.addItem(lbl.name, lbl.id)
            combo.currentIndexChanged.connect(
                lambda: self._adicionar_tag(combo.currentData(), combo))
            row.addWidget(combo)
            row.addStretch()
        finally:
            s.close()
        self._tags_layout.addWidget(linha)

    def _adicionar_tag(self, label_id, combo=None):
        if label_id is None and combo is not None:
            # Tag digitada que ainda não existe: cria e vincula.
            nome = (combo.currentText() or "").strip()
            if not nome or nome.startswith("+"):
                return
            s = get_session()
            try:
                existente = s.query(Label).filter(Label.name == nome).first()
                if existente is None:
                    existente = Label(name=nome[:60])
                    s.add(existente)
                    s.commit()
                label_id = existente.id
            finally:
                s.close()
        if label_id is None:
            return
        s = get_session()
        try:
            task = s.get(Task, self.task_id)
            lbl = s.get(Label, label_id)
            if task is not None and lbl is not None and lbl not in task.labels:
                task.labels.append(lbl)
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()
        self._rebuild_tags()

    def _remover_tag(self, label_id):
        s = get_session()
        try:
            task = s.get(Task, self.task_id)
            lbl = s.get(Label, label_id)
            if task is not None and lbl is not None and lbl in task.labels:
                task.labels.remove(lbl)
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()
        self._rebuild_tags()

    # ------------------------------------------------------------------
    # Vínculos com outros cards
    # ------------------------------------------------------------------
    def _rebuild_vinculos(self):
        _limpar(self._vinculos_layout)
        t = current_theme()
        rotulo = QLabel(_t("Vinculados:"))
        rotulo.setProperty("class", "sectionLabel")
        self._vinculos_layout.addWidget(rotulo)

        s = get_session()
        try:
            task = s.get(Task, self.task_id)
            if task is None:
                return
            for dep in task.blocked_by:
                alvo = dep.blocker
                linha = QWidget()
                row = QHBoxLayout(linha)
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(6)
                cod = QLabel(alvo.code)
                cod.setStyleSheet(
                    f"font-family: 'Fira Code', monospace; color: {t.text_muted};")
                row.addWidget(cod)
                row.addWidget(QLabel(alvo.title), 1)
                remover = QPushButton("✕")
                remover.setFixedSize(24, 24)
                remover.setCursor(Qt.PointingHandCursor)
                remover.setStyleSheet(
                    f"background: transparent; color: {t.text_muted}; border: none;")
                did = dep.id
                remover.clicked.connect(lambda _=False, x=did: self._remover_vinculo(x))
                row.addWidget(remover)
                self._vinculos_layout.addWidget(linha)

            add = QHBoxLayout()
            self.dep_input = QLineEdit()
            self.dep_input.setPlaceholderText(_t("Código do card (ex.: PROJ-12)"))
            self.dep_input.returnPressed.connect(self._adicionar_vinculo)
            add.addWidget(self.dep_input, 1)
            btn = QPushButton(_t("Vincular"))
            btn.setProperty("class", "secondary")
            btn.clicked.connect(self._adicionar_vinculo)
            add.addWidget(btn)
            self._vinculos_layout.addLayout(add)
        finally:
            s.close()

    def _adicionar_vinculo(self):
        codigo = self.dep_input.text().strip().upper()
        if "-" not in codigo:
            return
        prefixo, numero = codigo.rsplit("-", 1)
        if not numero.isdigit():
            return
        s = get_session()
        try:
            from maestro_local.db.models import Project
            alvo = (s.query(Task)
                    .join(Project, Task.project_id == Project.id)
                    .filter(Project.key == prefixo, Task.number == int(numero),
                            Task.deleted_at == None)  # noqa: E711
                    .first())
            if alvo is None or alvo.id == self.task_id:
                return
            existe = (s.query(TaskDependency)
                      .filter(TaskDependency.blocker_id == alvo.id,
                              TaskDependency.blocked_id == self.task_id)
                      .first())
            if existe is None:
                s.add(TaskDependency(blocker_id=alvo.id, blocked_id=self.task_id))
                s.add(ActivityLog(entity_type="task", entity_id=self.task_id,
                                  action="linked", detail=codigo))
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()
        self.dep_input.clear()
        self._rebuild_vinculos()

    def _remover_vinculo(self, dep_id):
        s = get_session()
        try:
            dep = s.get(TaskDependency, dep_id)
            if dep is not None:
                s.delete(dep)
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()
        self._rebuild_vinculos()

    # ------------------------------------------------------------------
    # Comentários
    # ------------------------------------------------------------------
    def _rebuild_comentarios(self):
        _limpar(self._comentarios_layout)
        t = current_theme()
        rotulo = QLabel(_t("Comentários:"))
        rotulo.setProperty("class", "sectionLabel")
        self._comentarios_layout.addWidget(rotulo)

        self.comments_list = QListWidget()
        s = get_session()
        try:
            for c in (s.query(Comment)
                      .filter(Comment.task_id == self.task_id)
                      .order_by(Comment.created_at).all()):
                dt = c.created_at.strftime("%d/%m %H:%M") if c.created_at else ""
                self.comments_list.addItem(f"{dt} — {c.author or 'local'}: {c.body}")
        finally:
            s.close()
        self.comments_list.setMinimumHeight(90)
        self._comentarios_layout.addWidget(self.comments_list)

        linha = QHBoxLayout()
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText(_t("Escreva um comentário..."))
        self.comment_input.returnPressed.connect(self._adicionar_comentario)
        linha.addWidget(self.comment_input, 1)
        enviar = QPushButton(_t("Enviar"))
        enviar.clicked.connect(self._adicionar_comentario)
        linha.addWidget(enviar)
        self._comentarios_layout.addLayout(linha)

    def _adicionar_comentario(self):
        corpo = self.comment_input.text().strip()
        if not corpo:
            return
        s = get_session()
        try:
            s.add(Comment(task_id=self.task_id, body=corpo))
            s.add(ActivityLog(entity_type="task", entity_id=self.task_id,
                              action="commented"))
            s.commit()
            self.task_updated.emit()
        finally:
            s.close()
        self.comment_input.clear()
        self._rebuild_comentarios()

    # ------------------------------------------------------------------
    # Exclusão
    # ------------------------------------------------------------------
    def _delete(self):
        resposta = QMessageBox.question(
            self, _t("Excluir card"),
            _t("Tem certeza que deseja excluir este card?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resposta != QMessageBox.Yes:
            return
        s = get_session()
        try:
            task = s.get(Task, self.task_id)
            if task is not None:
                task.deleted_at = datetime.utcnow()
                s.add(ActivityLog(entity_type="task", entity_id=self.task_id,
                                  action="deleted"))
                s.commit()
                self.task_updated.emit()
                self.accept()
        finally:
            s.close()

    def accept(self):
        if self._desc_timer.isActive():
            self._desc_timer.stop()
            self._salvar_descricao()
        super().accept()

    def reject(self):
        if self._desc_timer.isActive():
            self._desc_timer.stop()
            self._salvar_descricao()
        super().reject()


def _limpar(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.deleteLater()
        elif item.layout() is not None:
            _limpar(item.layout())
