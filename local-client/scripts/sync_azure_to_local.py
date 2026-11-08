#!/usr/bin/env python3
"""Sincroniza Azure DevOps (somente leitura) -> Maestro local (escrita local).

Uso:
  az boards query ... -o json > /tmp/azure.json 2>/tmp/azure.err
  python3 local-client/scripts/sync_azure_to_local.py --project "VAR 3.0 - Migração GX" --local-project-key MIG --input /tmp/azure.json --dry-run
  python3 local-client/scripts/sync_azure_to_local.py --project "VAR 3.0 - Migração GX" --local-project-key MIG --input /tmp/azure.json
"""
import argparse, json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from maestro_local.db.models import BoardColumn, Label, Project, Task, get_session, get_or_create_member

from datetime import datetime


def _data_conclusao(fields: dict):
    """Data real de conclusão do work item (Azure), se o board informar."""
    for chave in ("Microsoft.VSTS.Common.ClosedDate",
                  "Microsoft.VSTS.Common.ResolvedDate",
                  "System.ChangedDate"):
        valor = fields.get(chave)
        if not valor:
            continue
        try:
            return datetime.fromisoformat(str(valor).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            continue
    return None
from maestro_local.config import get_active_workspace_id, get_workspace_db_path
from maestro_local.db.models import init_db

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="Nome do projeto no Azure")
    ap.add_argument("--local-project-key", default=None, help="Key do projeto local (se omitido, usa o Azure sanitizado)")
    ap.add_argument("--input", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.loads(Path(args.input).read_text())
    print(f"Azure: {len(data)} work items lidos de {args.input}")

    # garante DB local
    from maestro_local.config import get_active_workspace_id, get_workspace_db_path
    init_db(get_workspace_db_path(get_active_workspace_id()))

    key = args.local_project_key or "".join(c for c in args.project if c.isalnum())[:8].upper() or "GAVAR"
    s = get_session()
    try:
        proj = s.query(Project).filter(Project.key == key).first()
        if not proj:
            proj = s.query(Project).filter(Project.name == args.project).first()
        if not proj:
            print(f"Criando projeto local {key} - {args.project}")
            proj = Project(name=args.project, key=key)
            s.add(proj); s.flush()
            for i, (name, is_done) in enumerate([("To do", False), ("Doing", False), ("Done", True)]):
                s.add(BoardColumn(project_id=proj.id, name=name, order=i, is_done=is_done))
            s.commit()
        # garante colunas Azure se faltar, na ordem do template Azure (To do -> Done)
        template_order = ["To do","Approved","Refinement","Ready for Dev","Doing","Dev Box","Dev Review","In Test","Rework","Verified","Accepted","Done"]
        order_index = {n.lower(): i for i, n in enumerate(template_order)}
        col_by_name = {c.name.lower(): c for c in s.query(BoardColumn).filter(BoardColumn.project_id == proj.id).all()}
        for state in sorted({it["fields"].get("System.State","To do") for it in data}, key=lambda x: order_index.get(x.lower(), 99)):
            if state.lower() not in col_by_name:
                max_order = max((c.order for c in col_by_name.values()), default=-1)
                col = BoardColumn(project_id=proj.id, name=state, order=order_index.get(state.lower(), max_order+1), is_done=(state.lower()=="done"))
                s.add(col); s.flush()
                col_by_name[state.lower()] = col
                print(f"  coluna criada: {state}")
        # reordena todas para seguir o template
        for col in s.query(BoardColumn).filter(BoardColumn.project_id==proj.id).all():
            if col.name.lower() in order_index:
                col.order = order_index[col.name.lower()]
        s.flush()
        s.commit()
        created = updated = ignorados = 0
        for it in data:
            wid = it["id"]; f = it["fields"]
            title = f.get("System.Title","").strip()[:250] or f"GAVAR-{wid}"
            state = f.get("System.State","To do")
            assignee = (f.get("System.AssignedTo") or {}).get("displayName")
            col = col_by_name.get(state.lower()) or next(iter(col_by_name.values()))
            code_num = wid
            # tags -> labels (System.Tags é "a; b; c")
            raw_tags = (f.get("System.Tags") or "").strip()
            tag_names = [t.strip() for t in raw_tags.split(";") if t.strip()] if raw_tags else []
            # normaliza: remove duplicatas mantendo ordem, limita a 60 chars
            seen = set()
            tag_names = [t[:60] for t in tag_names if not (t in seen or seen.add(t))]
            # tarefas locais nunca entram no sync (nem são sobrescritas por número)
            local_com_mesmo_numero = s.query(Task).filter(
                Task.project_id==proj.id, Task.number==code_num, Task.is_local == True  # noqa: E712
            ).first()
            if local_com_mesmo_numero:
                ignorados += 1
                print(f"  ignorado #{wid}: número {code_num} pertence a uma tarefa local ({local_com_mesmo_numero.title[:40]})")
                continue
            task = s.query(Task).filter(
                Task.project_id==proj.id, Task.number==code_num, Task.is_local == False  # noqa: E712
            ).first()
            if task:
                changed = False
                if task.title != title: task.title = title; changed=True
                if task.column_id != col.id: task.column_id = col.id; changed=True
                if col.is_done:
                    quando = _data_conclusao(f)
                    if quando and (task.done_at is None or abs((task.done_at - quando).days) > 0):
                        task.done_at = quando
                        changed = True
                if (task.assignee or "") != (assignee or ""):
                    task.assignee = assignee; changed=True
                    if assignee: get_or_create_member(s, proj.id, assignee)
                # sincroniza labels
                existing_labels = {lb.name for lb in task.labels}
                desired_labels = set(tag_names)
                if existing_labels != desired_labels:
                    # limpa e recria
                    task.labels.clear()
                    for tname in tag_names:
                        lb = s.query(Label).filter(Label.name == tname).first()
                        if not lb:
                            lb = Label(name=tname)
                            s.add(lb); s.flush()
                        task.labels.append(lb)
                    changed = True
                if changed: updated+=1
            else:
                # encontra coluna inicial se estado não existe
                proj_task_seq = (proj.task_seq or 0) + 1
                proj.task_seq = proj_task_seq
                task = Task(project_id=proj.id, column_id=col.id, number=code_num, title=title,
                            description=f"Importado do Azure #{wid} - {state}", assignee=assignee,
                            done_at=_data_conclusao(f) if col.is_done else None)
                s.add(task)
                if assignee: get_or_create_member(s, proj.id, assignee)
                # labels para novo card
                for tname in tag_names:
                    lb = s.query(Label).filter(Label.name == tname).first()
                    if not lb:
                        lb = Label(name=tname)
                        s.add(lb); s.flush()
                    task.labels.append(lb)
                created+=1
        locais = s.query(Task).filter(
            Task.project_id==proj.id, Task.is_local == True, Task.deleted_at == None  # noqa: E712, E711
        ).count()
        if args.dry_run:
            s.rollback()
            print(f"DRY-RUN: {created} criados, {updated} atualizados, {ignorados} ignorados (número de tarefa local) — não gravado")
        else:
            s.commit()
            print(f"OK: {created} criados, {updated} atualizados em {proj.key} ({proj.name})")
        print(f"Tarefas locais preservadas (não sincronizam): {locais}")
    finally:
        s.close()

if __name__ == "__main__":
    main()
