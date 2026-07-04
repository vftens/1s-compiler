"""
1S: ERP Free Edition — Procurement & Purchasing Module (SAP MM/ME analogue).

Covers:
  • Supplier       — поставщик / постачальник
  • PurchaseRequest — заявка на закупку
  • PurchaseOrder  — заказ поставщику (многострочный)
  • ReceivingOrder  — приходная накладная (goods receipt)
  • ProcurementAnalytics — ABC-поставщики, экономия, SLA

Workflow: Draft → Approved → Sent → PartiallyReceived → Closed | Cancelled
"""
from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from .workflow import WorkflowDocument, WF


# ── Supplier ──────────────────────────────────────────────────────────────────

@dataclass
class Supplier:
    """Поставщик / Постачальник / Supplier."""
    name: str
    code: str
    rating: float = 5.0          # 1..10
    payment_days: int = 30       # credit days
    currency: str = "RUB"
    contact: str = ""
    country: str = ""

    # English aliases
    @property
    def Name(self): return self.name
    @property
    def Code(self): return self.code
    @property
    def Rating(self): return self.rating

    # Russian
    @property
    def Наименование(self): return self.name
    @property
    def Код(self): return self.code
    @property
    def Рейтинг(self): return self.rating
    @property
    def ДниОплаты(self): return self.payment_days

    # Ukrainian
    @property
    def Назва(self): return self.name
    @property
    def Рейтинґ(self): return self.rating

    def __repr__(self):
        return f"Supplier({self.code}, {self.name!r}, rating={self.rating})"


# ── Purchase Order Line ───────────────────────────────────────────────────────

@dataclass
class POLine:
    """Строка заказа / Рядок замовлення / PO Line."""
    item_code: str
    description: str
    qty: Decimal
    unit_price: Decimal
    unit: str = "шт"
    received_qty: Decimal = field(default_factory=lambda: Decimal("0"))

    @property
    def line_total(self) -> Decimal:
        return self.qty * self.unit_price

    @property
    def remaining_qty(self) -> Decimal:
        return self.qty - self.received_qty

    @property
    def is_closed(self) -> bool:
        return self.received_qty >= self.qty

    # Aliases
    @property
    def Сумма(self): return self.line_total
    @property
    def Сума(self): return self.line_total
    @property
    def Total(self): return self.line_total


# ── Purchase Order ────────────────────────────────────────────────────────────

