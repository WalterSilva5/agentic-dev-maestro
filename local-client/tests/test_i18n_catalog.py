"""O catálogo i18n é um dict literal — chaves repetidas são aceitas em silêncio
pelo Python (a última vence), deixando traduções mortas. Este teste falha se
alguma duplicata for reintroduzida."""
from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / "maestro_local" / "i18n_catalog.py"


def _literal_keys() -> list[str]:
    """Todas as chaves string dos dicts do catálogo, na ordem em que aparecem."""
    tree = ast.parse(CATALOG.read_text(encoding="utf-8"))
    keys: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k in node.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.append(k.value)
    return keys


def test_catalogo_sem_chaves_duplicadas():
    dupes = [k for k, n in Counter(_literal_keys()).items() if n > 1]
    assert not dupes, (
        f"{len(dupes)} chave(s) duplicada(s) no i18n_catalog.py "
        f"(a última vence, as anteriores viram tradução morta): {sorted(dupes)}"
    )


def test_catalogo_carrega_e_traduz():
    from maestro_local import i18n_catalog
    cat = getattr(i18n_catalog, "CATALOG", None) or getattr(i18n_catalog, "EN", None)
    assert isinstance(cat, dict) and cat, "catálogo vazio ou não encontrado"
