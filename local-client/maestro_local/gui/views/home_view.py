"""Tela inicial (home) — tudo acessível por botões, sem painel lateral.

Substitui o antigo menu lateral: ao abrir o programa, esta tela mostra as
funcionalidades em cartões agrupados por seção, além de cartões de resumo
(pendências, projeto ativo e próxima pausa para os olhos).
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from maestro_local import features
from maestro_local.config import get_active_project_id
from maestro_local.db.models import Project, get_session
from maestro_local.gui.icons import nav_icon
from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t
from maestro_local.todos import todos_abertos

# Seções da home. Mantém o agrupamento que o menu tinha, mas sem esconder nada
# atrás de um painel: cada seção é uma grade de cartões.
SECOES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Trabalho", ("transcricoes", "dashboard", "daily", "chat")),
    ("Gerenciar", ("projects", "board", "skills")),
    ("Ferramentas", ("study", "vault", "library", "apitester",
                     "kb", "memory", "english", "translate")),
    ("Sistema", ("guide", "settings")),
)

_COLUNAS = 3

# Chaves de seção que não estão em `features.FUNCIONALIDADES` — a tela
# Configurações é protegida (nunca desligável), então não vive lá.
_ROTULOS = {
    "settings": ("Configurações", "Idioma, provedores de IA e transcrições"),
}


def _por_chave() -> dict:
    return {f.chave: f for f in features.FUNCIONALIDADES}


def _saudacao() -> str:
    hora = datetime.now().hour
    if hora < 12:
        return t("Bom dia")
    if hora < 18:
        return t("Boa tarde")
    return t("Boa noite")


class FeatureCard(QFrame):
    """Cartão clicável de uma funcionalidade (ícone, título e descrição)."""

    clicked = Signal(str)

    def __init__(self, chave: str, rotulo: str, descricao: str, parent=None):
        super().__init__(parent)
        self._chave = chave
        self.setProperty("class", "featureCard")
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(84)

        col = QVBoxLayout(self)
        col.setContentsMargins(12, 10, 12, 10)
        col.setSpacing(5)

        self._icone = QLabel()
        self._icone.setFixedSize(20, 20)
        self._icone.setStyleSheet("background: transparent; border: none;")
        col.addWidget(self._icone)

        self._titulo = QLabel(rotulo)
        self._titulo.setProperty("class", "cardTitle")
        self._titulo.setStyleSheet("font-size: 13px;")
        col.addWidget(self._titulo)

        if descricao:
            self._desc = QLabel(descricao)
            self._desc.setProperty("class", "hint")
            self._desc.setWordWrap(True)
            col.addWidget(self._desc, 1)
        else:
            col.addStretch(1)

    def apply_theme(self, ativo: bool = False):
        th = current_theme()
        cor = th.accent if ativo else th.text_secondary
        icone = nav_icon(self._chave, cor)
        self._icone.setPixmap(icone.pixmap(20, 20))

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._chave)
            event.accept()
            return
        super().mousePressEvent(event)


class SummaryCard(QFrame):
    """Cartão de resumo com um valor em destaque e uma ação."""

    action = Signal()

    def __init__(self, titulo: str, icone: str, acao: str, parent=None):
        super().__init__(parent)
        self.setProperty("class", "summaryCard")
        col = QVBoxLayout(self)
        col.setContentsMargins(14, 12, 14, 12)
        col.setSpacing(5)

        cabecalho = QHBoxLayout()
        cabecalho.setSpacing(7)
        self._icone = QLabel()
        self._icone.setFixedSize(16, 16)
        self._icone.setStyleSheet("background: transparent; border: none;")
        cabecalho.addWidget(self._icone)
        rotulo = QLabel(titulo)
        rotulo.setProperty("class", "sectionLabel")
        cabecalho.addWidget(rotulo)
        cabecalho.addStretch()
        col.addLayout(cabecalho)

        self._valor = QLabel("—")
        self._valor.setProperty("class", "summaryValue")
        col.addWidget(self._valor)

        self._detalhe = QLabel("")
        self._detalhe.setProperty("class", "hint")
        self._detalhe.setWordWrap(True)
        col.addWidget(self._detalhe, 1)

        self._btn = QPushButton(acao)
        self._btn.setProperty("class", "secondary")
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.clicked.connect(self.action.emit)
        col.addWidget(self._btn, 0, Qt.AlignLeft)

        self._icone_chave = icone

    def set_rate(self, valor: str, detalhe: str = ""):
        self._valor.setText(valor)
        self._detalhe.setText(detalhe)

    def apply_theme(self):
        th = current_theme()
        icone = nav_icon(self._icone_chave, th.accent)
        self._icone.setPixmap(icone.pixmap(16, 16))


class HomeView(QWidget):
    """Lançador: resumo do dia + todas as funcionalidades em cartões."""

    open_key = Signal(str)
    open_todos = Signal()
    eyecare_test = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        raiz.addWidget(scroll)

        container = QWidget()
        col = QVBoxLayout(container)
        col.setContentsMargins(22, 18, 22, 22)
        col.setSpacing(14)

        self.greeting = QLabel(_saudacao())
        self.greeting.setObjectName("homeGreeting")
        col.addWidget(self.greeting)
        self.subtitle = QLabel(t("Suas ferramentas e o seu dia, num só lugar."))
        self.subtitle.setProperty("class", "hint")
        col.addWidget(self.subtitle)

        # --- Cartões de resumo (widgets estratégicos) ---
        self.card_pendencias = SummaryCard(
            t("Pendências"), "bell", t("Abrir TODOs"))
        self.card_pendencias.action.connect(self.open_todos.emit)
        self.card_projeto = SummaryCard(
            t("Projeto ativo"), "projects", t("Ver projetos"))
        self.card_projeto.action.connect(lambda: self.open_key.emit("projects"))
        self.card_pausa = SummaryCard(
            t("Pausa para os olhos"), "eye", t("Fazer agora"))
        self.card_pausa.action.connect(self.eyecare_test.emit)

        resumo = QHBoxLayout()
        resumo.setSpacing(10)
        for card in (self.card_pendencias, self.card_projeto, self.card_pausa):
            resumo.addWidget(card, 1)
        col.addLayout(resumo)

        # --- Seções de funcionalidades ---
        catalogo = _por_chave()
        self.cards: list[FeatureCard] = []
        for titulo, chaves in SECOES:
            ativas = [k for k in chaves if features.habilitada(k)]
            if not ativas:
                continue
            label = QLabel(t(titulo).upper())
            label.setProperty("class", "homeSection")
            col.addWidget(label)

            grade = QGridLayout()
            grade.setHorizontalSpacing(10)
            grade.setVerticalSpacing(10)
            for indice, chave in enumerate(ativas):
                f = catalogo.get(chave)
                if f is not None:
                    rotulo, descricao = f.rotulo, f.descricao
                else:
                    rotulo, descricao = _ROTULOS.get(chave, (chave, ""))
                card = FeatureCard(chave, t(rotulo), t(descricao))
                card.clicked.connect(self.open_key.emit)
                grade.addWidget(card, indice // _COLUNAS, indice % _COLUNAS)
                self.cards.append(card)
            for c in range(_COLUNAS):
                grade.setColumnStretch(c, 1)
            col.addLayout(grade)

        col.addStretch(1)
        scroll.setWidget(container)
        self.apply_theme()

    # ------------------------------------------------------------------
    def apply_theme(self):
        self.card_pendencias.apply_theme()
        self.card_projeto.apply_theme()
        self.card_pausa.apply_theme()
        pausa_ativa = features.habilitada("eyecare")
        self.card_pausa.setVisible(pausa_ativa)
        for card in self.cards:
            card.apply_theme()

    def refresh(self):
        self.greeting.setText(_saudacao())
        self._atualizar_pendencias()
        self._atualizar_projeto()
        self._atualizar_pausa()

    def _atualizar_pendencias(self):
        itens = todos_abertos(limite=999)
        total = len(itens)
        self.card_pendencias.set_rate(
            str(total) if total else t("Tudo em dia"),
            itens[0]["text"] if itens else t("Nenhuma pendência em aberto."))

    def _atualizar_projeto(self):
        pid = get_active_project_id()
        nome = None
        if pid:
            s = get_session()
            try:
                p = s.get(Project, pid)
                if p is not None:
                    nome = f"{p.key} · {p.name}"
            finally:
                s.close()
        self.card_projeto.set_rate(
            nome or t("Nenhum"), t("Projeto em foco no board."))

    def _atualizar_pausa(self):
        from maestro_local import eyecare
        if not features.habilitada("eyecare"):
            return
        try:
            proxima = eyecare.proxima_pausa()
            self.card_pausa.set_rate(
                proxima.strftime("%H:%M"),
                t("Regra 20-20-20 · a cada {n} min").format(
                    n=eyecare.config()["intervalo_min"]))
        except Exception:  # noqa: BLE001 - resumo não pode quebrar a home
            self.card_pausa.set_rate("—", "")