class PurchaseOrder(WorkflowDocument):
    """
    ЗаказПоставщику / ЗамовленняПостачальнику / PurchaseOrder.

    Multi-line purchase order with partial receiving support.
    """
    STATUS_SENT     = "sent"
    STATUS_PARTIAL  = "partially_received"
    STATUS_CLOSED   = "closed"

    def __init__(self, number: str, supplier: Optional[Supplier] = None):
        super().__init__(number)
        self.supplier = supplier
        self.lines: list[POLine] = []
        self.order_date: datetime.date = datetime.date.today()
        self.delivery_date: Optional[datetime.date] = None
        self.warehouse: str = ""
        self.currency: str = supplier.currency if supplier else "RUB"
        self.po_status: str = WF.DRAFT

    def add_line(self, item_code: str, description: str,
                 qty: float, unit_price: float, unit: str = "шт") -> POLine:
        line = POLine(
            item_code=item_code,
            description=description,
            qty=Decimal(str(qty)),
            unit_price=Decimal(str(unit_price)),
            unit=unit,
        )
        self.lines.append(line)
        return line

    # RU/UK aliases
    def ДобавитьСтроку(self, code, desc, qty, price, unit="шт"):
        return self.add_line(code, desc, qty, price, unit)
    def ДодатиРядок(self, code, desc, qty, price, unit="шт"):
        return self.add_line(code, desc, qty, price, unit)
    def AddLine(self, code, desc, qty, price, unit="pcs"):
        return self.add_line(code, desc, qty, price, unit)

    @property
    def total_amount(self) -> Decimal:
        return sum((l.line_total for l in self.lines), Decimal("0"))

    @property
    def Итого(self): return self.total_amount
    @property
    def Підсумок(self): return self.total_amount
    @property
    def Total(self): return self.total_amount

    def receive(self, item_code: str, qty: float, actor: str = "warehouse") -> str:
        """Register partial or full goods receipt."""
        for line in self.lines:
            if line.item_code == item_code:
                line.received_qty += Decimal(str(qty))
                break
        all_closed = all(l.is_closed for l in self.lines)
        self.po_status = self.STATUS_CLOSED if all_closed else self.STATUS_PARTIAL
        return self.po_status

    # RU/UK
    def Принять(self, code, qty, actor="склад"): return self.receive(code, qty, actor)
    def Прийняти(self, code, qty, actor="склад"): return self.receive(code, qty, actor)
    def Receive(self, code, qty, actor="warehouse"): return self.receive(code, qty, actor)

    @property
    def completion_pct(self) -> float:
        if not self.lines:
            return 0.0
        total_q = sum(l.qty for l in self.lines)
        recv_q = sum(l.received_qty for l in self.lines)
        if total_q == 0:
            return 100.0
        return round(float(recv_q / total_q) * 100, 1)

    def report(self, lang: str = "ru") -> str:
        lbl = {
            "ru": ("Заказ поставщику", "Поставщик", "Дата", "Строк",
                   "Итого", "Выполнение", "Арт.", "Кол.", "Цена", "Сумма"),
            "uk": ("Замовлення постачальнику", "Постачальник", "Дата", "Рядків",
                   "Підсумок", "Виконання", "Арт.", "Кіл.", "Ціна", "Сума"),
            "en": ("Purchase Order", "Supplier", "Date", "Lines",
                   "Total", "Completion", "Code", "Qty", "Price", "Amount"),
        }.get(lang, ("PO", "Supplier", "Date", "Lines", "Total", "Done",
                     "Code", "Qty", "Price", "Amt"))
        lines = [
            f"{lbl[0]}: {self.number}",
            f"  {lbl[1]}: {self.supplier.name if self.supplier else '-'}",
            f"  {lbl[2]}: {self.order_date}",
            f"  {lbl[3]}: {len(self.lines)} | {lbl[5]}: {self.completion_pct}%",
            f"  {lbl[4]}: {self.total_amount} {self.currency}",
            f"  {'─'*50}",
            f"  {lbl[6]:<12} {lbl[7]:>8} {lbl[8]:>10} {lbl[9]:>12}",
        ]
        for l in self.lines:
            recv_mark = "✓" if l.is_closed else f"~{l.received_qty}"
            lines.append(f"  {l.item_code:<12} {l.qty:>8} {l.unit_price:>10} "
                         f"{l.line_total:>12}  {recv_mark}")
        return "\n".join(lines)

    def __repr__(self):
        return f"PurchaseOrder({self.number!r}, {self.supplier.name if self.supplier else '-'}, {self.total_amount})"


# ── Receiving Order ───────────────────────────────────────────────────────────

class ReceivingOrder(WorkflowDocument):
    """
    ПриходнаяНакладная / ПрибутковаНакладна / ReceivingOrder (Goods Receipt).
    """
    def __init__(self, number: str, po: Optional[PurchaseOrder] = None):
        super().__init__(number)
        self.purchase_order = po
        self.lines: list[dict] = []  # [{code, description, qty, price}]
        self.received_date: datetime.date = datetime.date.today()
        self.warehouse: str = ""

    def add_receipt(self, item_code: str, description: str,
                    qty: float, unit_price: float) -> None:
        self.lines.append({
            "code": item_code,
            "description": description,
            "qty": Decimal(str(qty)),
            "price": Decimal(str(unit_price)),
            "total": Decimal(str(qty)) * Decimal(str(unit_price)),
        })
        if self.purchase_order:
            self.purchase_order.receive(item_code, qty)

    def ДобавитьПриход(self, code, desc, qty, price):
        self.add_receipt(code, desc, qty, price)
    def ДодатиПрихід(self, code, desc, qty, price):
        self.add_receipt(code, desc, qty, price)
    def AddReceipt(self, code, desc, qty, price):
        self.add_receipt(code, desc, qty, price)

    @property
    def total_amount(self) -> Decimal:
        return sum(l["total"] for l in self.lines)

    def __repr__(self):
        return f"ReceivingOrder({self.number!r}, lines={len(self.lines)}, total={self.total_amount})"


