"""
1S: ERP Free Edition — Workflow Engine (inspired by SAP WF / BPM).

A WorkflowDocument adds an approval state machine on top of Document:

    Draft → Submitted → Approved / Rejected → Posted
                ↑                   ↓
            (recall)            (revision)

Every transition is logged with actor, timestamp, comment.
Aliases cover Russian, Ukrainian, English.
"""
from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from typing import Optional
from .catalogs import Document
from .types import Undefined


# ── Status constants ─────────────────────────────────────────────────────────

class WF:
    """Workflow status constants — same spelling used by all languages."""
    DRAFT     = "draft"
    PENDING   = "pending"
    APPROVED  = "approved"
    REJECTED  = "rejected"
    POSTED    = "posted"
    CANCELLED = "cancelled"
    REVISION  = "revision"    # sent back for correction

    # Russian display names
    _RU = {
        DRAFT:     "Черновик",
        PENDING:   "На согласовании",
        APPROVED:  "Согласован",
        REJECTED:  "Отклонён",
        POSTED:    "Проведён",
        CANCELLED: "Отменён",
        REVISION:  "На доработке",
    }
    # Ukrainian
    _UK = {
        DRAFT:     "Чернетка",
        PENDING:   "На погодженні",
        APPROVED:  "Погоджено",
        REJECTED:  "Відхилено",
        POSTED:    "Проведено",
        CANCELLED: "Скасовано",
        REVISION:  "На доопрацюванні",
    }
    # English
    _EN = {
        DRAFT:     "Draft",
        PENDING:   "Pending Approval",
        APPROVED:  "Approved",
        REJECTED:  "Rejected",
        POSTED:    "Posted",
        CANCELLED: "Cancelled",
        REVISION:  "Needs Revision",
    }

    @classmethod
    def label(cls, status: str, lang: str = "ru") -> str:
        table = {"ru": cls._RU, "uk": cls._UK, "en": cls._EN}.get(lang, cls._EN)
        return table.get(status, status)


# ── Audit / transition entry ──────────────────────────────────────────────────

