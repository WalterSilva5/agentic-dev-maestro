from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from maestro_local.gui.theme import current_theme

SECTIONS = [
    {
        "icon": "1",
        "title": "Crie um projeto",
        "body": (
            "Acesse a aba Projetos e crie um novo projeto com nome e chave (ex: MEU-PROJ). "
            "O board sera criado automaticamente com as colunas: "
            "Backlog, A fazer, Fazendo, Revisao e Concluido."
        ),
    },
    {
        "icon": "2",
        "title": "Adicione tarefas ao board",
        "body": (
            "No Board, use o campo de texto na parte inferior de cada coluna para criar "
            "tarefas rapidamente. Clique em uma tarefa para abrir o detalhe e preencher "
            "descricao, prioridade, tipo, checklist e labels."
        ),
    },
    {
        "icon": "3",
        "title": "Instale skills no seu projeto",
        "body": (
            "Acesse a aba Skills, selecione o diretorio do seu projeto e instale as skills "
            "desejadas. Elas serao salvas em .claude/skills/ e ensinam agentes de IA a "
            "interagir com o Maestro via API."
        ),
    },
    {
        "icon": "4",
        "title": "Agentes trabalham via API",
        "body": (
            "Com as skills instaladas, agentes de IA (como o Claude Code) podem:\n"
            "- Listar e pegar tarefas do backlog\n"
            "- Mover tarefas entre colunas\n"
            "- Registrar progresso com comentarios\n"
            "- Criar code reviews antes de enviar para revisao\n\n"
            "A API roda em http://127.0.0.1:9777/api enquanto o app estiver aberto."
        ),
    },
    {
        "icon": "5",
        "title": "Fluxo de trabalho com agentes",
        "body": (
            "O fluxo padrao e:\n"
            "1. Agente pega uma tarefa do Backlog ou A fazer\n"
            "2. Move para Fazendo e implementa o codigo\n"
            "3. Documenta o progresso com comentarios\n"
            "4. Cria um Code Review detalhado\n"
            "5. Move para Revisao (exige code review)\n"
            "6. Informa o desenvolvedor sobre o que foi feito\n"
            "7. O desenvolvedor revisa, testa, faz commit e push\n\n"
            "IMPORTANTE: Agentes nunca fazem commits ou pushs. "
            "Essa responsabilidade e exclusiva do desenvolvedor."
        ),
    },
    {
        "icon": "6",
        "title": "Tarefas exclusivas de desenvolvedor",
        "body": (
            "Marque tarefas como 'Requer desenvolvedor' no detalhe da tarefa. "
            "Essas tarefas aparecem com badge DEV no board e sao ignoradas "
            "automaticamente pelos agentes."
        ),
    },
    {
        "icon": "7",
        "title": "Acompanhe metricas",
        "body": (
            "A aba Metricas mostra:\n"
            "- Total de tarefas e progresso\n"
            "- Throughput semanal (tarefas concluidas por semana)\n"
            "- Lead time e cycle time medios\n"
            "- Distribuicao por tipo e prioridade\n"
            "- Alertas de tarefas com prazo vencido"
        ),
    },
    {
        "icon": "?",
        "title": "Atalhos de teclado",
        "body": (
            "- Ctrl+K — Busca global de tarefas\n"
            "- Alt+1 — Board\n"
            "- Alt+2 — Projetos\n"
            "- Alt+3 — Labels\n"
            "- Alt+4 — Metricas\n"
            "- Alt+5 — Skills\n"
            "- Alt+6 — Instrucoes (esta tela)\n"
            "- Escape — Fechar busca"
        ),
    },
]


class GuideView(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        title = QLabel("Como usar o Agentic Dev Maestro")
        title.setObjectName("sectionTitle")
        main_layout.addWidget(title)

        subtitle = QLabel(
            "Gerencie tarefas com um board kanban e deixe agentes de IA "
            "ajudarem no desenvolvimento via API REST."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("subtitle")
        main_layout.addWidget(subtitle)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)

        self.scroll.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll, 1)

        self._build_cards()

    def _build_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        t = current_theme()
        for section in SECTIONS:
            card = QFrame()
            card.setProperty("class", "card")

            row = QHBoxLayout(card)
            row.setContentsMargins(10, 8, 10, 8)
            row.setSpacing(14)

            badge = QLabel(section["icon"])
            badge.setFixedSize(36, 36)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(
                f"background: {t.accent}; color: {t.text_on_accent}; "
                f"border-radius: 18px; font-size: 15px; font-weight: 800; border: none;"
            )
            row.addWidget(badge, 0, Qt.AlignTop)

            text_col = QVBoxLayout()
            text_col.setSpacing(4)

            heading = QLabel(section["title"])
            heading.setProperty("class", "cardTitle")
            text_col.addWidget(heading)

            body = QLabel(section["body"])
            body.setWordWrap(True)
            body.setProperty("class", "hint")
            text_col.addWidget(body)

            row.addLayout(text_col, 1)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def refresh(self):
        self._build_cards()
