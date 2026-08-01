"""Confirmação antes de enviar dados do seu trabalho ao assistente da reunião.

O nome do workspace, o projeto e as tarefas em aberto são informação do seu
trabalho. Mandar isso para o provedor de IA é uma decisão do usuário, não um
padrão silencioso — por isso a pergunta é feita ao começar a gravar, dizendo
exatamente o que seria enviado.
"""
from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from maestro_local.i18n import t


def confirm_share_context(parent, workspace: str = "", projeto: str = "",
                          n_tarefas: int = 0) -> bool:
    """Pergunta se o contexto do workspace/projeto vai junto. True = incluir."""
    itens = []
    if workspace:
        itens.append(t("• Workspace: {name}").format(name=workspace))
    if projeto:
        itens.append(t("• Projeto: {name} (nome e descrição)").format(name=projeto))
    if n_tarefas:
        itens.append(t("• {n} tarefa(s) em aberto do projeto").format(n=n_tarefas))

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Question)
    box.setWindowTitle(t("Incluir contexto do projeto?"))
    box.setText(t("Enviar dados do seu trabalho ao assistente desta reunião?"))
    box.setInformativeText(
        t("Seriam enviados ao provedor de IA:\n{itens}\n\n"
          "Isso ajuda o assistente a alinhar plano e ações ao seu trabalho. "
          "Sem isso, ele usa apenas a preparação, os anexos e a transcrição "
          "da própria reunião.").format(itens="\n".join(itens))
    )
    incluir = box.addButton(t("Incluir"), QMessageBox.AcceptRole)
    nao = box.addButton(t("Não incluir"), QMessageBox.RejectRole)
    # Pré-seleciona NÃO incluir: enviar dados do trabalho é o caminho que
    # merece uma escolha deliberada, não o que acontece ao apertar Enter.
    box.setDefaultButton(nao)
    box.exec()
    return box.clickedButton() is incluir
