"""Componentes da tela de Reuniões.

Cada widget aqui é responsável por montar e expor um bloco da tela; as regras
de negócio (IA, persistência, gravação) ficam na view/serviços. Os widgets
filhos são expostos como atributos para que a view continue acessando-os
diretamente durante a migração incremental.
"""
from maestro_local.gui.meetings.destination_bar import DestinationBar
from maestro_local.gui.meetings.history_panel import HistoryPanel

__all__ = ["DestinationBar", "HistoryPanel"]
