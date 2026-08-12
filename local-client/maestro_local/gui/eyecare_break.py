"""Tela da pausa para os olhos.

Janela própria em tela cheia, fora da janela do Maestro — como o SafeEyes faz.
Uma pausa desenhada dentro do aplicativo só interrompe quem já estava olhando
para ele; quem estava no editor ou no navegador nem via o lembrete, que é
justamente quem mais precisa dele.

Com vários monitores, cada tela recebe uma cobertura: deixar uma livre
convidaria a continuar trabalhando nela e a pausa não aconteceria.

Sobre o "sempre por cima": `WindowStaysOnTopHint` só é respeitado no X11 — no
Wayland o cliente não escolhe a ordem das janelas (mesma restrição registrada
no plano 14). O que funciona nos dois é a tela cheia com foco, então é nela que
a pausa se apoia; a dica de topo fica como reforço onde vale.

Sempre dá para sair: "Pular" encerra e "Adiar" empurra alguns minutos — um
lembrete que não se pode dispensar vira obstáculo, não ajuda.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from maestro_local.i18n import t

# Paleta fixa, escura, independente do tema do aplicativo.
#
# A tela seguia o tema e no tema claro ficava quase branca em tela cheia — o
# oposto do que a pausa quer: uma parede de luz nos olhos que se pretende
# descansar. Preto puro também não serve: o contraste extremo com o texto claro
# incomoda e o corte brusco ao aparecer assusta. Daí um cinza-azulado escuro.
FUNDO = "#12171F"
TITULO = "#2DD4BF"
TEXTO = "#94A3B8"
CONTADOR = "#E2E8F0"
BORDA = "#334155"
ACENTO = "#0D9488"
ACENTO_HOVER = "#0F766E"


class _Cobertura(QWidget):
    """Painel liso para os monitores secundários (sem contador nem botões)."""

    def __init__(self, tela, cor: str):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint
                         | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"_Cobertura {{ background: {cor}; }}")
        self.setScreen(tela)
        self.setGeometry(tela.geometry())


class EyecareBreak(QWidget):
    """Janela da pausa, com contagem regressiva. Emite o que o usuário escolheu.

    `parent` não é o pai visual (a janela é independente): serve só para saber
    em qual monitor o usuário está e para a janela não ser coletada enquanto
    aparece.
    """

    concluida = Signal()     # a pausa foi até o fim ou foi pulada
    adiada = Signal()        # empurrar para daqui a alguns minutos

    def __init__(self, parent, duracao_seg: int = 20):
        super().__init__(parent, Qt.Window | Qt.FramelessWindowHint
                         | Qt.WindowStaysOnTopHint)
        self._dono = parent
        self._coberturas: list[_Cobertura] = []
        self._restante = max(1, int(duracao_seg))
        self._cor_fundo = FUNDO
        self.setWindowTitle(t("Pausa para os olhos"))
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"EyecareBreak {{ background: {FUNDO}; }}"
            f"EyecareBreak QPushButton {{ background: {ACENTO}; color: #FFFFFF; "
            f"border: none; border-radius: 10px; padding: 10px 22px; "
            f"font-size: 13px; font-weight: 600; }}"
            f"EyecareBreak QPushButton:hover {{ background: {ACENTO_HOVER}; }}"
            f'EyecareBreak QPushButton[flat="true"] {{ background: transparent; '
            f"color: {TEXTO}; border: 1px solid {BORDA}; }}"
            f'EyecareBreak QPushButton[flat="true"]:hover {{ '
            f"background: rgba(255, 255, 255, 0.06); color: {CONTADOR}; }}"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setSpacing(18)
        lay.addStretch()

        titulo = QLabel(t("Pausa para os olhos"))
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet(
            f"color: {TITULO}; font-size: 26px; font-weight: 800; "
            f"background: transparent; border: none;")
        lay.addWidget(titulo)

        # Uma dica diferente a cada pausa. Uma frase fixa vira paisagem depois
        # de algumas repetições e a tela deixa de ensinar qualquer coisa.
        from maestro_local.eyecare import proxima_dica
        self.dica = QLabel(t(proxima_dica()))
        self.dica.setAlignment(Qt.AlignCenter)
        self.dica.setWordWrap(True)
        self.dica.setStyleSheet(
            f"color: {TEXTO}; font-size: 15px; line-height: 150%; "
            f"background: transparent; border: none;")
        lay.addWidget(self.dica, 0, Qt.AlignHCenter)
        self._largura_dica = 620

        self._contador = QLabel("")
        self._contador.setAlignment(Qt.AlignCenter)
        self._contador.setStyleSheet(
            f"color: {CONTADOR}; font-size: 46px; font-weight: 800; "
            f"letter-spacing: 2px; background: transparent; border: none;")
        lay.addWidget(self._contador)

        acoes = QHBoxLayout()
        acoes.setSpacing(10)
        acoes.addStretch()
        self.btn_adiar = QPushButton(t("Adiar"))
        self.btn_adiar.setProperty("flat", "true")
        self.btn_adiar.setCursor(Qt.PointingHandCursor)
        self.btn_adiar.clicked.connect(self._on_adiar)
        acoes.addWidget(self.btn_adiar)
        self.btn_pular = QPushButton(t("Pular"))
        self.btn_pular.setCursor(Qt.PointingHandCursor)
        self.btn_pular.clicked.connect(self._on_pular)
        acoes.addWidget(self.btn_pular)
        acoes.addStretch()
        lay.addLayout(acoes)
        lay.addStretch()

        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)
        self._atualizar_contador()

    # ------------------------------------------------------------------
    def _tela_do_usuario(self):
        """O monitor onde o Maestro está — não necessariamente o primário."""
        dono = self._dono
        if dono is not None:
            tela = dono.screen()
            if tela is not None:
                return tela
        return QGuiApplication.primaryScreen()

    def iniciar(self):
        principal = self._tela_do_usuario()
        for tela in QGuiApplication.screens():
            if tela is principal:
                continue
            cobertura = _Cobertura(tela, self._cor_fundo)
            cobertura.showFullScreen()
            self._coberturas.append(cobertura)

        if principal is not None:
            self.setScreen(principal)
            self.setGeometry(principal.geometry())
        self._ajustar_dica(principal)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.btn_pular.setFocus()
        self._tick.start()

    def _ajustar_dica(self, tela):
        """Fixa a largura da dica e reserva a altura que o texto quebrado ocupa.

        Um QLabel com wordWrap não informa ao layout a altura que vai precisar:
        o layout pergunta a altura para a largura natural, e o texto sai cortado
        na última linha. Com a largura fixada dá para perguntar direto ao
        heightForWidth.

        A linha também não pode ser larga demais: percorrer uma linha longa em
        tela cheia cansa justamente o olho que a pausa quer descansar.
        """
        disponivel = tela.geometry().width() if tela is not None else 800
        largura = max(280, min(self._largura_dica, disponivel - 80))
        self.dica.setFixedWidth(largura)
        self.dica.setMinimumHeight(self.dica.heightForWidth(largura))

    def keyPressEvent(self, event):
        # Esc adia em vez de fechar sem mais: uma janela em tela cheia que some
        # sem consequência ensina a dispensá-la por reflexo.
        if event.key() == Qt.Key_Escape:
            self._on_adiar()
            return
        super().keyPressEvent(event)

    def _atualizar_contador(self):
        self._contador.setText(t("{s}s").format(s=self._restante))

    def _on_tick(self):
        self._restante -= 1
        if self._restante <= 0:
            self._encerrar()
            self.concluida.emit()
            return
        self._atualizar_contador()

    def _on_pular(self):
        # Pular conta como pausa feita: o ciclo reinicia em vez de insistir.
        self._encerrar()
        self.concluida.emit()

    def _on_adiar(self):
        self._encerrar()
        self.adiada.emit()

    def _encerrar(self):
        self._tick.stop()
        for cobertura in self._coberturas:
            cobertura.hide()
            cobertura.deleteLater()
        self._coberturas.clear()
        self.hide()
        self.deleteLater()

    def segundos_restantes(self) -> int:
        return self._restante
