"""Limites do contexto de reunião: config, aplicação e API de settings."""
import pytest
from fastapi.testclient import TestClient

from maestro_local.api.app import app
from maestro_local.db.models import init_db


@pytest.fixture
def client(tmp_path, temp_db):
    with TestClient(app) as c:
        yield c


def test_padroes_dos_limites(temp_db):
    from maestro_local.config import get_meeting_context_limits

    assert get_meeting_context_limits() == {"cards": 12, "overdue": 8, "dailies": 5, "deliveries": 8}


def test_salva_e_limita_valores(temp_db):
    from maestro_local.config import get_meeting_context_limits, set_meeting_context_limits

    saida = set_meeting_context_limits(cards=3, overdue=2, dailies=1)
    assert saida == {"cards": 3, "overdue": 2, "dailies": 1, "deliveries": 8}

    # fora da faixa é aparado (1..50)
    assert set_meeting_context_limits(cards=0)["cards"] == 1
    assert set_meeting_context_limits(cards=999)["cards"] == 50
    assert get_meeting_context_limits()["cards"] == 50


def test_contexto_respeita_os_limites(temp_db):
    from datetime import datetime, timedelta

    from maestro_local.db.models import BoardColumn, Project, ProjectDailyEntry, Task, get_session
    from maestro_local.meeting_context import project_context

    s = get_session()
    p = Project(name="Limites", key="LIM")
    s.add(p)
    s.flush()
    s.add(BoardColumn(project_id=p.id, name="To do", order=0))
    col = BoardColumn(project_id=p.id, name="Dev Box", order=1)
    s.add(col)
    s.flush()
    for i in range(5):
        s.add(Task(project_id=p.id, column_id=col.id, number=i + 1, title=f"card {i}",
                   assignee="Ana", updated_at=datetime.now() - timedelta(days=5)))
    for i in range(5):
        s.add(ProjectDailyEntry(project_id=p.id, date=f"2026-11-0{i + 1}", kind="WORK",
                                body=f"registro {i}"))
    s.commit()

    texto = project_context(s, p.id, limits={"cards": 2, "overdue": 1, "dailies": 3, "deliveries": 1})
    s.close()

    assert texto.count("- LIM-") == 2          # só 2 cards em andamento
    assert texto.count("· WORK ·") == 3        # só 3 dailies


def test_api_settings_round_trip(client):
    r = client.put("/api/settings", json={"meetingContext": {"cards": 7, "overdue": 4, "dailies": 2}})
    assert r.status_code == 200
    ctx = r.json()["meetingContext"]
    assert ctx["cards"] == 7 and ctx["overdue"] == 4 and ctx["dailies"] == 2
    assert ctx["deliveries"] == 8              # não enviado, mantém o padrão

    assert client.get("/api/settings").json()["meetingContext"]["cards"] == 7
