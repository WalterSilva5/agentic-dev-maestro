"""Cofre de senhas GLOBAL compatível com KeePass (.kdbx, KeePass 2.x).

- Um único cofre para o app (não por workspace), em ~/.maestro-local/vault.kdbx
  (caminho configurável — permite apontar para um vault KeePass existente).
- Destravado por senha-mestra e/ou key file, via pykeepass.
- A senha-mestra NUNCA é persistida: fica só na instância aberta em memória e
  é descartada no lock().
"""
from __future__ import annotations

import logging
import os
import secrets
import string
from pathlib import Path

from maestro_local.db.models import DATA_DIR

logger = logging.getLogger("maestro.vault")

DEFAULT_VAULT_PATH = DATA_DIR / "vault.kdbx"

CLIPBOARD_CLEAR_SECONDS = 25
AUTO_LOCK_SECONDS = 5 * 60


def get_vault_path() -> Path:
    """Caminho do cofre global (config `vault_path` ou o padrão)."""
    from maestro_local.config import load_config
    cfg = load_config().get("settings", {})
    p = cfg.get("vault_path")
    return Path(p) if p else DEFAULT_VAULT_PATH


def set_vault_path(path: str) -> None:
    from maestro_local.config import load_config, save_config
    cfg = load_config()
    cfg.setdefault("settings", {})["vault_path"] = path
    save_config(cfg)


class VaultLocked(Exception):
    pass


class VaultManager:
    """Sessão do cofre em memória. Uma instância global no app desktop."""

    def __init__(self):
        self._kp = None  # instância PyKeePass enquanto destravado

    # ---- Estado ----
    @property
    def is_unlocked(self) -> bool:
        return self._kp is not None

    def vault_exists(self) -> bool:
        return get_vault_path().exists()

    def lock(self) -> None:
        self._kp = None  # descarta credenciais/DB da memória

    # ---- Abrir/criar ----
    def create(self, master_password: str, keyfile: str | None = None) -> None:
        from pykeepass import create_database
        path = get_vault_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._kp = create_database(str(path), password=master_password, keyfile=keyfile)

    def unlock(self, master_password: str, keyfile: str | None = None) -> None:
        from pykeepass import PyKeePass
        self._kp = PyKeePass(str(get_vault_path()), password=master_password or None,
                             keyfile=keyfile or None)

    def _require(self):
        if self._kp is None:
            raise VaultLocked("Cofre travado")
        return self._kp

    # ---- Entradas ----
    def entries(self, query: str = "") -> list[dict]:
        kp = self._require()
        out = []
        q = (query or "").lower()
        for e in kp.entries:
            title = e.title or ""
            username = e.username or ""
            url = e.url or ""
            group = e.group.name if e.group else ""
            hay = f"{title} {username} {url} {group}".lower()
            if q and q not in hay:
                continue
            out.append({
                "uuid": e.uuid.hex, "title": title, "username": username,
                "url": url, "group": group, "notes": e.notes or "",
            })
        out.sort(key=lambda x: (x["group"].lower(), x["title"].lower()))
        return out

    def get_password(self, uuid_hex: str) -> str:
        kp = self._require()
        for e in kp.entries:
            if e.uuid.hex == uuid_hex:
                return e.password or ""
        raise KeyError("Entrada não encontrada")

    def add_entry(self, title: str, username: str, password: str,
                  url: str = "", notes: str = "", group_name: str = "") -> None:
        kp = self._require()
        group = kp.root_group
        if group_name:
            found = kp.find_groups(name=group_name, first=True)
            group = found or kp.add_group(kp.root_group, group_name)
        kp.add_entry(group, title, username, password, url=url or None,
                     notes=notes or None)
        kp.save()

    def update_entry(self, uuid_hex: str, *, title=None, username=None,
                     password=None, url=None, notes=None) -> None:
        kp = self._require()
        for e in kp.entries:
            if e.uuid.hex == uuid_hex:
                if title is not None:
                    e.title = title
                if username is not None:
                    e.username = username
                if password:
                    e.password = password
                if url is not None:
                    e.url = url
                if notes is not None:
                    e.notes = notes
                kp.save()
                return
        raise KeyError("Entrada não encontrada")

    def delete_entry(self, uuid_hex: str) -> None:
        kp = self._require()
        for e in kp.entries:
            if e.uuid.hex == uuid_hex:
                kp.delete_entry(e)
                kp.save()
                return
        raise KeyError("Entrada não encontrada")

    def groups(self) -> list[str]:
        kp = self._require()
        return sorted({g.name for g in kp.groups if g.name and g.name != "Root"})


def generate_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# Instância global do app desktop
vault = VaultManager()
