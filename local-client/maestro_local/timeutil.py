"""Conversão de timestamps do banco para data/hora local.

O banco grava `created_at`/`updated_at`/`done_at` com `datetime.utcnow()`
(naive, em UTC). Comparar `.date()` disso com `date.today()` (local) erra o dia
sempre que o fuso não é UTC — no Brasil, uma entrega às 22h cai no dia seguinte
em UTC, e o relatório semanal a colocava na semana errada.
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone


def local(dt: datetime | None) -> datetime | None:
    """Converte um timestamp naive-UTC para datetime com fuso local."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone()
    return dt.astimezone()


def data_local(dt: datetime | None) -> date | None:
    """Data local de um timestamp gravado em UTC."""
    convertido = local(dt)
    return convertido.date() if convertido else None


def limites_utc(inicio: date, fim: date) -> tuple[datetime, datetime]:
    """Intervalo de datas locais -> timestamps naive-UTC (para filtrar no banco)."""
    fuso = datetime.now().astimezone().tzinfo
    inicio_dt = datetime.combine(inicio, time.min, tzinfo=fuso).astimezone(timezone.utc)
    fim_dt = datetime.combine(fim, time.max, tzinfo=fuso).astimezone(timezone.utc)
    return inicio_dt.replace(tzinfo=None), fim_dt.replace(tzinfo=None)
