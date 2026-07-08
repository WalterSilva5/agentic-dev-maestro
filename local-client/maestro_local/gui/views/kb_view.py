"""Base de conhecimento (2º cérebro): notas KB com backlinks [[título]] e
perguntas respondidas pela IA sobre as notas (RAG-lite)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from maestro_local.db.models import Document, get_session
from maestro_local.i18n import t as _t


class KBView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(_t("Base de conhecimento"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        subtitle = QLabel(_t("Notas com backlinks [[título]] e perguntas respondidas pela IA sobre as suas notas."))
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Q&A
        ask_row = QHBoxLayout()
        self.question = QLineEdit()
        self.question.setPlaceholderText(_t("Pergunte à sua base..."))
        self.question.returnPressed.connect(self._ask)
        ask_row.addWidget(self.question, 1)
        ask_btn = QPushButton(_t("Perguntar à IA"))
        ask_btn.setCursor(Qt.PointingHandCursor)
        ask_btn.clicked.connect(self._ask)
        ask_row.addWidget(ask_btn)
        layout.addLayout(ask_row)
        self.answer = QLabel("")
        self.answer.setWordWrap(True)
        self.answer.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.answer.setObjectName("subtitle")
        layout.addWidget(self.answer)

        # Notas: lista + editor
        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(_t("Buscar..."))
        self.search.textChanged.connect(self._reload)
        top.addWidget(self.search, 1)
        newb = QPushButton(_t("+ Nova"))
        newb.setCursor(Qt.PointingHandCursor)
        newb.clicked.connect(self._new)
        top.addWidget(newb)
        ll.addLayout(top)
        self.list = QListWidget()
        self.list.itemClicked.connect(self._open)
        ll.addWidget(self.list, 1)
        dele = QPushButton(_t("Excluir selecionada"))
        dele.clicked.connect(self._delete)
        ll.addWidget(dele)
        splitter.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(_t("Título da nota"))
        rl.addWidget(self.title_edit)
        self.body_edit = QPlainTextEdit()
        self.body_edit.setPlaceholderText(_t("Conteúdo... use [[título]] para linkar outra nota"))
        rl.addWidget(self.body_edit, 1)
        save_row = QHBoxLayout()
        save = QPushButton(_t("Salvar"))
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(self._save)
        save_row.addWidget(save)
        save_row.addStretch()
        self.backlinks_lbl = QLabel("")
        self.backlinks_lbl.setObjectName("subtitle")
        save_row.addWidget(self.backlinks_lbl)
        rl.addLayout(save_row)
        splitter.addWidget(right)
        splitter.setSizes([240, 520])
        layout.addWidget(splitter, 1)

        self._sel_id = None
        self.refresh()

    def refresh(self):
        self._reload()

    def _notes(self):
        s = get_session()
        try:
            docs = (s.query(Document).filter(Document.type == "KB")
                    .order_by(Document.updated_at.desc()).all())
            return [{"id": d.id, "title": d.title, "body": d.body or ""} for d in docs]
        finally:
            s.close()

    def _reload(self):
        q = self.search.text().lower().strip()
        self.list.clear()
        for n in self._notes():
            if q and q not in f"{n['title']} {n['body']}".lower():
                continue
            item = QListWidgetItem(n["title"])
            item.setData(Qt.UserRole, n["id"])
            self.list.addItem(item)
        self._update_backlinks()

    def _open(self, item):
        nid = item.data(Qt.UserRole)
        s = get_session()
        try:
            d = s.get(Document, nid)
            if not d:
                return
            self._sel_id = d.id
            self.title_edit.setText(d.title)
            self.body_edit.setPlainText(d.body or "")
        finally:
            s.close()
        self._update_backlinks()

    def _new(self):
        self._sel_id = None
        self.title_edit.clear()
        self.body_edit.clear()
        self.backlinks_lbl.clear()

    def _save(self):
        from datetime import datetime as _dt
        title = self.title_edit.text().strip()
        if not title:
            return
        s = get_session()
        try:
            if self._sel_id:
                d = s.get(Document, self._sel_id)
            else:
                d = Document(type="KB")
                s.add(d)
            d.title = title
            d.body = self.body_edit.toPlainText()
            d.type = "KB"
            d.version = (d.version or 1) + 1
            d.updated_at = _dt.utcnow()
            s.commit()
            self._sel_id = d.id
        finally:
            s.close()
        self._reload()

    def _delete(self):
        item = self.list.currentItem()
        if not item:
            return
        nid = item.data(Qt.UserRole)
        s = get_session()
        try:
            d = s.get(Document, nid)
            if d:
                s.delete(d)
                s.commit()
        finally:
            s.close()
        if self._sel_id == nid:
            self._new()
        self._reload()

    def _update_backlinks(self):
        if not self._sel_id:
            self.backlinks_lbl.setText("")
            return
        from maestro_local.kb import backlinks
        notes = self._notes()
        links = backlinks(notes).get(self._sel_id, [])
        if links:
            self.backlinks_lbl.setText(
                _t("Referenciada por") + ": " + ", ".join(b["title"] for b in links))
        else:
            self.backlinks_lbl.setText("")

    def _ask(self):
        from maestro_local.kb import answer as kb_answer
        question = self.question.text().strip()
        if not question:
            return
        notes = self._notes()
        if not notes:
            self.answer.setText(_t("Nenhuma nota na base de conhecimento ainda."))
            return
        self.answer.setText(_t("Pensando..."))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = kb_answer(notes, question)
        except Exception as e:  # noqa: BLE001
            self.answer.setText(_t("Erro") + f": {e}")
            return
        finally:
            QApplication.restoreOverrideCursor()
        txt = result["answer"]
        if result.get("sources"):
            txt += "\n\n" + _t("Fontes") + ": " + ", ".join(s["title"] for s in result["sources"])
        self.answer.setText(txt)
