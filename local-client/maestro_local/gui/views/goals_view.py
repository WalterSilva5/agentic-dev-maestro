"""Goals: objetivos de fluxo com progresso e contagem regressiva.

Um goal é "entregar as tarefas que casam com <filtros> até <data>". Os filtros
(tag, épico e sprint) são opcionais e combináveis. O progresso conta cards em
coluna de conclusão sobre o total do filtro.
"""
from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from maestro_local.config import get_active_project_id
from maestro_local.db.models import (
    BoardColumn,
    Epic,
    Goal,
    Label,
    Project,
    Sprint,
    Task,
    get_session,
)
from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t as _t


def _progresso(goal, s) -> tuple[int, int]:
    q = s.query(Task).filter(
        Task.project_id == goal.project_id,
        Task.deleted_at == None,  # noqa: E711
        Task.archived_at == None,  # noqa: E711
    )
    if goal.tag:
        q = q.filter(Task.labels.any(Label.name == goal.tag))
    if goal.epic_id:
        q = q.filter(Task.epics.any(Epic.id == goal.epic_id))
    if goal.sprint_id:
        q = q.filter(Task.sprint_id == goal.sprint_id)
    total = q.count()
    done = q.join(BoardColumn, Task.column_id == BoardColumn.id).filter(
        BoardColumn.is_done == True).count()  # noqa: E712
    return done, total


