"""
1S: ERP Free Edition — Audit Log (inspired by SAP Change Documents).

Tracks who changed what and when. Every write to catalogs, registers,
and documents can call AuditLog.Record() to leave a traceable entry.

The global LOG instance is available as АудитЖурнал / AuditLog in scripts.
"""
from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuditEntry:
    """One audit record."""
    timestamp:   datetime.datetime
    user:        str
    action:      str          # Created / Updated / Deleted / Posted / Approved ...
    object_type: str          # Document, Catalog, Register ...
    object_id:   str          # Number, Code, or other identifier
    details:     str = ""     # Human-readable description of the change

    def __str__(self) -> str:
        ts = self.timestamp.strftime("%d.%m.%Y %H:%M:%S")
        return f"[{ts}] {self.user}  {self.action}  {self.object_type}#{self.object_id}  {self.details}"

    # 1S-style property aliases
    @property
    def Дата(self):         return self.timestamp
    @property
    def Пользователь(self): return self.user
    @property
    def Користувач(self):   return self.user
    @property
    def Действие(self):     return self.action
    @property
    def Дія(self):          return self.action
    @property
    def Объект(self):       return self.object_type
    @property
    def Обєкт(self):        return self.object_type
    @property
    def ИД(self):           return self.object_id
    @property
    def ІД(self):           return self.object_id
    @property
    def Описание(self):     return self.details
    @property
    def Опис(self):         return self.details
    @property
    def Date(self):         return self.timestamp
    @property
    def User(self):         return self.user
    @property
    def Action(self):       return self.action
    @property
    def Details(self):      return self.details


class AuditLog:
    """
    Журнал аудита / Журнал аудиту / Audit Log.

    A named, in-memory append-only log of business events.
    Multiple named logs can co-exist (one per module, one global, etc.)

    Example (Ukrainian):
        Журнал = АудитЖурнал("Бухгалтерія")
        Журнал.Записати("Іваненко", "Провести", "Документ", "ВН-000001",
                         "Видаткова накладна на 54 000 грн")

    Example (English):
        Log = AuditLog("Accounting")
        Log.Record("jsmith", "Post", "Document", "SI-000001",
                   "Sales invoice 54000")
    """

    def __init__(self, name: str = "Global"):
        self.name = name
        self._entries: list[AuditEntry] = []

    # ── Write ────────────────────────────────────────────────────────

    def Record(self, user: str, action: str, object_type: str,
               object_id: str = "", details: str = "") -> AuditEntry:
        entry = AuditEntry(
            timestamp=datetime.datetime.now(),
            user=user,
            action=action,
            object_type=object_type,
            object_id=object_id,
            details=details,
        )
        self._entries.append(entry)
        return entry

    # ── Read ─────────────────────────────────────────────────────────

    def GetEntries(self, limit: int = 100,
                   user: str = "",
                   action: str = "",
                   object_type: str = "") -> list[AuditEntry]:
        """Return recent entries, optionally filtered."""
        result = self._entries
        if user:
            result = [e for e in result if e.user == user]
        if action:
            result = [e for e in result if e.action == action]
        if object_type:
            result = [e for e in result if e.object_type == object_type]
        return result[-limit:]

    def Count(self) -> int:
        return len(self._entries)

    def Clear(self) -> None:
        self._entries.clear()

    def Print(self, limit: int = 20) -> None:
        """Print last N entries (for 1S scripts)."""
        for entry in self.GetEntries(limit):
            print(entry, flush=True)

    def __iter__(self):
        return iter(self._entries)

    def __len__(self):
        return len(self._entries)

    def __repr__(self):
        return f"AuditLog({self.name!r}, {len(self._entries)} entries)"

    # ── Russian aliases ───────────────────────────────────────────────
    Записать       = Record
    ПолучитьЗаписи = GetEntries
    Количество     = Count
    Очистить       = Clear
    Вывести        = Print

    # ── Ukrainian aliases ─────────────────────────────────────────────
    Записати       = Record
    ОтриматиЗаписи = GetEntries
    Кількість      = Count
    Очистити       = Clear
    Вивести        = Print


# ── Global audit log + aliases ────────────────────────────────────────────────

# Scripts can use  АудитЖурнал  or  AuditLog()  to get a global instance
_GLOBAL_AUDIT = AuditLog("Global")

АудитЖурнал  = AuditLog    # Russian / Ukrainian class alias
