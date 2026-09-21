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

A lista de pendências entra como leitura: a pausa também é um bom momento para
reencontrar o que ficou em aberto sem trocar de tela. Marcar como concluído,
não — isso convidaria a continuar trabalhando em plena pausa.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
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
PERIGO = "#F87171"   # pendência urgente
ALERTA = "#FBBF24"   # pendência de prioridade alta

# Modo hora de dormir: fundo vermelho, texto grande. Vermelho escuro em vez do
# puro (#DC2626): em tela cheia o tom saturado ofusca, e a tela já chega tarde
# da noite, quando a vista está cansada.
DORMIR_FUNDO = "#B91C1C"
DORMIR_FUNDO_HOVER = "#991B1B"
DORMIR_TITULO = "#FFFFFF"
DORMIR_TEXTO = "#FECACA"
# Segundos mínimos antes de liberar "Pular"/"Adiar" no modo dormir.
DORMIR_BLOQUEIO_SEG = 5


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

    def __init__(self, parent, duracao_seg: int = 20, dormir: bool = False):
        super().__init__(parent, Qt.Window | Qt.FramelessWindowHint
                         | Qt.WindowStaysOnTopHint)
        self._dono = parent
        self._coberturas: list[_Cobertura] = []
        self._restante = max(1, int(duracao_seg))
        self._dormir = bool(dormir)
        # No modo dormir nada dispensa antes de alguns segundos: um lembrete de
        # dormir que se pula por reflexo não serve para nada.
        self._bloqueio_seg = DORMIR_BLOQUEIO_SEG if self._dormir else 0
        self._cor_fundo = DORMIR_FUNDO if self._dormir else FUNDO
        self.setWindowTitle(t("Hora de dormir") if self._dormir
                            else t("Pausa para os olhos"))
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(self._folha())

        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setSpacing(18)
        lay.addStretch()

        self.titulo = QLabel(t("HORA DE DORMIR") if self._dormir
                             else t("Pausa para os olhos"))
        self.titulo.setAlignment(Qt.AlignCenter)
        self.titulo.setWordWrap(True)
        self.titulo.setStyleSheet(
            f"color: {DORMIR_TITULO if self._dormir else TITULO}; "
            f"font-size: {58 if self._dormir else 26}px; font-weight: 800; "
            f"letter-spacing: 2px; background: transparent; border: none;")
        lay.addWidget(self.titulo)

        # Uma dica diferente a cada pausa. Uma frase fixa vira paisagem depois
        # de algumas repetições e a tela deixa de ensinar qualquer coisa.
        if self._dormir:
            self.dica = QLabel(t("Salve o trabalho, desligue as telas e vá "
                                 "descansar. O corpo agradece."))
        else:
            from maestro_local.eyecare import proxima_dica
            self.dica = QLabel(t(proxima_dica()))
        self.dica.setAlignment(Qt.AlignCenter)
        self.dica.setWordWrap(True)
        self.dica.setStyleSheet(
            f"color: {DORMIR_TEXTO if self._dormir else TEXTO}; font-size: 15px; "
            f"line-height: 150%; background: transparent; border: none;")
        lay.addWidget(self.dica, 0, Qt.AlignHCenter)
        self._largura_dica = 620

        self._contador = QLabel("")
        self._contador.setAlignment(Qt.AlignCenter)
        self._contador.setStyleSheet(
            f"color: {DORMIR_TITULO if self._dormir else CONTADOR}; "
            f"font-size: 46px; font-weight: 800; "
            f"letter-spacing: 2px; background: transparent; border: none;")
        lay.addWidget(self._contador)

        # Aviso do bloqueio de saída (só no modo dormir).
        self._aviso = QLabel("")
        self._aviso.setAlignment(Qt.AlignCenter)
        self._aviso.setStyleSheet(
            f"color: {DORMIR_TEXTO}; font-size: 13px; font-weight: 600; "
            f"background: transparent; border: none;")
        lay.addWidget(self._aviso)

        # Pendências em aberto: a pausa já tem a atenção de quem está diante da
        # tela, então é um bom lugar para a lista sem tirar o foco do descanso.
        # No modo dormir, não: a lista convidaria a continuar trabalhando.
        self.pendencias = None if self._dormir else self._montar_pendencias()
        if self.pendencias is not None:
            linha = QHBoxLayout()
            linha.addStretch()
            linha.addWidget(self.pendencias)
            linha.addStretch()
            lay.addLayout(linha)

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

        if self._bloqueado():
            self.btn_adiar.setEnabled(False)
            self.btn_pular.setEnabled(False)
            self._atualizar_aviso()

        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)
        self._atualizar_contador()

    # ------------------------------------------------------------------
    def _folha(self) -> str:
        """QSS da janela: paleta normal ou a vermelha do modo dormir."""
        if self._dormir:
            return (
                f"EyecareBreak {{ background: {DORMIR_FUNDO}; }}"
                f"EyecareBreak QPushButton {{ background: #FFFFFF; "
                f"color: {DORMIR_FUNDO}; border: none; border-radius: 10px; "
                f"padding: 10px 22px; font-size: 13px; font-weight: 700; }}"
                f"EyecareBreak QPushButton:hover {{ background: {DORMIR_TEXTO}; }}"
                f"EyecareBreak QPushButton:disabled {{ "
                f"background: rgba(255, 255, 255, 0.22); "
                f"color: rgba(255, 255, 255, 0.55); }}"
                f'EyecareBreak QPushButton[flat="true"] {{ background: transparent; '
                f"color: {DORMIR_TEXTO}; border: 1px solid rgba(255,255,255,0.55); }}"
                f'EyecareBreak QPushButton[flat="true"]:hover {{ '
                f"background: rgba(255, 255, 255, 0.12); }}"
            )
        return (
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

    def _bloqueado(self) -> bool:
        """Ainda não dá para sair? (só acontece no modo dormir)"""
        return self._dormir and self._bloqueio_seg > 0

    def _atualizar_aviso(self):
        self._aviso.setText(
            t("Você poderá pular em {s}s").format(s=self._bloqueio_seg)
            if self._bloqueado() else "")

    def _liberar(self):
        self.btn_adiar.setEnabled(True)
        self.btn_pular.setEnabled(True)
        self._aviso.setText("")
        self.btn_pular.setFocus()

    def _montar_pendencias(self):
        """Lista das pendências em aberto, ou None quando não há nenhuma.

        Só de leitura de propósito: concluir aqui convidaria a continuar
        trabalhando, e a pausa deixaria de acontecer. Concluir segue na tela
        de TODOs.
        """
        try:
            from maestro_local.todos import todos_abertos
            self._todos = todos_abertos(limite=20)
        except Exception:  # noqa: BLE001 - a pausa não pode falhar por causa da lista
            self._todos = []
        if not self._todos:
            return None

        caixa = QFrame()
        caixa.setObjectName("eyecarePendencias")
        caixa.setStyleSheet(
            f"#eyecarePendencias {{ background: transparent; "
            f"border: 1px solid {BORDA}; border-radius: 12px; }}")
        col = QVBoxLayout(caixa)
        col.setContentsMargins(18, 12, 18, 12)
        col.setSpacing(8)

        titulo = QLabel(t("Pendências ({n})").format(n=len(self._todos)))
        titulo.setStyleSheet(
            f"color: {TITULO}; font-size: 13px; font-weight: 700; "
            f"background: transparent; border: none;")
        col.addWidget(titulo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(200)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }")
        cont = QWidget()
        lista = QVBoxLayout(cont)
        lista.setContentsMargins(0, 0, 0, 0)
        lista.setSpacing(4)
        for td in self._todos:
            lista.addWidget(self._linha_pendencia(td))
        lista.addStretch()
        scroll.setWidget(cont)
        col.addWidget(scroll)
        return caixa

    def _linha_pendencia(self, td: dict) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        marca = QLabel("•")
        marca.setStyleSheet(
            f"color: {TITULO}; font-size: 13px; background: transparent; border: none;")
        row.addWidget(marca)

        texto = QLabel(td["text"])
        texto.setWordWrap(True)
        texto.setStyleSheet(
            f"color: {TEXTO}; font-size: 12px; background: transparent; border: none;")
        row.addWidget(texto, 1)

        if td.get("priority") in ("URGENT", "HIGH"):
            urgente = td["priority"] == "URGENT"
            tag = QLabel(t("urgente") if urgente else t("alta"))
            tag.setStyleSheet(
                f"color: {PERIGO if urgente else ALERTA}; font-size: 10px; "
                f"font-weight: 700; background: transparent; border: none;")
            row.addWidget(tag)

        if td.get("due_at"):
            venc = QLabel(td["due_at"].strftime("%d/%m"))
            venc.setStyleSheet(
                f"color: {TEXTO}; font-size: 10px; background: transparent; border: none;")
            row.addWidget(venc)
        return w

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
        if not self._bloqueado():
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
        if self.pendencias is not None:
            self.pendencias.setFixedWidth(largura)

    def keyPressEvent(self, event):
        # Esc adia em vez de fechar sem mais: uma janela em tela cheia que some
        # sem consequência ensina a dispensá-la por reflexo.
        if event.key() == Qt.Key_Escape:
            if self._bloqueado():
                return       # no modo dormir, Esc também espera o bloqueio
            self._on_adiar()
            return
        super().keyPressEvent(event)

    def _atualizar_contador(self):
        self._contador.setText(t("{s}s").format(s=self._restante))

    def _on_tick(self):
        self._restante -= 1
        if self._bloqueio_seg > 0:
            self._bloqueio_seg -= 1
            if self._bloqueio_seg <= 0:
                self._liberar()
            else:
                self._atualizar_aviso()
        if self._restante <= 0:
            self._encerrar()
            self.concluida.emit()
            return
        self._atualizar_contador()

    def _on_pular(self):
        if self._bloqueado():
            return
        # Pular conta como pausa feita: o ciclo reinicia em vez de insistir.
        self._encerrar()
        self.concluida.emit()

    def _on_adiar(self):
        if self._bloqueado():
            return
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