class GoalDialog(QDialog):
    def __init__(self, project_id: int, goal: Goal | None = None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle(_t("Editar goal") if goal else _t("Novo goal"))
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        self.name = QLineEdit(goal.name if goal else "")
        self.name.setPlaceholderText(_t("Ex.: entregar cashier até o fim do mês"))
        form.addRow(_t("Goal:"), self.name)

        self.desc = QTextEdit(goal.description if goal else "")
        self.desc.setFixedHeight(70)
        form.addRow(_t("Descrição:"), self.desc)

        self.due = QDateEdit()
        self.due.setCalendarPopup(True)
        self.due.setDisplayFormat("dd/MM/yyyy")
        self.due.setSpecialValueText(_t("Sem data"))
        if goal and goal.due_date:
            self.due.setDate(QDate(goal.due_date.year, goal.due_date.month, goal.due_date.day))
        else:
            self.due.setDate(self.due.minimumDate())
        form.addRow(_t("Até:"), self.due)

        self.tag = QComboBox()
        self.tag.setEditable(True)
        self.tag.addItem(_t("(qualquer tag)"), "")
        s = get_session()
        try:
            for lbl in s.query(Label).order_by(Label.name).all():
                self.tag.addItem(lbl.name, lbl.name)
        finally:
            s.close()
        if goal and goal.tag:
            i = self.tag.findData(goal.tag)
            self.tag.setCurrentIndex(i if i >= 0 else 0)
            if i < 0:
                self.tag.setEditText(goal.tag)
        form.addRow(_t("Com a tag:"), self.tag)

        self.epic = QComboBox()
        self.epic.addItem(_t("(qualquer épico)"), None)
        self.sprint = QComboBox()
        self.sprint.addItem(_t("(qualquer sprint)"), None)
        s = get_session()
        try:
            for ep in s.query(Epic).filter(Epic.project_id == project_id).order_by(Epic.name).all():
                self.epic.addItem(ep.name, ep.id)
            for sp in s.query(Sprint).filter(Sprint.project_id == project_id).order_by(
                    Sprint.sort_order, Sprint.id).all():
                self.sprint.addItem(sp.name, sp.id)
        finally:
            s.close()
        if goal and goal.epic_id:
            i = self.epic.findData(goal.epic_id)
            if i >= 0:
                self.epic.setCurrentIndex(i)
        if goal and goal.sprint_id:
            i = self.sprint.findData(goal.sprint_id)
            if i >= 0:
                self.sprint.setCurrentIndex(i)
        form.addRow(_t("Épico:"), self.epic)
        form.addRow(_t("Sprint:"), self.sprint)

        lay.addLayout(form)
        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        lay.addWidget(botoes)

    def valores(self) -> dict:
        due = None
        if self.due.date() != self.due.minimumDate():
            q = self.due.date()
            due = datetime(q.year(), q.month(), q.day())
        return {
            "name": self.name.text().strip(),
            "description": self.desc.toPlainText().strip(),
            "due_date": due,
            "tag": (self.tag.currentData() or self.tag.currentText() or "").strip() or None,
            "epic_id": self.epic.currentData(),
            "sprint_id": self.sprint.currentData(),
        }


class GoalCard(QFrame):
    edit_clicked = Signal(int)
    delete_clicked = Signal(int)

    def __init__(self, goal: Goal, done: int, total: int, sprint_info: str):
        super().__init__()
        t = current_theme()
        self.setProperty("class", "card")
        pct = int(done / total * 100) if total else 0

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        topo = QHBoxLayout()
        nome = QLabel(goal.name)
        nome.setProperty("class", "cardTitle")
        nome.setStyleSheet("font-size: 16px;")
        topo.addWidget(nome, 1)
        if goal.due_date:
            dias = (goal.due_date.date() - date.today()).days
            cor = t.danger if dias < 0 else (t.warning if dias <= 7 else t.text_muted)
            rotulo = _t("{d} dias").format(d=dias) if dias >= 0 else _t("{d} dias (atrasado)").format(d=abs(dias))
            prazo = QLabel(rotulo)
            prazo.setStyleSheet(f"color: {cor}; font-weight: 700; font-size: 12px;")
            topo.addWidget(prazo)
        editar = QPushButton(_t("Editar"))
        editar.setProperty("class", "secondary")
        editar.clicked.connect(lambda: self.edit_clicked.emit(goal.id))
        topo.addWidget(editar)
        excluir = QPushButton("✕")
        excluir.setFixedSize(24, 24)
        excluir.setCursor(Qt.PointingHandCursor)
        excluir.setStyleSheet(f"background: transparent; color: {t.text_muted}; border: none;")
        excluir.clicked.connect(lambda: self.delete_clicked.emit(goal.id))
        topo.addWidget(excluir)
        lay.addLayout(topo)

        filtros = []
        if goal.tag:
            filtros.append(f"#{goal.tag}")
        if goal.epic:
            filtros.append(goal.epic.name)
        if goal.sprint:
            filtros.append(goal.sprint.name)
        if filtros:
            f = QLabel("  ·  ".join(filtros))
            f.setProperty("class", "hint")
            lay.addWidget(f)
        if goal.description:
            d = QLabel(goal.description)
            d.setWordWrap(True)
            d.setProperty("class", "hint")
            lay.addWidget(d)

        linha = QHBoxLayout()
        barra = QProgressBar()
        barra.setValue(pct)
        barra.setTextVisible(True)
        barra.setFormat(f"{pct}%  ({done}/{total})")
        barra.setFixedHeight(18)
        linha.addWidget(barra, 1)
        if sprint_info:
            sl = QLabel(sprint_info)
            sl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px;")
            linha.addWidget(sl)
        lay.addLayout(linha)


class GoalsView(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 20)
        root.setSpacing(12)

        topo = QHBoxLayout()
        titulo = QLabel(_t("Goals"))
        titulo.setObjectName("sectionTitle")
        topo.addWidget(titulo)
        topo.addStretch()
        self.novo_btn = QPushButton(_t("+ Novo goal"))
        self.novo_btn.setCursor(Qt.PointingHandCursor)
        self.novo_btn.clicked.connect(self._novo)
        topo.addWidget(self.novo_btn)
        root.addLayout(topo)

        self.subtitulo = QLabel("")
        self.subtitulo.setObjectName("subtitle")
        self.subtitulo.setWordWrap(True)
        root.addWidget(self.subtitulo)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.container = QWidget()
        self.col = QVBoxLayout(self.container)
        self.col.setContentsMargins(0, 0, 0, 0)
        self.col.setSpacing(12)
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)

        self.refresh()

    # ------------------------------------------------------------------
    def _projeto(self):
        pid = get_active_project_id()
        if not pid:
            return None
        s = get_session()
        try:
            return s.get(Project, pid)
        finally:
            s.close()

    def refresh(self):
        while self.col.count():
            item = self.col.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        projeto = self._projeto()
        if projeto is None:
            self.subtitulo.setText(_t("Selecione um projeto para ver os goals."))
            self.novo_btn.setEnabled(False)
            return
        self.novo_btn.setEnabled(True)
        self.subtitulo.setText(
            _t("Objetivos de {proj} — progresso e dias restantes.").format(proj=projeto.name))

        s = get_session()
        try:
            goals = (s.query(Goal)
                     .filter(Goal.project_id == projeto.id)
                     .order_by(Goal.due_date.is_(None), Goal.due_date)
                     .all())
            if not goals:
                vazio = QLabel(_t("Nenhum goal ainda. Crie um com “+ Novo goal”."))
                vazio.setProperty("class", "hint")
                vazio.setAlignment(Qt.AlignCenter)
                self.col.addWidget(vazio)
            for goal in goals:
                done, total = _progresso(goal, s)
                sprint_info = ""
                if goal.sprint is not None and goal.sprint.end_date:
                    dias = (goal.sprint.end_date.date() - date.today()).days
                    sprint_info = _t("Sprint acaba em {d} dias").format(d=dias)
                card = GoalCard(goal, done, total, sprint_info)
                card.edit_clicked.connect(self._editar)
                card.delete_clicked.connect(self._excluir)
                self.col.addWidget(card)
            self.col.addStretch(1)
        finally:
            s.close()

    # ------------------------------------------------------------------
    def _novo(self):
        projeto = self._projeto()
        if projeto is None:
            return
        dlg = GoalDialog(projeto.id, None, self)
        if dlg.exec() != QDialog.Accepted:
            return
        v = dlg.valores()
        if not v["name"]:
            return
        s = get_session()
        try:
            s.add(Goal(project_id=projeto.id, **v))
            s.commit()
        finally:
            s.close()
        self.refresh()

    def _editar(self, goal_id):
        s = get_session()
        try:
            goal = s.get(Goal, goal_id)
            if goal is None:
                return
            projeto_id = goal.project_id
        finally:
            s.close()
        dlg = GoalDialog(projeto_id, goal, self)
        if dlg.exec() != QDialog.Accepted:
            return
        v = dlg.valores()
        if not v["name"]:
            return
        s = get_session()
        try:
            goal = s.get(Goal, goal_id)
            if goal is not None:
                for k, val in v.items():
                    setattr(goal, k, val)
                s.commit()
        finally:
            s.close()
        self.refresh()

    def _excluir(self, goal_id):
        if QMessageBox.question(
                self, _t("Excluir goal"),
                _t("Excluir este goal?"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        s = get_session()
        try:
            goal = s.get(Goal, goal_id)
            if goal is not None:
                s.delete(goal)
                s.commit()
        finally:
            s.close()
        self.refresh()
