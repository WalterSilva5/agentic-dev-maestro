#!/usr/bin/env python3
"""Importa os docs de daily do vault para o Daily do projeto no Maestro.

Lê `daily/YYYY-MM/DD-MM-YYYY - Daily - <tema>.md` e cria os registros
(INTRO / ITEMS / SPRINT / PENDING) por dia no projeto local.

Uso:
    python scripts/import_daily_vault.py \
        --dir /home/wsi/repositorios/github/vault-docs-projetos/tarefas/VERZEL/GAV/daily \
        --project-key MIG --dry-run

    # aplicando
    python scripts/import_daily_vault.py --dir <...> --project-key MIG

    # só um mês / um arquivo
    python scripts/import_daily_vault.py --dir <...> --project-key MIG --month 2026-11
    python scripts/import_daily_vault.py --file "<...>.md" --project-key MIG
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from maestro_local.config import get_active_workspace_id, get_workspace_db_path  # noqa: E402
from maestro_local.daily_doc import parse_daily_markdown  # noqa: E402
from maestro_local.db.models import (  # noqa: E402
    Project,
    ProjectDailyEntry,
    get_session,
    init_db,
)


def _arquivos(base: Path, month: str | None, file: str | None) -> list[Path]:
    if file:
        return [Path(file).expanduser()]
    if month:
        return sorted((base / month).glob("*.md"))
    return sorted(base.rglob("*.md"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="", help="pasta raiz dos dailies (daily/)")
    ap.add_argument("--file", default="", help="importar um único .md")
    ap.add_argument("--month", default="", help="importar só um mês (YYYY-MM)")
    ap.add_argument("--project-key", required=True, help="key do projeto local (ex.: MIG)")
    ap.add_argument("--replace", action="store_true",
                    help="substitui os registros do dia (padrão: pula dias já existentes)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.file and not args.dir:
        ap.error("informe --dir ou --file")

    init_db(get_workspace_db_path(get_active_workspace_id()))
    s = get_session()
    try:
        projeto = s.query(Project).filter(Project.key == args.project_key.upper()).first()
        if not projeto:
            print(f"Projeto {args.project_key!r} não encontrado neste workspace.")
            return 2

        arquivos = _arquivos(Path(args.dir).expanduser(), args.month or None, args.file or None)
        print(f"{len(arquivos)} arquivo(s) para importar em {projeto.key} ({projeto.name})")

        criados = pulados = erros = 0
        for arq in arquivos:
            if not arq.exists():
                print(f"  ! não existe: {arq}")
                erros += 1
                continue
            try:
                day, titulo, blocks = parse_daily_markdown(arq.read_text(encoding="utf-8", errors="replace"))
            except Exception as e:  # noqa: BLE001
                print(f"  ! erro lendo {arq.name}: {e}")
                erros += 1
                continue
            if not day or not blocks:
                print(f"  ! sem cabeçalho/blocos: {arq.name}")
                erros += 1
                continue

            ja = (
                s.query(ProjectDailyEntry)
                .filter(ProjectDailyEntry.project_id == projeto.id, ProjectDailyEntry.date == day)
                .count()
            )
            if ja and not args.replace:
                pulados += 1
                continue

            if ja and args.replace:
                for old in (
                    s.query(ProjectDailyEntry)
                    .filter(ProjectDailyEntry.project_id == projeto.id, ProjectDailyEntry.date == day)
                    .all()
                ):
                    s.delete(old)
                s.flush()

            base = (
                s.query(ProjectDailyEntry)
                .filter(ProjectDailyEntry.project_id == projeto.id, ProjectDailyEntry.date == day)
                .count()
            )
            for i, b in enumerate(blocks):
                s.add(ProjectDailyEntry(
                    project_id=projeto.id,
                    date=day,
                    kind=(b.kind or "WORK")[:20],
                    section=(b.section or "ITEMS")[:20],
                    title=(b.title or "")[:200],
                    sort_order=base + i,
                    body=b.body or "",
                    author=(b.author or None),
                    minutes=b.minutes,
                    task_code=(b.task_code or "")[:40],
                ))
            criados += 1
            print(f"  + {day}  {len(blocks):2d} blocos  {titulo[:60]}")

        if args.dry_run:
            s.rollback()
            print(f"\nDRY-RUN: {criados} dia(s) importado(s), {pulados} pulado(s), {erros} erro(s) (nada gravado)")
        else:
            s.commit()
            print(f"\nOK: {criados} dia(s) importado(s), {pulados} pulado(s), {erros} erro(s)")
        return 0
    finally:
        s.close()


if __name__ == "__main__":
    raise SystemExit(main())
