"""Tradutor (estilo Google Tradutor): origem (com detecção automática) →
destino, via provedor de IA. Desktop, in-process, com a IA em QThread."""
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from maestro_local.i18n import t as _t

# (código, rótulo). "auto" só na origem.
LANGS = [
    ("pt", "Português"),
    ("en", "Inglês"),
    ("es", "Espanhol"),
    ("fr", "Francês"),
    ("de", "Alemão"),
    ("it", "Italiano"),
    ("ja", "Japonês"),
    ("zh", "Chinês"),
    ("ko", "Coreano"),
    ("ru", "Russo"),
]


class _TranslateWorker(QThread):
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, text, source, target, parent=None):
        super().__init__(parent)
        self.text = text
        self.source = source
        self.target = target

    def run(self):
        from maestro_local.translate import translate
        try:
            self.done.emit(translate(self.text, self.source, self.target))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class TranslateView(QWidget):
    def __init__(self):
        super().__init__()
        self._worker = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(_t("Tradutor"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        subtitle = QLabel(_t("Traduza texto entre idiomas (detecção automática da origem)."))
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # Seletores de idioma
        sel = QHBoxLayout()
        self.source = QComboBox()
        self.source.addItem(_t("Detectar idioma"), "auto")
        for code, label in LANGS:
            self.source.addItem(_t(label), code)
        sel.addWidget(self.source, 1)

        self.swap_btn = QPushButton("⇄")
        self.swap_btn.setFixedWidth(40)
        self.swap_btn.setToolTip(_t("Trocar idiomas"))
        self.swap_btn.setCursor(Qt.PointingHandCursor)
        self.swap_btn.clicked.connect(self._swap)
        sel.addWidget(self.swap_btn)

        self.target = QComboBox()
        for code, label in LANGS:
            self.target.addItem(_t(label), code)
        self.target.setCurrentIndex(1)  # Inglês
        sel.addWidget(self.target, 1)
        layout.addLayout(sel)

        # Áreas de texto lado a lado
        panes = QHBoxLayout()
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText(_t("Digite o texto..."))
        panes.addWidget(self.input, 1)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText(_t("Tradução"))
        panes.addWidget(self.output, 1)
        layout.addLayout(panes, 1)

        # Ações
        actions = QHBoxLayout()
        self.translate_btn = QPushButton(_t("Traduzir"))
        self.translate_btn.setCursor(Qt.PointingHandCursor)
        self.translate_btn.clicked.connect(self._translate)
        actions.addWidget(self.translate_btn)
        self.copy_btn = QPushButton(_t("Copiar"))
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy)
        actions.addWidget(self.copy_btn)
        actions.addStretch()
        self.status = QLabel("")
        self.status.setObjectName("subtitle")
        actions.addWidget(self.status)
        layout.addLayout(actions)

    def refresh(self):
        pass

    def _swap(self):
        src = self.source.currentData()
        tgt = self.target.currentData()
        new_src = tgt
        new_tgt = src if src != "auto" else "en"
        self.source.setCurrentIndex(self.source.findData(new_src))
        self.target.setCurrentIndex(self.target.findData(new_tgt))
        # troca os textos também
        in_txt = self.input.toPlainText()
        out_txt = self.output.toPlainText()
        self.input.setPlainText(out_txt)
        self.output.setPlainText(in_txt)

    def _translate(self):
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.translate_btn.setEnabled(False)
        self.status.setText(_t("Traduzindo..."))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._worker = _TranslateWorker(text, self.source.currentData(), self.target.currentData())
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_done(self, res):
        QApplication.restoreOverrideCursor()
        self.translate_btn.setEnabled(True)
        self.output.setPlainText(res.get("translated", ""))
        if self.source.currentData() == "auto" and res.get("detectedSource"):
            self.status.setText(_t("Detectado") + f": {res['detectedSource']}")
        else:
            self.status.setText("")

    def _on_failed(self, msg):
        QApplication.restoreOverrideCursor()
        self.translate_btn.setEnabled(True)
        self.status.setText(_t("Erro") + f": {msg}")

    def _copy(self):
        txt = self.output.toPlainText()
        if txt:
            QApplication.clipboard().setText(txt)
            self.status.setText(_t("Copiado!"))
