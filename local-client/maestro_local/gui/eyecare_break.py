"""Tela da pausa para os olhos.

Cobre a janela do Maestro com uma contagem regressiva, para o olhar sair da
tela de fato. Não cobre a área de trabalho inteira como o SafeEyes faz: no
Wayland um cliente não consegue se sobrepor às outras janelas de forma
portátil (mesma restrição registrada no plano 14 para o overlay do copiloto).
Então a pausa é firme dentro do aplicativo, e não uma barreira do sistema.

Sempre dá para sair: "Pular" encerra e "Adiar" empurra alguns minutos — um
lembrete que não se pode dispensar vira obstáculo, não ajuda.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t


class EyecareBreak(QWidget):
    """Sobreposição com contagem regressiva. Emite o que o usuário escolheu."""

    concluida = Signal()     # a pausa foi até o fim ou foi pulada
    adiada = Signal()        # empurrar para daqui a alguns minutos

    def __init__(self, parent, duracao_seg: int = 20):
        super().__init__(parent)
        self._restante = max(1, int(duracao_seg))
        th = current_theme()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"EyecareBreak {{ background: {th.bg_card}; }}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setSpacing(18)
        lay.addStretch()

        titulo = QLabel(t("Pausa para os olhos"))
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet(
            f"color: {th.accent}; font-size: 26px; font-weight: 800; "
            f"background: transparent; border: none;")
        lay.addWidget(titulo)

        instrucao = QLabel(t("Olhe para algo a uns 6 metros de distância e pisque algumas vezes."))
        instrucao.setAlignment(Qt.AlignCenter)
        instrucao.setWordWrap(True)
        instrucao.setStyleSheet(
            f"color: {th.text_secondary}; font-size: 14px; "
            f"background: transparent; border: none;")
        lay.addWidget(instrucao)

        self._contador = QLabel("")
        self._contador.setAlignment(Qt.AlignCenter)
        self._contador.setStyleSheet(
            f"color: {th.text_primary}; font-size: 46px; font-weight: 800; "
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
    def iniciar(self):
        pai = self.parent()
        if pai is not None:
            self.setGeometry(pai.rect())
        self.show()
        self.raise_()
        self._tick.start()

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
        self.hide()
        self.deleteLater()

    def segundos_restantes(self) -> int:
        return self._restante