@dataclass
class WFEntry:
    """One step in a workflow history."""
    from_status: str
    to_status:   str
    actor:       str
    comment:     str
    timestamp:   datetime.datetime = field(default_factory=datetime.datetime.now)

    def __str__(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M")
        return (f"[{ts}] {self.actor}: {self.from_status} → {self.to_status}"
                + (f"  «{self.comment}»" if self.comment else ""))

    # Aliases for 1S scripts
    @property
    def Дата(self):        return self.timestamp
    @property
    def Автор(self):       return self.actor
    @property
    def Коментар(self):    return self.comment
    @property
    def Комментарий(self): return self.comment
    @property
    def Comment(self):     return self.comment
    @property
    def Actor(self):       return self.actor
    @property
    def Date(self):        return self.timestamp
    @property
    def FromStatus(self):  return self.from_status
    @property
    def ToStatus(self):    return self.to_status


# ── Workflow Document ─────────────────────────────────────────────────────────

class WorkflowDocument(Document):
    """
    Документ с маршрутом согласования.

    Inherits all Document features and adds:
      • Status / Статус / Статус
      • Submit()  / Подать()       / Надіслати()
      • Approve() / Согласовать()  / Погодити()
      • Reject()  / Отклонить()    / Відхилити()
      • Recall()  / Отозвать()     / Відкликати()
      • Revise()  / НаДоработку()  / НаДоопрацювання()
      • History   / Журнал         / Журнал

    Example (Ukrainian):
        НЗ = ДокументЗМаршрутом("НарядЗамовлення")
        НЗ.Відповідальний = "Іваненко"
        НЗ.Надіслати("Іваненко", "Прошу погодити")
        НЗ.Погодити("Директор", "Погоджено")
        НЗ.Провести()

    Example (English):
        PO = WorkflowDocument("PurchaseOrder")
        PO.Submit("manager", "Please approve")
        PO.Approve("cfo", "Approved — within budget")
        PO.Post()
    """

    def __init__(self, doc_type: str = ""):
        super().__init__(doc_type)
        object.__setattr__(self, "_wf_status",  WF.DRAFT)
        object.__setattr__(self, "_wf_history", [])
        object.__setattr__(self, "_wf_approver", "")

    # ── Status ───────────────────────────────────────────────────────

    @property
    def Status(self) -> str:
        return object.__getattribute__(self, "_wf_status")

    @property
    def Статус(self) -> str:
        return object.__getattribute__(self, "_wf_status")

    def StatusLabel(self, lang: str = "ru") -> str:
        return WF.label(self.Status, lang)

    # ── History ──────────────────────────────────────────────────────

    @property
    def History(self) -> list[WFEntry]:
        return object.__getattribute__(self, "_wf_history")

    @property
    def Журнал(self) -> list[WFEntry]:
        return self.History

    def _transition(self, to: str, actor: str, comment: str = "") -> None:
        from_s = object.__getattribute__(self, "_wf_status")
        entry = WFEntry(from_status=from_s, to_status=to,
                        actor=actor, comment=comment)
        object.__getattribute__(self, "_wf_history").append(entry)
        object.__setattr__(self, "_wf_status", to)

    # ── Transitions ──────────────────────────────────────────────────

    def Submit(self, actor: str = "system", comment: str = "") -> bool:
        """Send for approval (Draft → Pending)."""
        if self.Status != WF.DRAFT:
            return False
        self._transition(WF.PENDING, actor, comment)
        return True

    def Approve(self, actor: str = "system", comment: str = "") -> bool:
        """Approve (Pending → Approved)."""
        if self.Status != WF.PENDING:
            return False
        object.__setattr__(self, "_wf_approver", actor)
        self._transition(WF.APPROVED, actor, comment)
        return True

    def Reject(self, actor: str = "system", reason: str = "") -> bool:
        """Reject (Pending → Rejected)."""
        if self.Status != WF.PENDING:
            return False
        self._transition(WF.REJECTED, actor, reason)
        return True

    def Revise(self, actor: str = "system", comment: str = "") -> bool:
        """Send back for revision (Pending → Revision)."""
        if self.Status != WF.PENDING:
            return False
        self._transition(WF.REVISION, actor, comment)
        return True

    def Recall(self, actor: str = "system", reason: str = "") -> bool:
        """Recall from approval (Pending → Draft)."""
        if self.Status != WF.PENDING:
            return False
        self._transition(WF.DRAFT, actor, reason or "Recalled")
        return True

    def Resubmit(self, actor: str = "system", comment: str = "") -> bool:
        """Resubmit after revision (Revision → Pending)."""
        if self.Status not in (WF.REVISION, WF.DRAFT, WF.REJECTED):
            return False
        self._transition(WF.PENDING, actor, comment)
        return True

    def Cancel(self, actor: str = "system", reason: str = "") -> bool:
        """Cancel (any non-Posted → Cancelled)."""
        if self.Status == WF.POSTED:
            return False
        self._transition(WF.CANCELLED, actor, reason)
        return True

    def Post(self, actor: str = "system", comment: str = "") -> bool:
        """Post to accounting (Approved → Posted). Draft also allowed for bypass."""
        if self.Status not in (WF.APPROVED, WF.DRAFT):
            return False
        result = super().Post()
        if result:
            self._transition(WF.POSTED, actor or "system", comment or "Posted")
        return result

    # ── Convenience ──────────────────────────────────────────────────

    @property
    def IsDraft(self) -> bool:     return self.Status == WF.DRAFT
    @property
    def IsPending(self) -> bool:   return self.Status == WF.PENDING
    @property
    def IsApproved(self) -> bool:  return self.Status == WF.APPROVED
    @property
    def IsRejected(self) -> bool:  return self.Status == WF.REJECTED
    @property
    def IsPosted(self) -> bool:    return self.Status == WF.POSTED

    def PrintHistory(self, lang: str = "ru") -> None:
        """Print workflow history to stdout (for 1S scripts)."""
        for entry in self.History:
            ts = entry.timestamp.strftime("%d.%m.%Y %H:%M")
            frm = WF.label(entry.from_status, lang)
            to  = WF.label(entry.to_status,   lang)
            line = f"  [{ts}]  {entry.actor}: {frm} → {to}"
            if entry.comment:
                line += f"   «{entry.comment}»"
            print(line, flush=True)

    # ── Russian aliases ───────────────────────────────────────────────
    Подать           = Submit
    Согласовать      = Approve
    Отклонить        = Reject
    НаДоработку      = Revise
    Отозвать         = Recall
    Переподать       = Resubmit
    Отменить         = Cancel
    МетаСтатус       = StatusLabel
    ВыводЖурнала     = PrintHistory

    # ── Ukrainian aliases ─────────────────────────────────────────────
    Надіслати         = Submit
    Погодити          = Approve
    Відхилити         = Reject
    НаДоопрацювання   = Revise
    Відкликати        = Recall
    Перенадіслати     = Resubmit
    Скасувати         = Cancel
    МетаСтатус        = StatusLabel
    ВивідЖурналу      = PrintHistory

    # ── Lowercase aliases (used by 1S transpiled scripts) ─────────────
    submit    = Submit
    approve   = Approve
    reject    = Reject
    revise    = Revise
    recall    = Recall
    resubmit  = Resubmit
    cancel    = Cancel
    post      = Post
    status    = property(lambda self: self.Status)
    is_draft  = property(lambda self: self.IsDraft)
    is_posted = property(lambda self: self.IsPosted)


# Constructor aliases
ДокументЗМаршрутом = WorkflowDocument   # Ukrainian
ДокументСМаршрутом = WorkflowDocument   # Russian
