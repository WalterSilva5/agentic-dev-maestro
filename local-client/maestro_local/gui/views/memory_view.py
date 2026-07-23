"""Memória agentic do workspace: listar, gravar, buscar e perguntar."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
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

from maestro_local.db.models import MemoryEntry, get_session
from maestro_local.i18n import t as _t

_KINDS = [
    ("fact", "Fato"),
    ("decision", "Decisão"),
    ("preference", "Preferência"),
    ("episode", "Episódio"),
    ("procedure", "Procedimento"),
    ("context", "Contexto"),
]


class MemoryView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(_t("Memória agentic"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        subtitle = QLabel(_t(
            "Base de conhecimento semântica do workspace — fatos, decisões e "
            "contexto para agentes. Busca híbrida (embedding + palavras-chave)."
        ))
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Busca / Q&A
        ask_row = QHBoxLayout()
        self.question = QLineEdit()
        self.question.setPlaceholderText(_t("Buscar ou perguntar à memória..."))
        self.question.returnPressed.connect(self._search)
        ask_row.addWidget(self.question, 1)
        search_btn = QPushButton(_t("Buscar"))
        search_btn.setCursor(Qt.PointingHandCursor)
        search_btn.clicked.connect(self._search)
        ask_row.addWidget(search_btn)
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

        self.stats_lbl = QLabel("")
        self.stats_lbl.setObjectName("subtitle")
        layout.addWidget(self.stats_lbl)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        filter_row = QHBoxLayout()
        self.kind_filter = QComboBox()
        self.kind_filter.addItem(_t("Todos os tipos"), "")
        for k, label in _KINDS:
            self.kind_filter.addItem(_t(label), k)
        self.kind_filter.currentIndexChanged.connect(self._reload)
        filter_row.addWidget(self.kind_filter, 1)
        newb = QPushButton(_t("+ Nova"))
        newb.setCursor(Qt.PointingHandCursor)
        newb.clicked.connect(self._new)
        filter_row.addWidget(newb)
        ll.addLayout(filter_row)
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
        self.title_edit.setPlaceholderText(_t("Título"))
        rl.addWidget(self.title_edit)

        meta = QHBoxLayout()
        self.kind_edit = QComboBox()
        for k, label in _KINDS:
            self.kind_edit.addItem(_t(label), k)
        meta.addWidget(self.kind_edit)
        meta.addWidget(QLabel(_t("Importância")))
        self.importance = QDoubleSpinBox()
        self.importance.setRange(0.0, 1.0)
        self.importance.setSingleStep(0.1)
        self.importance.setValue(0.5)
        meta.addWidget(self.importance)
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText(_t("tags, separadas, por vírgula"))
        meta.addWidget(self.tags_edit, 1)
        rl.addLayout(meta)

        self.summary_edit = QLineEdit()
        self.summary_edit.setPlaceholderText(_t("Resumo curto (opcional)"))
        rl.addWidget(self.summary_edit)

        self.body_edit = QPlainTextEdit()
        self.body_edit.setPlaceholderText(_t("Conteúdo da memória..."))
        rl.addWidget(self.body_edit, 1)

        save_row = QHBoxLayout()
        save = QPushButton(_t("Salvar"))
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(self._save)
        save_row.addWidget(save)
        save_row.addStretch()
        self.meta_lbl = QLabel("")
        self.meta_lbl.setObjectName("subtitle")
        save_row.addWidget(self.meta_lbl)
        rl.addLayout(save_row)
        splitter.addWidget(right)
        splitter.setSizes([280, 520])
        layout.addWidget(splitter, 1)

        self._sel_id = None
        self.refresh()

    def refresh(self):
        self._reload()
        self._update_stats()

    def _update_stats(self):
        from maestro_local import memory as mem
        s = get_session()
        try:
            st = mem.stats(s)
        finally:
            s.close()
        self.stats_lbl.setText(
            _t("Total") + f": {st['total']}  ·  "
            + _t("Com embedding") + f": {st['withEmbedding']}  ·  "
            + ", ".join(f"{k}={v}" for k, v in sorted((st.get("byKind") or {}).items()))
        )

    def _reload(self):
        kind = self.kind_filter.currentData() or None
        s = get_session()
        try:
            from maestro_local import memory as mem
            rows = mem.list_entries(s, kind=kind, limit=200)
        finally:
            s.close()
        self.list.clear()
        for n in rows:
            label = f"[{n.get('kind')}] {n.get('title') or '(sem título)'}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, n["id"])
            self.list.addItem(item)

    def _open(self, item):
        mid = item.data(Qt.UserRole)
        s = get_session()
        try:
            e = (
                s.query(MemoryEntry)
                .filter(MemoryEntry.id == mid, MemoryEntry.deleted_at.is_(None))
                .first()
            )
            if not e:
                return
            self._sel_id = e.id
            self.title_edit.setText(e.title or "")
            self.summary_edit.setText(e.summary or "")
            self.body_edit.setPlainText(e.content or "")
            self.tags_edit.setText(e.tags or "")
            self.importance.setValue(float(e.importance or 0.5))
            idx = self.kind_edit.findData(e.kind or "fact")
            if idx >= 0:
                self.kind_edit.setCurrentIndex(idx)
            emb = _t("sim") if e.embedding else _t("não")
            self.meta_lbl.setText(
                f"id={e.id} · embed={emb} · source={e.source_type or 'manual'}"
            )
        finally:
            s.close()

    def _new(self):
        self._sel_id = None
        self.title_edit.clear()
        self.summary_edit.clear()
        self.body_edit.clear()
        self.tags_edit.clear()
        self.importance.setValue(0.5)
        self.kind_edit.setCurrentIndex(0)
        self.meta_lbl.clear()

    def _save(self):
        title = self.title_edit.text().strip()
        content = self.body_edit.toPlainText().strip()
        if not content:
            return
        if not title:
            title = content[:80]
        from maestro_local import memory as mem
        s = get_session()
        try:
            if self._sel_id:
                e = (
                    s.query(MemoryEntry)
                    .filter(
                        MemoryEntry.id == self._sel_id,
                        MemoryEntry.deleted_at.is_(None),
                    )
                    .first()
                )
                if not e:
                    return
                mem.update_entry(
                    s,
                    e,
                    title=title,
                    content=content,
                    kind=self.kind_edit.currentData() or "fact",
                    summary=self.summary_edit.text().strip(),
                    tags=self.tags_edit.text().strip(),
                    importance=self.importance.value(),
                )
            else:
                e = mem.remember(
                    s,
                    title=title,
                    content=content,
                    kind=self.kind_edit.currentData() or "fact",
                    summary=self.summary_edit.text().strip(),
                    tags=self.tags_edit.text().strip(),
                    importance=self.importance.value(),
                    source_type="manual",
                )
            s.commit()
            self._sel_id = e.id
        except Exception as ex:  # noqa: BLE001
            s.rollback()
            self.answer.setText(_t("Erro") + f": {ex}")
            return
        finally:
            s.close()
        self.refresh()

    def _delete(self):
        item = self.list.currentItem()
        if not item:
            return
        mid = item.data(Qt.UserRole)
        from maestro_local import memory as mem
        s = get_session()
        try:
            e = (
                s.query(MemoryEntry)
                .filter(MemoryEntry.id == mid, MemoryEntry.deleted_at.is_(None))
                .first()
            )
            if e:
                mem.soft_delete(s, e)
                s.commit()
        finally:
            s.close()
        if self._sel_id == mid:
            self._new()
        self.refresh()

    def _search(self):
        query = self.question.text().strip()
        if not query:
            self._reload()
            return
        from maestro_local import memory as mem
        s = get_session()
        try:
            hits = mem.search(s, query, top_k=12, mark_accessed=True)
        finally:
            s.close()
        self.list.clear()
        if not hits:
            self.answer.setText(_t("Nenhuma memória relevante."))
            return
        self.answer.setText(
            _t("Resultados") + f": {len(hits)} — " +
            ", ".join(f"{h['title']} ({h.get('score', 0)})" for h in hits[:5])
        )
        for h in hits:
            label = f"[{h.get('kind')}] {h.get('title')}  ·  {h.get('score', 0)}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, h["id"])
            self.list.addItem(item)

    def _ask(self):
        question = self.question.text().strip()
        if not question:
            return
        from maestro_local import memory as mem
        self.answer.setText(_t("Pensando..."))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        s = get_session()
        try:
            result = mem.answer(s, question)
        except Exception as e:  # noqa: BLE001
            self.answer.setText(_t("Erro") + f": {e}")
            return
        finally:
            s.close()
            QApplication.restoreOverrideCursor()
        txt = result.get("answer") or ""
        if result.get("sources"):
            txt += "\n\n" + _t("Fontes") + ": " + ", ".join(
                f"{src.get('title')} (#{src.get('id')})" for src in result["sources"]
            )
        self.answer.setText(txt)
