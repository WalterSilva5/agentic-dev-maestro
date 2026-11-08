"""Catálogo interno (`/api/skills`) x skills globais (`~/.config/opencode/skills`).

O catálogo é o espelho que aparece na tela "Skills" do app e no endpoint
`/api/skills`; os arquivos `SKILL.md` são o que os agentes carregam. Quando um
dos dois muda sozinho, o outro fica mentindo — este teste pega a divergência.
"""
import pathlib

import pytest

from maestro_local.skills import catalog

SKILLS_DIR = pathlib.Path.home() / ".config" / "opencode" / "skills"
PRECISA_GLOBAIS = pytest.mark.skipif(
    not SKILLS_DIR.exists(), reason="skills globais não instaladas nesta máquina"
)


def _sem_name(texto: str) -> list[str]:
    """Compara sem a linha `name:` (no catálogo o nome vem do campo "name")."""
    return [l for l in texto.strip().splitlines() if not l.startswith("name: ")]


@PRECISA_GLOBAIS
@pytest.mark.parametrize("skill", catalog.SKILLS, ids=[s["id"] for s in catalog.SKILLS])
def test_catalogo_espelha_o_skill_md_global(skill):
    arquivo = SKILLS_DIR / skill["id"] / "SKILL.md"
    if not arquivo.exists():
        pytest.skip(f"{skill['id']} não existe no diretório global")
    catalogo = _sem_name(skill["content"])
    global_ = _sem_name(arquivo.read_text())
    assert catalogo == global_, (
        f"{skill['id']} divergiu do SKILL.md global — atualize os dois lados"
    )


def test_toda_skill_tem_frontmatter_e_fences_fechadas():
    for skill in catalog.SKILLS:
        corpo = skill["content"]
        assert corpo.startswith("---"), skill["id"]
        assert "description:" in corpo.split("---")[1], skill["id"]
        assert corpo.count("```") % 2 == 0, f"{skill['id']}: fence ``` sem fechar"
        assert skill["name"].strip(), skill["id"]


@PRECISA_GLOBAIS
def test_skills_documentam_os_recursos_novos():
    """Os recursos novos precisam estar documentados para os agentes."""
    api = next(s for s in catalog.SKILLS if s["id"] == "maestro-api-agent")["content"]
    for trecho in ("metrics/dimensions", "metrics/stages", "isLocal", "/api/recordings"):
        assert trecho in api, f"maestro-api-agent não documenta {trecho}"

    goals = next(s for s in catalog.SKILLS if s["id"] == "maestro-goals")["content"]
    assert "isLocal" in goals, "goals precisa avisar que tarefa local não conta"
