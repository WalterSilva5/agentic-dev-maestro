"""Lista os modelos que o provedor respondeu, para copiar ou usar.

O nome do modelo é digitado à mão na configuração, e errar um caractere só
aparece muito depois — como falha na primeira chamada de IA, longe da tela onde
o erro foi cometido. Ver a lista que o próprio provedor devolveu e escolher dali
tira o palpite do caminho.

Duas saídas porque são dois usos diferentes: **Usar** preenche o campo (o caso
comum) e **Copiar** manda para a área de transferência, para quem quer o nome em
outro lugar — um script, o `.env` de outro projeto.

Estar na lista não garante que o modelo funcione: `/models` é catálogo, não
lista de permissões, e não diz nada sobre região, plano ou opt-in. Daí o botão
**Verificar**, que faz uma chamada mínima de verdade. Ele é botão, e não
verificação automática ao selecionar, porque a chamada custa — quem decide
gastar é o usuário, num clique explícito.
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from maestro_local.i18n import t


class _VerificacaoWorker(QThread):
    """Fora da thread da interface: a chamada pode levar segundos."""

    done = Signal(bool, str)

    def __init__(self, provider, modelo):
        super().__init__()
        self._provider = provider
        self._modelo = modelo

    def run(self):
        from maestro_local.ai.providers import verificar_modelo
        ok, msg = verificar_modelo(self._provider, self._modelo)
        self.done.emit(ok, msg)


class ModelPickerDialog(QDialog):
    def __init__(self, parent, modelos: list[str], atual: str = "",
                 provider: dict | None = None):
        super().__init__(parent)
        self._modelos = list(modelos)
        self._provider = provider or {}
        self._worker = None
        self.escolhido: str | None = None
        self.setWindowTitle(t("Modelos disponíveis"))
        self.setMinimumSize(460, 420)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        titulo = QLabel(
            t("{n} modelo(s) respondidos pelo provedor.").format(n=len(self._modelos)))
        titulo.setProperty("class", "hint")
        titulo.setWordWrap(True)
        lay.addWidget(titulo)

        # Provedores locais chegam a listar dezenas de modelos; rolar a lista
        # inteira para achar um nome conhecido é pior do que digitar parte dele.
        self.filtro = QLineEdit()
        self.filtro.setPlaceholderText(t("Filtrar..."))
        self.filtro.setClearButtonEnabled(True)
        self.filtro.textChanged.connect(self._aplicar_filtro)
        lay.addWidget(self.filtro)

        self.lista = QListWidget()
        self.lista.itemDoubleClicked.connect(lambda _: self._usar())
        # O resultado é de um modelo só; trocar a seleção o torna enganoso.
        self.lista.currentItemChanged.connect(self._on_selecao_mudou)
        lay.addWidget(self.lista, 1)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setProperty("class", "hint")
        lay.addWidget(self.status)

        acoes = QHBoxLayout()
        acoes.setSpacing(8)
        self.btn_verificar = QPushButton(t("Verificar"))
        self.btn_verificar.setProperty("class", "secondary")
        self.btn_verificar.setToolTip(
            t("Faz uma chamada real e mínima ao provedor para confirmar que o "
              "modelo responde. Estar na lista não garante acesso — pode ser "
              "recusado por região ou plano. A chamada é cobrada."))
        self.btn_verificar.clicked.connect(self._verificar)
        acoes.addWidget(self.btn_verificar)
        self.btn_copiar = QPushButton(t("Copiar nome"))
        self.btn_copiar.setProperty("class", "secondary")
        self.btn_copiar.clicked.connect(self._copiar)
        acoes.addWidget(self.btn_copiar)
        acoes.addStretch()
        fechar = QPushButton(t("Fechar"))
        fechar.setProperty("flat", "true")
        fechar.clicked.connect(self.reject)
        acoes.addWidget(fechar)
        self.btn_usar = QPushButton(t("Usar este modelo"))
        self.btn_usar.setDefault(True)
        self.btn_usar.clicked.connect(self._usar)
        acoes.addWidget(self.btn_usar)
        lay.addLayout(acoes)

        self._aplicar_filtro("")
        self._selecionar(atual)

    # ------------------------------------------------------------------
    def _aplicar_filtro(self, texto: str):
        alvo = (texto or "").strip().lower()
        self.lista.clear()
        for nome in self._modelos:
            if alvo in nome.lower():
                self.lista.addItem(nome)
        if self.lista.count():
            self.lista.setCurrentRow(0)
        self._atualizar_acoes()

    def _on_selecao_mudou(self, *_a):
        self.status.setText("")
        self._atualizar_acoes()

    def _selecionar(self, nome: str):
        """Deixa o modelo já configurado em foco, se ele estiver na lista."""
        if not nome:
            return
        achados = self.lista.findItems(nome, Qt.MatchExactly)
        if achados:
            self.lista.setCurrentItem(achados[0])

    def _atualizar_acoes(self):
        # Sem seleção, copiar/usar não teriam o que fazer — e um botão que não
        # responde ao clique confunde mais do que um desabilitado.
        tem = self.lista.currentItem() is not None
        self.btn_usar.setEnabled(tem)
        self.btn_copiar.setEnabled(tem)
        # Sem base_url não há o que chamar; esconder o botão explicaria menos
        # do que deixá-lo visível e inerte.
        self.btn_verificar.setEnabled(tem and bool(self._provider.get("base_url")))

    def selecionado(self) -> str:
        item = self.lista.currentItem()
        return item.text() if item is not None else ""

    def _copiar(self):
        nome = self.selecionado()
        if nome:
            QApplication.clipboard().setText(nome)

    def _verificar(self):
        modelo = self.selecionado()
        if not modelo:
            return
        self.status.setText(t("Verificando {m}...").format(m=modelo))
        self.btn_verificar.setEnabled(False)
        self._worker = _VerificacaoWorker(self._provider, modelo)
        self._worker.done.connect(self._on_verificado)
        self._worker.start()

    def _on_verificado(self, ok, msg):
        self.status.setText(("✓ " if ok else "✕ ") + msg)
        self.btn_verificar.setEnabled(True)

    def _usar(self):
        nome = self.selecionado()
        if not nome:
            return
        self.escolhido = nome
        self.accept()

    def closeEvent(self, event):
        """Espera a verificação antes de sumir com o diálogo.

        Destruir uma QThread em execução dispara qFatal e o processo morre com
        SIGABRT — o mesmo modo de falha já visto ao fechar o programa durante
        uma chamada de IA. Aqui a chamada tem timeout de 30s, então a espera é
        limitada e o pior caso é o diálogo demorar a fechar.
        """
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.wait(31000)
        super().closeEvent(event)
