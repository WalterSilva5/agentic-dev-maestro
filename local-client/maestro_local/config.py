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


def create_workspace(name: str, icon: str = "W") -> dict:
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

    ws = {"id": ws_id, "name": name, "icon": icon}
    ws_list.append(ws)
    cfg["workspaces"] = ws_list
    save_config(cfg)
    return ws


def rename_workspace(ws_id: str, new_name: str, new_icon: str | None = None):
    cfg = load_config()
    for ws in cfg.get("workspaces", []):
        if ws["id"] == ws_id:
            ws["name"] = new_name
            if new_icon is not None:
                ws["icon"] = new_icon
            break
    save_config(cfg)


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
