"""Usabilidade do fluxo: colunas padrão enxutas, filtros de épico/tag e
abertura de board definindo o projeto ativo."""
from relay.db.models import (
    DEFAULT_COLUMNS,
    BoardColumn,
    Epic,
    Label,
    Project,
    Task,
    get_session,
)
from relay.gui.views.board_view import BoardView


def _projeto_com_card():
    s = get_session()
    p = Project(name="P", key="P")
    s.add(p)
    s.flush()
    pid = p.id
    for i, c in enumerate(DEFAULT_COLUMNS):
        s.add(BoardColumn(project_id=pid, name=c["name"], order=i,
                          is_done=c.get("is_done", False)))
    s.flush()
    col = s.query(BoardColumn).filter_by(project_id=pid).first()
    t1 = Task(project_id=pid, column_id=col.id, number=1, title="A",
              assignee="Walter")
    s.add(t1)
    e = Epic(project_id=pid, name="Cashier")
    s.add(e)
    s.flush()
    t1.epics.append(e)
    lbl = Label(name="onda-1")
    s.add(lbl)
    s.flush()
    t1.labels.append(lbl)
    s.commit()
    s.close()
    return pid


def test_colunas_padrao_sao_tres(temp_db):
    assert [c["name"] for c in DEFAULT_COLUMNS] == ["A fazer", "Fazendo", "Feito"]
    assert sum(1 for c in DEFAULT_COLUMNS if c.get("is_done")) == 1


def test_filtros_epico_e_tag_carregados(qapp, temp_db):
    pid = _projeto_com_card()
    v = BoardView()
    v.set_project(pid)
    assert v.filter_bar.epic_combo.count() == 2      # Todos + Cashier
    assert v.filter_bar.tag_combo.count() == 2       # Todas + onda-1
    assert sum(len(c.get_cards()) for c in v._columns) == 1


def test_filtro_epico_esconde_quem_nao_casa(qapp, temp_db):
    pid = _projeto_com_card()
    v = BoardView()
    v.set_project(pid)
    v.show()
    idx = v.filter_bar.epic_combo.findData(999999)
    assert idx == -1
    v.filter_bar.epic_combo.setCurrentIndex(1)  # Cashier
    v._apply_filters()
    visiveis = sum(
        1 for c in v._columns for card in c.get_cards() if card.isVisible())
    assert visiveis == 1


def test_abrir_board_define_projeto_ativo(qapp, temp_db):
    from relay.config import get_active_project_id
    from relay.gui.main_window import MainWindow
    pid = _projeto_com_card()
    w = MainWindow()
    w._open_board(pid)
    assert get_active_project_id() == pid
    assert w.stack.currentWidget() is w.board_view
