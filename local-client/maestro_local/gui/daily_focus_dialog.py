"""Modal de foco do dia — aparece uma vez por dia ao abrir o programa.

No topo, a mensagem de foco (configurável em Configurações; padrão
"FOCO NO OBJETIVO"). Abaixo, os TODOs em aberto, para o dia começar com a
lista à vista em vez de precisar procurá-la.

Os TODOs podem ser marcados como concluídos aqui mesmo — é o momento em que
se olha para eles, então obrigar a abrir outra tela só para isso seria atrito.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from maestro_local.db.models import Todo, get_session
from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t

_PRIORIDADE_ORDEM = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def todos_abertos(limite: int = 30) -> list[dict]:
    """TODOs não concluídos, os mais urgentes primeiro.

    Devolve dicts para o diálogo não segurar objetos da sessão.
    """
    s = get_session()
    try:
        itens = s.query(Todo).filter(Todo.done == False).all()  # noqa: E712
        itens.sort(key=lambda td: (
            _PRIORIDADE_ORDEM.get(td.priority or "MEDIUM", 2),
            td.due_at or datetime.max,
            td.sort_order or 0,
        ))
        return [{"id": td.id, "text": td.text, "priority": td.priority or "MEDIUM",
                 "due_at": td.due_at} for td in itens[:limite]]
    finally:
        s.close()


def marcar_concluido(todo_id: int) -> None:
    s = get_session()
    try:
        td = s.get(Todo, todo_id)
        if td is not None and not td.done:
            td.done = True
            td.completed_at = datetime.utcnow()
            s.commit()
    finally:
        s.close()


class DailyFocusDialog(QDialog):
    """Mensagem de foco + TODOs do dia."""

    def __init__(self, parent=None, mensagem: str = "", todos: list[dict] | None = None):
        super().__init__(parent)
        th = current_theme()
        self.setWindowTitle(t("Foco do dia"))
        self.setMinimumWidth(460)
        self._concluidos: set[int] = set()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(14)

        # Mensagem de foco — o motivo do modal existir, então domina o topo.
        self.msg_label = QLabel(mensagem or t("FOCO NO OBJETIVO"))
        self.msg_label.setWordWrap(True)
        self.msg_label.setAlignment(Qt.AlignCenter)
        self.msg_label.setStyleSheet(
            f"color: {th.accent}; font-size: 20px; font-weight: 800; "
            f"letter-spacing: 0.5px; background: transparent; border: none;")
        lay.addWidget(self.msg_label)

        linha = QFrame()
        linha.setFrameShape(QFrame.HLine)
        linha.setFixedHeight(1)
        linha.setStyleSheet(f"background: {th.border}; border: none;")
        lay.addWidget(linha)

        todos = todos or []
        titulo = QLabel(
            t("Suas pendências ({n})").format(n=len(todos)) if todos
            else t("Nenhuma pendência — dia limpo."))
        titulo.setObjectName("subtitle")
        lay.addWidget(titulo)

        if todos:
            lay.addWidget(self._lista(todos, th), 1)

        acoes = QHBoxLayout()
        acoes.addStretch()
        fechar = QPushButton(t("Começar o dia"))
        fechar.setCursor(Qt.PointingHandCursor)
        fechar.clicked.connect(self.accept)
        acoes.addWidget(fechar)
        lay.addLayout(acoes)

    # ------------------------------------------------------------------
    def _lista(self, todos: list[dict], th) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(300)

        cont = QWidget()
        col = QVBoxLayout(cont)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(4)
        for td in todos:
            col.addWidget(self._linha(td, th))
        col.addStretch()
        scroll.setWidget(cont)
        return scroll

    def _linha(self, td: dict, th) -> QWidget:
        w = QFrame()
        row = QHBoxLayout(w)
        row.setContentsMargins(2, 2, 2, 2)
        row.setSpacing(8)

        chk = QCheckBox(td["text"])
        chk.setToolTip(t("Marcar como concluído"))
        chk.toggled.connect(lambda on, i=td["id"], c=chk: self._on_check(on, i, c))
        row.addWidget(chk, 1)

        if td["priority"] in ("URGENT", "HIGH"):
            tag = QLabel(t("urgente") if td["priority"] == "URGENT" else t("alta"))
            cor = th.danger if td["priority"] == "URGENT" else th.warning
            tag.setStyleSheet(
                f"color: {cor}; font-size: 10px; font-weight: 700; "
                f"background: transparent; border: none;")
            row.addWidget(tag)

        if td["due_at"]:
            venc = QLabel(td["due_at"].strftime("%d/%m"))
            venc.setObjectName("subtitle")
            row.addWidget(venc)
        return w

    def _on_check(self, marcado: bool, todo_id: int, chk: QCheckBox) -> None:
        """Conclui na hora; desmarcar não reabre (evita alternar sem querer)."""
        if not marcado:
            return
        marcar_concluido(todo_id)
        self._concluidos.add(todo_id)
        chk.setEnabled(False)

    def concluidos(self) -> set[int]:
        return set(self._concluidos)
