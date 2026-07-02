"""Gera os screenshots (tema claro) da documentação a partir do workspace demo.

Uso:
    QT_QPA_PLATFORM=offscreen python -m scripts.gen_screenshots
    (ou)  QT_QPA_PLATFORM=offscreen python scripts/gen_screenshots.py

Usa o workspace "wsi" (projeto demo MST "Maestro App"), semeia dados das
funcionalidades novas (sprints + plano de estudo) de forma idempotente, aplica
o tema claro e captura cada tela para local-client/docs/screenshots/*-light.png.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WS_ID = "wsi"
OUT = ROOT / "docs" / "screenshots"
SIZE = (1040, 760)


def seed_demo(session, models):
    """Garante sprints e um plano de estudo no projeto demo (idempotente)."""
    Project = models.Project
    Sprint = models.Sprint
    Task = models.Task
    StudyPlan = models.StudyPlan
    StudyTopic = models.StudyTopic

    p = session.query(Project).filter(Project.key == "MST").first()
    if not p:
        return
    # Sprints
    if not session.query(Sprint).filter(Sprint.project_id == p.id).count():
        s1 = Sprint(project_id=p.id, name="Sprint 1 — MVP", goal="Fluxo principal do board",
                    status="ATIVA", capacity=12.0, sort_order=0)
        s2 = Sprint(project_id=p.id, name="Sprint 2 — Beta", goal="Métricas e polimento",
                    status="PLANEJADA", capacity=15.0, sort_order=1)
        session.add_all([s1, s2])
        session.flush()
        tasks = session.query(Task).filter(Task.project_id == p.id, Task.deleted_at.is_(None)).order_by(Task.number).all()
        for i, tk in enumerate(tasks):
            tk.estimate_md = tk.estimate_md or float(1 + (i % 3))
            # 2 primeiras no backlog; restantes na sprint ativa
            tk.sprint_id = None if i < 2 else s1.id
        session.commit()
    # Plano de estudo
    if not session.query(StudyPlan).count():
        plan = StudyPlan(title="Aprender Rust", category="LINGUAGEM",
                         description="Do ownership ao async, com prática.")
        session.add(plan)
        session.flush()
        topics = [
            ("Ownership e Borrowing", "CONCLUIDO", 4),
            ("Lifetimes", "ESTUDANDO", 3),
            ("Traits e Generics", "PENDENTE", 5),
            ("Concorrência com threads", "PENDENTE", 4),
            ("async/await", "PENDENTE", 6),
        ]
        for i, (t, st, h) in enumerate(topics):
            session.add(StudyTopic(plan_id=plan.id, title=t, status=st, sort_order=i,
                                   weight=1.0, estimate_hours=float(h)))
        session.commit()


def grab(win, app, name):
    app.processEvents()
    app.processEvents()
    OUT.mkdir(parents=True, exist_ok=True)
    win.grab().save(str(OUT / f"{name}.png"))
    print("saved", name)


def main():
    from maestro_local import config
    from maestro_local.db import models

    original_ws = config.get_active_workspace_id()
    config.set_active_workspace(WS_ID)
    db_path = config.get_workspace_db_path(WS_ID)
    models.switch_db(db_path)
    models.init_db(db_path)

    s = models.get_session()
    try:
        seed_demo(s, models)
    finally:
        s.close()

    from PySide6.QtWidgets import QApplication

    from maestro_local.gui.theme import LIGHT, build_stylesheet, set_theme

    app = QApplication.instance() or QApplication([])
    set_theme(LIGHT)
    app.setStyleSheet(build_stylesheet(LIGHT))

    from maestro_local.gui.main_window import MainWindow

    win = MainWindow(api_port=9777)
    win.resize(*SIZE)
    win.show()
    app.processEvents()

    nav = win.nav_list

    def go(row):
        nav.setCurrentRow(row)
        app.processEvents()
        w = win.stack.currentWidget()
        if hasattr(w, "refresh"):
            try:
                w.refresh()
            except Exception:  # noqa: BLE001
                pass
        app.processEvents()

    # Dashboard, Meu Dia
    go(0); grab(win, app, "dashboard-light")
    go(1); grab(win, app, "meudia-light")

    # Estudos — abre o primeiro plano para mostrar o assistente
    go(2)
    try:
        plan = models.get_session()
        p = plan.query(models.StudyPlan).first()
        pid = p.id if p else None
        plan.close()
        if pid:
            win.study_view._open_plan(pid)
            app.processEvents()
    except Exception:  # noqa: BLE001
        pass
    grab(win, app, "estudos-light")

    # Board (aba de fluxo) + Planejamento de Sprints — abre o projeto demo
    go(3)
    try:
        bs = models.get_session()
        mst = bs.query(models.Project).filter(models.Project.key == "MST").first()
        mst_id = mst.id if mst else None
        bs.close()
        if mst_id:
            win.board_view.set_project(mst_id)
            app.processEvents()
    except Exception:  # noqa: BLE001
        pass
    win.board_view.tabs.setCurrentIndex(0)
    grab(win, app, "board-light")
    win.board_view.tabs.setCurrentIndex(1)
    app.processEvents()
    grab(win, app, "planejamento-light")
    win.board_view.tabs.setCurrentIndex(0)

    # Assistente (chat)
    go(4); grab(win, app, "chat-light")

    # Reuniões — mostra o painel ao vivo (copiloto) populado
    go(5)
    tv = win.transcricoes_view
    tv.live_box.setVisible(True)
    tv._live_state = {
        "action_items": [{"description": "Ajustar validação do CSV", "assignee": "Ana"}],
        "decisions": ["Adotar dark mode no dashboard"],
        "open_questions": ["Qual limite de linhas na exportação?"],
        "plan": ["Levantar requisitos", "Prototipar UI", "Implementar e testar"],
        "tips": ["Validar acessibilidade do tema", "Cobrir exportação com testes"],
    }
    tv._refresh_live_panels()
    grab(win, app, "reunioes-light")

    # Projetos, Skills, Instruções, Configurações
    go(6); grab(win, app, "projetos-light")
    go(7); grab(win, app, "skills-light")
    go(8); grab(win, app, "instrucoes-light")
    go(9); grab(win, app, "configuracoes-light")

    config.set_active_workspace(original_ws)
    print("Workspace ativo restaurado para:", original_ws)


if __name__ == "__main__":
    main()
