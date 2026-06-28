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
        "icon": "🎯",
        "title": "O papel dos agentes",
        "body": (
            "Agentes de IA são auxiliares dos desenvolvedores. "
            "Ajudam a acelerar o trabalho repetitivo, documentar "
            "progresso e preparar código para revisão humana.\n\n"
            "O que agentes fazem:\n"
            "- Auxiliam na implementação de tarefas\n"
            "- Documentam progresso com comentários estruturados\n"
            "- Criam code reviews detalhados\n"
            "- Criam tarefas de revisão para o desenvolvedor validar\n"
            "- Geram relatórios e resumos do dia\n\n"
            "O que agentes NUNCA fazem:\n"
            "- Commits ou pushs (responsabilidade exclusiva do dev)\n"
            "- Tocar em tarefas marcadas como 'Requer desenvolvedor'\n"
            "- Tomar decisões de arquitetura sem consultar o dev"
        ),
    },
    {
        "icon": "1",
        "title": "Crie um projeto",
        "body": (
            "Acesse a aba Projetos e crie um novo projeto com nome e chave (ex: MEU-PROJ). "
            "O board será criado automaticamente com as colunas: "
            "Backlog, A fazer, Fazendo, Revisão e Concluído."
        ),
    },
    {
        "icon": "2",
        "title": "Adicione tarefas ao board",
        "body": (
            "No Board, use o campo de texto na parte inferior de cada coluna para criar "
            "tarefas rapidamente. Clique em uma tarefa para abrir o detalhe e preencher "
            "descrição, prioridade, tipo, checklist e labels."
        ),
    },
    {
        "icon": "3",
        "title": "Instale skills no seu projeto",
        "body": (
            "Acesse a aba Skills, selecione o diretório do seu projeto e instale as skills "
            "desejadas. Elas serão salvas em .claude/skills/ e ensinam agentes de IA a "
            "interagir com o Maestro via API.\n\n"
            "As skills orientam os agentes sobre como usar a API, seguir o fluxo de "
            "trabalho, criar tarefas de revisão e respeitar as regras do projeto."
        ),
    },
    {
        "icon": "4",
        "title": "Fluxo de trabalho: dev + agente",
        "body": (
            "O desenvolvedor lidera, o agente auxilia:\n\n"
            "1. Dev cria tarefas no board com descrição e critérios\n"
            "2. Agente pega uma tarefa e move para Fazendo\n"
            "3. Agente auxilia na implementação e documenta progresso\n"
            "4. Agente cria Code Review detalhado na tarefa\n"
            "5. Agente SEMPRE cria uma tarefa de revisão para o dev\n"
            "6. Agente move para Revisão (exige code review)\n"
            "7. Dev revisa as alterações, testa e faz commit/push\n"
            "8. Dev move para Concluído após validar\n\n"
            "A tarefa de revisão garante que o desenvolvedor sempre "
            "valide o trabalho do agente antes de ir para produção."
        ),
    },
    {
        "icon": "5",
        "title": "Tarefas de revisão",
        "body": (
            "Ao concluir qualquer implementação, o agente DEVE criar uma tarefa "
            "de revisão para o desenvolvedor. Essa tarefa inclui:\n"
            "- Resumo do que foi feito\n"
            "- Arquivos alterados\n"
            "- O que testar\n"
            "- Pontos de atenção\n\n"
            "Isso cria um histórico estruturado de revisões que serve como "
            "contexto para futuras sessões e garante qualidade no código."
        ),
    },
    {
        "icon": "6",
        "title": "Tarefas exclusivas de desenvolvedor",
        "body": (
            "Marque tarefas como 'Requer desenvolvedor' no detalhe da tarefa. "
            "Essas tarefas aparecem com badge DEV no board e são ignoradas "
            "automaticamente pelos agentes. Use para tarefas que exigem "
            "decisão humana, acesso a sistemas externos ou revisão crítica."
        ),
    },
    {
        "icon": "7",
        "title": "Acompanhe métricas",
        "body": (
            "A aba Métricas mostra:\n"
            "- Total de tarefas e progresso\n"
            "- Throughput semanal (tarefas concluídas por semana)\n"
            "- Lead time e cycle time médios\n"
            "- Distribuição por tipo e prioridade\n"
            "- Alertas de tarefas com prazo vencido"
        ),
    },
    {
        "icon": "8",
        "title": "Meu Dia e relatórios",
        "body": (
            "A tela Meu Dia é o ponto central do dia de trabalho:\n"
            "- Notas do dia com template de foco, tarefas e bloqueios\n"
            "- Geração de relatório com resumo de atividades\n"
            "- Dica IA com prompt para o agente gerar o resumo\n"
            "- Timeline de atividade do dia\n"
            "- Sincronização com vault do Obsidian"
        ),
    },
    {
        "icon": "9",
        "title": "Chat estratégico",
        "body": (
            "O Chat estratégico é um assistente de IA interno que roda com seu "
            "próprio provedor (LM Studio local, opencode, etc.). Diferente dos "
            "agentes externos, ele age dentro da aplicação:\n"
            "- Lê o board e resume o estado do trabalho\n"
            "- Sugere prioridades para o dia\n"
            "- Solicita revisões de tarefas (cria tarefa requer-dev)\n"
            "- Cria TODOs e comenta tarefas\n\n"
            "Configure o provedor em Configurações → Provedores de IA. "
            "É necessário definir a Base URL e o Modelo; a API Key fica em "
            "branco para provedores locais."
        ),
    },
    {
        "icon": "10",
        "title": "Cronista (gravações)",
        "body": (
            "O Cronista grava reuniões e sessões de estudo, transcreve localmente "
            "com Whisper e gera resumos estruturados com IA:\n"
            "- Captura microfone e/ou áudio do sistema (PipeWire/PulseAudio)\n"
            "- Transcrição offline com faster-whisper (modelo configurável)\n"
            "- Resumo de reunião: pontos-chave, decisões, ações\n"
            "- Resumo de estudo: conceitos, exercícios, tópicos relacionados\n"
            "- Histórico pesquisável e botão 'Salvar no Meu Dia'\n\n"
            "Atalho global Ctrl+Shift+R inicia/para a gravação. O modelo do "
            "Whisper é configurável em Configurações → Cronista."
        ),
    },
    {
        "icon": "?",
        "title": "Atalhos de teclado",
        "body": (
            "- Ctrl+K — Busca global de tarefas\n"
            "- Alt+1 — Dashboard\n"
            "- Alt+2 — Meu Dia\n"
            "- Alt+3 — TODOs\n"
            "- Alt+4 — Estudos\n"
            "- Alt+5 — Board\n"
            "- Alt+6 — Chat estratégico\n"
            "- Alt+7 — Cronista\n"
            "- Alt+8 — Projetos\n"
            "- Alt+9 — Labels\n"
            "- Alt+0 — Métricas\n"
            "- Ctrl+Shift+R — Iniciar/parar gravação (global)\n"
            "- Skills, Instruções e Configurações — pela barra lateral\n"
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
            "Gerencie tarefas com um board kanban e use agentes de IA como "
            "auxiliares dos desenvolvedores — eles ajudam a implementar, "
            "documentar e preparar código para revisão humana via API REST."
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
