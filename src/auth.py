"""
1S: ERP Free Edition — user auth management.
Passwords are stored as SHA-256 hashes in config/users.json.
Default accounts created on first run: admin/admin  user/user
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

_USERS_FILE = Path(__file__).parent.parent / "config" / "users.json"


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _load() -> dict:
    if not _USERS_FILE.exists():
        _bootstrap()
    with open(_USERS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    _USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _bootstrap() -> None:
    _save({
        "admin": {"password": _hash("admin"), "role": "admin",
                  "display": "Администратор"},
        "user":  {"password": _hash("user"),  "role": "user",
                  "display": "Пользователь"},
    })


def verify(username: str, password: str) -> dict | None:
    """Return user info dict if credentials valid, else None."""
    users = _load()
    rec = users.get(username)
    if rec and rec["password"] == _hash(password):
        return {"username": username, "role": rec["role"],
                "display": rec.get("display", username)}
    return None


def list_users() -> list[dict]:
    return [{"username": k, "role": v["role"], "display": v.get("display", k)}
            for k, v in _load().items()]


def add_user(username: str, password: str, role: str = "user",
             display: str = "") -> None:
    users = _load()
    users[username] = {
        "password": _hash(password),
        "role": role,
        "display": display or username,
    }
    _save(users)


def change_password(username: str, new_password: str) -> bool:
    users = _load()
    if username not in users:
        return False
    users[username]["password"] = _hash(new_password)
    _save(users)
    return True


def delete_user(username: str) -> bool:
    users = _load()
    if username not in users:
        return False
    del users[username]
    _save(users)
    return True
