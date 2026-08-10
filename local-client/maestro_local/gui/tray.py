"""Ícone na bandeja do sistema.

Serve para o que precisa de resposta rápida sem trazer a janela para a frente —
hoje, o controle da pausa para os olhos. Adiar uma pausa navegando até
Configurações é lento demais para o momento em que ela atrapalha.

O menu é remontado a cada abertura (`aboutToShow`): o horário da próxima pausa
e o estado de "adiada" mudam sozinhos com o tempo, e um menu montado uma vez só
mostraria informação velha.

Se a bandeja não estiver disponível (alguns ambientes sem StatusNotifierItem),
`instalar` devolve None e o resto do programa segue igual — a bandeja é um
atalho, nunca o único caminho para uma função.
"""
from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from maestro_local.i18n import t

TITULO = "Agentic Dev Maestro"


class MaestroTray(QSystemTrayIcon):
    def __init__(self, janela):
        super().__init__(janela)
        self._janela = janela
        self._menu = QMenu(janela)
        self._menu.aboutToShow.connect(self._remontar)
        self.setContextMenu(self._menu)
        self.setToolTip(TITULO)
        self.activated.connect(self._on_activated)
        self._remontar()

    # --- construção do menu ---

    def _remontar(self):
        from maestro_local import eyecare, features
        self._menu.clear()

        acao = QAction(t("Mostrar Maestro"), self._menu)
        acao.triggered.connect(self._mostrar_janela)
        self._menu.addAction(acao)
        self._menu.addSeparator()

        if features.habilitada("eyecare"):
            self._montar_eyecare(eyecare)
            self._menu.addSeparator()

        sair = QAction(t("Sair"), self._menu)
        sair.triggered.connect(self._janela.close)
        self._menu.addAction(sair)

    def _montar_eyecare(self, eyecare):
        c = eyecare.config()
        titulo = QAction(t("Pausa para os olhos"), self._menu)
        titulo.setEnabled(False)
        self._menu.addAction(titulo)

        # Enquanto uma reunião roda, a pausa está segura de qualquer jeito —
        # dizer "próxima às 14:05" ali seria mentira.
        if self._janela._em_reuniao():
            estado = t("Em pausa: reunião em andamento")
        else:
            estado = t("Próxima às {hora}").format(
                hora=eyecare.proxima_pausa().strftime("%H:%M"))
        info = QAction(f"   {estado}", self._menu)
        info.setEnabled(False)
        self._menu.addAction(info)

        agora = QAction(t("Fazer a pausa agora"), self._menu)
        agora.triggered.connect(self._janela.testar_eyecare)
        self._menu.addAction(agora)

        adiar = self._menu.addMenu(t("Adiar"))
        for minutos in (5, 15, 30, 60):
            a = QAction(t("{n} min").format(n=minutos), adiar)
            a.triggered.connect(lambda _=False, m=minutos: self._adiar(m))
            adiar.addAction(a)

        if c["adiada_ate"] is not None:
            retomar = QAction(t("Retomar agora (cancelar adiamento)"), self._menu)
            retomar.triggered.connect(self._retomar)
            self._menu.addAction(retomar)

    # --- ações ---

    def _mostrar_janela(self):
        self._janela.showNormal()
        self._janela.raise_()
        self._janela.activateWindow()

    def _on_activated(self, motivo):
        if motivo == QSystemTrayIcon.Trigger:
            self._mostrar_janela()

    def _adiar(self, minutos: int):
        from maestro_local import eyecare
        ate = eyecare.adiar(minutos)
        self._janela.show_toast(
            t("Pausa adiada para {hora}").format(hora=ate.strftime("%H:%M")))

    def _retomar(self):
        from maestro_local import eyecare
        eyecare.cancelar_adiamento()
        self._janela.show_toast(t("Adiamento cancelado."))


def instalar(janela) -> MaestroTray | None:
    """Cria o ícone da bandeja, ou None se o ambiente não tiver uma."""
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None
    from maestro_local.gui.icons import icone_do_app
    tray = MaestroTray(janela)
    tray.setIcon(icone_do_app())
    tray.show()
    return tray
