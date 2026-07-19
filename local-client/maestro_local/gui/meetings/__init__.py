"""Componentes da tela de Reuniões.

Cada widget aqui é responsável por montar e expor um bloco da tela; as regras
de negócio (IA, persistência, gravação) ficam na view/serviços. Os widgets
filhos são expostos como atributos para que a view continue acessando-os
diretamente durante a migração incremental.
"""
from maestro_local.gui.meetings.destination_bar import DestinationBar
from maestro_local.gui.meetings.history_panel import HistoryPanel
from maestro_local.gui.meetings.live_panel import LiveAssistantPanel
from maestro_local.gui.meetings.preparation_card import PreparationCard
from maestro_local.gui.meetings.recording_card import RecordingCard
from maestro_local.gui.meetings.result_card import ResultCard
from maestro_local.gui.meetings.section_card import SectionCard

__all__ = [
    "DestinationBar",
    "HistoryPanel",
    "LiveAssistantPanel",
    "PreparationCard",
    "RecordingCard",
    "ResultCard",
    "SectionCard",
]