# ── Procurement Analytics ─────────────────────────────────────────────────────

class ProcurementAnalytics:
    """
    АналитикаЗакупок / АналітикаЗакупівель / ProcurementAnalytics.
    Supplier performance, savings, top-spend analysis.
    """
    def __init__(self):
        self.orders: list[PurchaseOrder] = []

    def add(self, po: PurchaseOrder) -> None:
        self.orders.append(po)

    def Добавить(self, po): self.add(po)
    def Додати(self, po): self.add(po)

    @property
    def total_spend(self) -> Decimal:
        return sum((o.total_amount for o in self.orders), Decimal("0"))

    def by_supplier(self) -> list[tuple[str, Decimal, int]]:
        agg: dict[str, Decimal] = {}
        cnt: dict[str, int] = {}
        for o in self.orders:
            nm = o.supplier.name if o.supplier else "Unknown"
            agg[nm] = agg.get(nm, Decimal("0")) + o.total_amount
            cnt[nm] = cnt.get(nm, 0) + 1
        result = [(k, agg[k], cnt[k]) for k in sorted(agg, key=lambda x: -agg[x])]
        return result

    def top_supplier(self) -> Optional[str]:
        ranked = self.by_supplier()
        return ranked[0][0] if ranked else None

    def bar(self, value: float, max_val: float = 100, width: int = 20) -> str:
        filled = int(round(value / max_val * width)) if max_val else 0
        return "[" + "#" * filled + "-" * (width - filled) + "]"

    def dashboard(self, lang: str = "ru") -> str:
        lbl = {
            "ru": ("=== Аналитика закупок ===", "Заказов", "Поставщиков",
                   "Общий объём", "Топ поставщик", "Поставщик", "Сумма", "Заказов"),
            "uk": ("=== Аналітика закупівель ===", "Замовлень", "Постачальників",
                   "Загальний обсяг", "Топ постачальник", "Постачальник", "Сума", "Замовлень"),
            "en": ("=== Procurement Analytics ===", "Orders", "Suppliers",
                   "Total spend", "Top supplier", "Supplier", "Amount", "Orders"),
        }.get(lang, ("=== Procurement ===", "Orders", "Suppliers",
                     "Total", "Top", "Supplier", "Amount", "Orders"))
        by_sup = self.by_supplier()
        total = self.total_spend or Decimal("1")
        lines = [
            lbl[0],
            f"  {lbl[1]}: {len(self.orders)} | {lbl[2]}: {len(by_sup)}",
            f"  {lbl[3]}: {self.total_spend}",
            f"  {lbl[4]}: {self.top_supplier() or '-'}",
            f"  {'─'*40}",
            f"  {lbl[5]:<20} {lbl[6]:>12}  {lbl[7]:>4}",
        ]
        for name, amount, count in by_sup[:5]:
            pct = float(amount / total * 100)
            lines.append(f"  {name:<20} {amount:>12}  {count:>4}  {self.bar(pct, 100, 15)} {pct:.1f}%")
        return "\n".join(lines)


# ── Russian aliases ───────────────────────────────────────────────────────────
ЗаказПоставщику   = PurchaseOrder
ПриходнаяНакладная = ReceivingOrder
Поставщик         = Supplier
АналитикаЗакупок  = ProcurementAnalytics

# ── Ukrainian aliases ─────────────────────────────────────────────────────────
ЗамовленняПостачальнику = PurchaseOrder
ПрибутковаНакладна      = ReceivingOrder
Постачальник             = Supplier
АналітикаЗакупівель      = ProcurementAnalytics
