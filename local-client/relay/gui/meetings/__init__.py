"""Componentes da tela de Reuniões.

Cada widget aqui é responsável por montar e expor um bloco da tela; as regras
de negócio (IA, persistência, gravação) ficam na view/serviços. Os widgets
filhos são expostos como atributos para que a view continue acessando-os
diretamente durante a migração incremental.
"""
from relay.gui.meetings.destination_bar import DestinationBar
from relay.gui.meetings.flow_indicator import FlowIndicator
from relay.gui.meetings.history_panel import HistoryPanel
from relay.gui.meetings.live_panel import LiveAssistantPanel
from relay.gui.meetings.preparation_card import PreparationCard
from relay.gui.meetings.recording_card import RecordingCard
from relay.gui.meetings.result_card import ResultCard
from relay.gui.meetings.section_card import SectionCard

__all__ = [
    "DestinationBar",
    "FlowIndicator",
    "HistoryPanel",
    "LiveAssistantPanel",
    "PreparationCard",
    "RecordingCard",
    "ResultCard",
    "SectionCard",
]
