"""Assistente de code review: obtém um diff git e pede à IA uma revisão
estruturada (resumo, problemas por severidade, sugestões)."""
from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger("maestro.codereview")

MAX_DIFF_CHARS = 30000

_SYSTEM = (
    "Você é um revisor de código sênior, rigoroso e construtivo. "
    "Responda SEMPRE apenas com JSON válido, em português."
)

_PROMPT = (
    "Revise o diff abaixo. Aponte bugs, riscos de segurança, problemas de "
    "estilo/manutenção e melhorias. Seja específico e cite arquivos quando "
    "possível.\n\nDiff:\n```diff\n{diff}\n```\n\n"
    "Responda com JSON no formato exato:\n"
    "{{\n"
    '  "summary": "resumo geral da mudança e da qualidade",\n'
    '  "issues": [{{"severity": "LOW|MEDIUM|HIGH", "file": "arquivo", "note": "problema"}}],\n'
    '  "suggestions": ["sugestão de melhoria"]\n'
    "}}"
)


def get_git_diff(path: str, base: str = "") -> str:
    """Retorna o diff git. Sem `base`: diff do working tree (staged+unstaged).
    Com `base` (ex.: 'main', 'HEAD~1', 'main...HEAD'): diff contra essa ref."""
    args = ["git", "-C", path, "--no-pager", "diff"]
    if base and base.strip():
        args.append(base.strip())
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        raise RuntimeError("git não encontrado no PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError("git diff excedeu o tempo limite")
    if out.returncode != 0:
        raise RuntimeError((out.stderr or "git diff falhou").strip())
    return out.stdout


def review_diff(diff: str) -> dict:
    """Pede à IA uma revisão estruturada do diff."""
    from maestro_local.ai.providers import build_chat_model
    from maestro_local.transcricoes.summarizer import _parse_json_response

    if not diff.strip():
        raise ValueError("Diff vazio (nada a revisar)")
    truncated = diff[:MAX_DIFF_CHARS]
    llm = build_chat_model(temperature=0.2)
    resp = llm.invoke([("system", _SYSTEM), ("user", _PROMPT.format(diff=truncated))])
    parsed = _parse_json_response(getattr(resp, "content", str(resp)))
    if not isinstance(parsed, dict):
        raise ValueError("Resposta da IA não é um objeto JSON")

    issues = []
    for it in (parsed.get("issues") or []):
        if isinstance(it, dict):
            sev = str(it.get("severity", "MEDIUM")).upper()
            if sev not in ("LOW", "MEDIUM", "HIGH"):
                sev = "MEDIUM"
            issues.append({
                "severity": sev,
                "file": str(it.get("file") or ""),
                "note": str(it.get("note") or ""),
            })
    suggestions = parsed.get("suggestions") or []
    if not isinstance(suggestions, list):
        suggestions = [str(suggestions)]
    return {
        "summary": str(parsed.get("summary") or ""),
        "issues": issues,
        "suggestions": [str(x) for x in suggestions if str(x).strip()],
        "truncated": len(diff) > MAX_DIFF_CHARS,
    }


def review_to_markdown(review: dict) -> str:
    """Formata a revisão como markdown para um comentário CODE_REVIEW."""
    parts = ["## 🤖 Code review (IA)"]
    if review.get("summary"):
        parts.append(review["summary"])
    if review.get("issues"):
        parts.append("**Problemas:**")
        for it in review["issues"]:
            loc = f" `{it['file']}`" if it.get("file") else ""
            parts.append(f"- **[{it['severity']}]**{loc} {it['note']}")
    if review.get("suggestions"):
        parts.append("**Sugestões:**")
        parts += [f"- {sug}" for sug in review["suggestions"]]
    if review.get("truncated"):
        parts.append("_(diff truncado para revisão)_")
    return "\n\n".join(parts)
