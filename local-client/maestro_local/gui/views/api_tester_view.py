"""Testador de API (mini-Postman): monta, executa e salva requisições HTTP,
com histórico de execuções. Executa via a mesma função da API (stdlib)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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

from maestro_local.db.models import ApiCall, ApiRequest, get_session
from maestro_local.i18n import t as _t

METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


class ApiTesterView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(_t("Testador de API"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        subtitle = QLabel(_t("Monte, execute e salve requisições HTTP (mini-Postman)."))
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        self._editing_id = None

        splitter = QSplitter(Qt.Horizontal)

        # ---- Coluna esquerda: builder + resposta ----
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)

        url_row = QHBoxLayout()
        self.method = QComboBox()
        self.method.addItems(METHODS)
        self.method.setFixedWidth(90)
        url_row.addWidget(self.method)
        self.url = QLineEdit()
        self.url.setPlaceholderText("https://...")
        self.url.returnPressed.connect(self._run)
        url_row.addWidget(self.url, 1)
        run_btn = QPushButton(_t("Executar"))
        run_btn.setCursor(Qt.PointingHandCursor)
        run_btn.clicked.connect(self._run)
        url_row.addWidget(run_btn)
        ll.addLayout(url_row)

        self.name = QLineEdit()
        self.name.setPlaceholderText(_t("Nome para salvar"))
        ll.addWidget(self.name)

        self.headers = QPlainTextEdit()
        self.headers.setPlaceholderText(_t('Headers (JSON ou "Chave: valor" por linha)'))
        self.headers.setFixedHeight(60)
        ll.addWidget(self.headers)

        self.body = QPlainTextEdit()
        self.body.setPlaceholderText(_t("Corpo (body)"))
        self.body.setFixedHeight(80)
        ll.addWidget(self.body)

        save_row = QHBoxLayout()
        save_btn = QPushButton(_t("Salvar"))
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        save_row.addWidget(save_btn)
        new_btn = QPushButton(_t("Novo"))
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.clicked.connect(self._new)
        save_row.addWidget(new_btn)
        save_row.addStretch()
        self.status = QLabel("")
        self.status.setObjectName("subtitle")
        save_row.addWidget(self.status)
        ll.addLayout(save_row)

        self.resp_meta = QLabel("")
        ll.addWidget(self.resp_meta)
        self.resp_body = QPlainTextEdit()
        self.resp_body.setReadOnly(True)
        ll.addWidget(self.resp_body, 1)
        splitter.addWidget(left)

        # ---- Coluna direita: salvos + histórico ----
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel(_t("Salvos")))
        self.saved_list = QListWidget()
        self.saved_list.itemClicked.connect(self._load_saved)
        rl.addWidget(self.saved_list, 1)
        del_btn = QPushButton(_t("Excluir selecionado"))
        del_btn.clicked.connect(self._delete_saved)
        rl.addWidget(del_btn)
        rl.addWidget(QLabel(_t("Histórico")))
        self.history_list = QListWidget()
        rl.addWidget(self.history_list, 1)
        splitter.addWidget(right)

        splitter.setSizes([560, 260])
        layout.addWidget(splitter, 1)

        self.refresh()

    def refresh(self):
        self._reload_saved()
        self._reload_history()

    def _reload_saved(self):
        self.saved_list.clear()
        s = get_session()
        try:
            for r in s.query(ApiRequest).order_by(ApiRequest.updated_at.desc()).all():
                item = QListWidgetItem(f"{r.method}  {r.name}")
                item.setData(Qt.UserRole, r.id)
                self.saved_list.addItem(item)
        finally:
            s.close()

    def _reload_history(self):
        self.history_list.clear()
        s = get_session()
        try:
            for c in s.query(ApiCall).order_by(ApiCall.created_at.desc()).limit(30).all():
                st = c.status if c.status is not None else "ERR"
                self.history_list.addItem(f"{st}  {c.method}  {c.duration_ms}ms  {c.url}")
        finally:
            s.close()

    def _run(self):
        from maestro_local.api.app import _run_http_request
        url = self.url.text().strip()
        if not url:
            return
        self.status.setText(_t("Executando..."))
        method = self.method.currentText()
        result = _run_http_request(method, url, self.headers.toPlainText(), self.body.toPlainText())
        self.status.setText("")
        ok = result["ok"]
        st = result["status"] if result["status"] is not None else _t("Erro")
        color = "#2f9e44" if ok else "#e5484d"
        self.resp_meta.setText(
            f"<b style='color:{color}'>{st}</b> · {result['durationMs']} ms"
            + (f" · {result['error']}" if result.get("error") else ""))
        self.resp_body.setPlainText(result.get("body") or result.get("error") or "")

        s = get_session()
        try:
            s.add(ApiCall(
                request_id=self._editing_id, method=method, url=url,
                status=result["status"], duration_ms=result["durationMs"],
                ok=ok, error=result.get("error") or "",
                response_snippet=(result.get("body") or "")[:2000],
            ))
            s.commit()
        finally:
            s.close()
        self._reload_history()

    def _save(self):
        name = self.name.text().strip()
        url = self.url.text().strip()
        if not name or not url:
            self.status.setText(_t("Informe nome e URL"))
            return
        s = get_session()
        try:
            if self._editing_id:
                row = s.get(ApiRequest, self._editing_id)
            else:
                row = ApiRequest()
                s.add(row)
            row.name = name
            row.method = self.method.currentText()
            row.url = url
            row.headers = self.headers.toPlainText()
            row.body = self.body.toPlainText()
            s.commit()
            self._editing_id = row.id
        finally:
            s.close()
        self.status.setText(_t("Salvo"))
        self._reload_saved()

    def _new(self):
        self._editing_id = None
        self.name.clear()
        self.url.clear()
        self.headers.clear()
        self.body.clear()
        self.resp_meta.clear()
        self.resp_body.clear()
        self.status.setText("")

    def _load_saved(self, item):
        rid = item.data(Qt.UserRole)
        s = get_session()
        try:
            row = s.get(ApiRequest, rid)
            if not row:
                return
            self._editing_id = row.id
            self.name.setText(row.name)
            self.url.setText(row.url or "")
            idx = self.method.findText(row.method or "GET")
            self.method.setCurrentIndex(idx if idx >= 0 else 0)
            self.headers.setPlainText(row.headers or "")
            self.body.setPlainText(row.body or "")
        finally:
            s.close()

    def _delete_saved(self):
        item = self.saved_list.currentItem()
        if not item:
            return
        rid = item.data(Qt.UserRole)
        s = get_session()
        try:
            row = s.get(ApiRequest, rid)
            if row:
                s.delete(row)
                s.commit()
        finally:
            s.close()
        if self._editing_id == rid:
            self._new()
        self._reload_saved()
