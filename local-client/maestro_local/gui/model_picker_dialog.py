"""Lista os modelos que o provedor respondeu, para copiar ou usar.

O nome do modelo é digitado à mão na configuração, e errar um caractere só
aparece muito depois — como falha na primeira chamada de IA, longe da tela onde
o erro foi cometido. Ver a lista que o próprio provedor devolveu e escolher dali
tira o palpite do caminho.

Duas saídas porque são dois usos diferentes: **Usar** preenche o campo (o caso
comum) e **Copiar** manda para a área de transferência, para quem quer o nome em
outro lugar — um script, o `.env` de outro projeto.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
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


class ModelPickerDialog(QDialog):
    def __init__(self, parent, modelos: list[str], atual: str = ""):
        super().__init__(parent)
        self._modelos = list(modelos)
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
        lay.addWidget(self.lista, 1)

        acoes = QHBoxLayout()
        acoes.setSpacing(8)
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

    def selecionado(self) -> str:
        item = self.lista.currentItem()
        return item.text() if item is not None else ""

    def _copiar(self):
        nome = self.selecionado()
        if nome:
            QApplication.clipboard().setText(nome)

    def _usar(self):
        nome = self.selecionado()
        if not nome:
            return
        self.escolhido = nome
        self.accept()
