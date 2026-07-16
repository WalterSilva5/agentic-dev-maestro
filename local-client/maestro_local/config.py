import json
import shutil
from pathlib import Path

from maestro_local.db.models import DATA_DIR

_CONFIG_FILE = DATA_DIR / "config.json"
WORKSPACES_DIR = DATA_DIR / "workspaces"


def load_config() -> dict:
    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(cfg: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


# ---------------------------------------------------------------------------
# Projeto ativo (por workspace — os projetos vivem no banco do workspace)
# ---------------------------------------------------------------------------

def get_active_project_id():
    ws = get_active_workspace_id()
    pid = load_config().get("active_project_by_ws", {}).get(ws)
    try:
        return int(pid) if pid is not None else None
    except (TypeError, ValueError):
        return None


def set_active_project_id(project_id):
    cfg = load_config()
    by_ws = cfg.setdefault("active_project_by_ws", {})
    ws = get_active_workspace_id()
    if project_id is None:
        by_ws.pop(ws, None)
    else:
        by_ws[ws] = int(project_id)
    save_config(cfg)


# ---------------------------------------------------------------------------
# Coach proativo (dicas do agente ao longo do dia)
# ---------------------------------------------------------------------------

_COACH_DEFAULTS = {"enabled": True, "interval_min": 90}


def get_coach_config() -> dict:
    cfg = load_config().get("settings", {}).get("coach", {})
    return {
        "enabled": bool(cfg.get("enabled", _COACH_DEFAULTS["enabled"])),
        "interval_min": int(cfg.get("interval_min", _COACH_DEFAULTS["interval_min"])),
    }


def set_coach_config(enabled: bool | None = None, interval_min: int | None = None):
    cfg = load_config()
    settings = cfg.setdefault("settings", {})
    coach = settings.setdefault("coach", {})
    if enabled is not None:
        coach["enabled"] = bool(enabled)
    if interval_min is not None:
        coach["interval_min"] = max(15, int(interval_min))  # nunca menos que 15 min
    save_config(cfg)


# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------

def _ensure_workspaces():
    """Ensure workspaces dir and at least one workspace exist."""
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    ws_list = cfg.get("workspaces", [])

    if not ws_list:
        # First run or migration: create default workspace
        default_dir = WORKSPACES_DIR / "default"
        default_dir.mkdir(parents=True, exist_ok=True)

        # Migrate existing DB if present
        old_db = DATA_DIR / "maestro.db"
        new_db = default_dir / "maestro.db"
        if old_db.exists() and not new_db.exists():
            shutil.move(str(old_db), str(new_db))

        ws_list = [{"id": "default", "name": "Default", "icon": "A"}]
        cfg["workspaces"] = ws_list
        cfg["active_workspace"] = "default"
        save_config(cfg)

    return cfg


def list_workspaces() -> list[dict]:
    cfg = _ensure_workspaces()
    return cfg.get("workspaces", [])


def get_active_workspace_id() -> str:
    cfg = _ensure_workspaces()
    return cfg.get("active_workspace", "default")


def get_workspace_db_path(ws_id: str) -> str:
    ws_dir = WORKSPACES_DIR / ws_id
    ws_dir.mkdir(parents=True, exist_ok=True)
    return str(ws_dir / "maestro.db")


def set_active_workspace(ws_id: str):
    cfg = load_config()
    cfg["active_workspace"] = ws_id
    save_config(cfg)


def create_workspace(name: str, icon: str = "W", description: str = "", color: str = "") -> dict:
    cfg = _ensure_workspaces()
    ws_list = cfg.get("workspaces", [])

    # Generate ID from name
    ws_id = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    if not ws_id:
        ws_id = f"ws-{len(ws_list)}"
    # Ensure unique
    existing_ids = {w["id"] for w in ws_list}
    base_id = ws_id
    counter = 1
    while ws_id in existing_ids:
        ws_id = f"{base_id}-{counter}"
        counter += 1

    ws_dir = WORKSPACES_DIR / ws_id
    ws_dir.mkdir(parents=True, exist_ok=True)

    ws = {"id": ws_id, "name": name, "icon": icon, "description": description, "color": color}
    ws_list.append(ws)
    cfg["workspaces"] = ws_list
    save_config(cfg)
    return ws


def update_workspace(ws_id: str, *, name: str | None = None, icon: str | None = None,
                     description: str | None = None, color: str | None = None):
    cfg = load_config()
    for ws in cfg.get("workspaces", []):
        if ws["id"] == ws_id:
            if name is not None:
                ws["name"] = name
            if icon is not None:
                ws["icon"] = icon
            if description is not None:
                ws["description"] = description
            if color is not None:
                ws["color"] = color
            break
    save_config(cfg)


def rename_workspace(ws_id: str, new_name: str, new_icon: str | None = None):
    update_workspace(ws_id, name=new_name, icon=new_icon)


# ---------------------------------------------------------------------------
# Idioma da aplicação
# ---------------------------------------------------------------------------

def get_language() -> str:
    return load_config().get("language", "pt")


def set_language(code: str):
    cfg = load_config()
    cfg["language"] = code
    save_config(cfg)


# ---------------------------------------------------------------------------
# AI providers (OpenAI-compatible: LM Studio, opencode, etc.)
# ---------------------------------------------------------------------------

def list_ai_providers() -> list[dict]:
    cfg = load_config()
    return cfg.get("ai_providers", [])


def get_active_ai_provider() -> dict | None:
    cfg = load_config()
    active_id = cfg.get("active_ai_provider")
    for p in cfg.get("ai_providers", []):
        if p.get("id") == active_id:
            return p
    providers = cfg.get("ai_providers", [])
    return providers[0] if providers else None


def _invalidate_ai_caches():
    """Descarta modelos/agentes em cache quando o provedor muda (import tardio
    para evitar dependência circular com o pacote ai)."""
    try:
        from maestro_local.ai.providers import clear_model_cache
        clear_model_cache()
        from maestro_local.ai.agent import clear_agent_cache
        clear_agent_cache()
    except Exception:  # noqa: BLE001
        pass


def save_ai_providers(providers: list[dict], active_id: str | None = None):
    cfg = load_config()
    cfg["ai_providers"] = providers
    if active_id is not None:
        cfg["active_ai_provider"] = active_id
    elif active_id is None and not any(
        p.get("id") == cfg.get("active_ai_provider") for p in providers
    ):
        cfg["active_ai_provider"] = providers[0]["id"] if providers else None
    save_config(cfg)
    _invalidate_ai_caches()


def set_active_ai_provider(provider_id: str):
    cfg = load_config()
    cfg["active_ai_provider"] = provider_id
    save_config(cfg)
    _invalidate_ai_caches()


def delete_workspace(ws_id: str) -> bool:
    cfg = load_config()
    ws_list = cfg.get("workspaces", [])
    if len(ws_list) <= 1:
        return False
    cfg["workspaces"] = [w for w in ws_list if w["id"] != ws_id]
    if cfg.get("active_workspace") == ws_id:
        cfg["active_workspace"] = cfg["workspaces"][0]["id"]
    save_config(cfg)

    ws_dir = WORKSPACES_DIR / ws_id
    if ws_dir.exists():
        shutil.rmtree(ws_dir)
    return True
