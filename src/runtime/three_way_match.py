"""
ThreeWayMatch — automatic PO + GR + SupplierInvoice reconciliation.
Tolerance-based matching with dispute workflow.
"""
from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from .procurement import PurchaseOrder, ReceivingOrder


# ── SupplierInvoice (lives here, not in procurement.py, to avoid circular imports) ──
@dataclass
class InvoiceLine:
    item_code:   str
    description: str
    quantity:    Decimal
    unit_price:  Decimal

    @property
    def line_total(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))

    # EN
    @property
    def Total(self):    return self.line_total
    @property
    def Qty(self):      return self.quantity
    @property
    def Price(self):    return self.unit_price
    # RU
    @property
    def Сумма(self):    return self.line_total
    @property
    def Количество(self): return self.quantity
    @property
    def Цена(self):     return self.unit_price
    # UK
    @property
    def Сума(self):     return self.line_total
    @property
    def Кількість(self): return self.quantity


class SupplierInvoice:
    """
    Vendor invoice from the supplier — third leg of the 3-way match.
    """

    def __init__(self, number: str, supplier_name: str = ""):
        self._number       = number
        self._supplier     = supplier_name
        self._date         = datetime.date.today()
        self._lines: List[InvoiceLine] = []

    def add_line(self, item_code: str, description: str,
                 quantity: float | Decimal, unit_price: float | Decimal) -> None:
        self._lines.append(InvoiceLine(
            item_code=item_code,
            description=description,
            quantity=Decimal(str(quantity)),
            unit_price=Decimal(str(unit_price)),
        ))

    @property
    def number(self):   return self._number
    @property
    def Number(self):   return self._number
    @property
    def Номер(self):    return self._number
    @property
    def supplier(self): return self._supplier
    @property
    def lines(self):    return list(self._lines)
    @property
    def Lines(self):    return list(self._lines)

    @property
    def total_amount(self) -> Decimal:
        return sum((ln.line_total for ln in self._lines), Decimal("0"))

    @property
    def Total(self):  return self.total_amount
    @property
    def Итого(self):  return self.total_amount
    @property
    def Підсумок(self): return self.total_amount

    def AddLine(self, code, desc, qty, price): return self.add_line(code, desc, qty, price)
    def ДобавитьСтроку(self, code, desc, qty, price): return self.add_line(code, desc, qty, price)
    def ДодатиРядок(self, code, desc, qty, price): return self.add_line(code, desc, qty, price)

    def __repr__(self) -> str:
        return f"SupplierInvoice({self._number!r}, total={self.total_amount})"


# ── Match result ─────────────────────────────────────────────────────────────
class MatchStatus(str, Enum):
    MATCHED    = "matched"
    MISMATCH   = "mismatch"
    PENDING_GR = "pending_gr"    # GR not yet received


@dataclass
class LineMatchResult:
    item_code:     str
    po_qty:        Decimal
    gr_qty:        Decimal
    inv_qty:       Decimal
    po_price:      Decimal
    inv_price:     Decimal
    qty_diff_pct:  Decimal   # % deviation
    price_diff_pct: Decimal
    qty_ok:        bool
    price_ok:      bool

    @property
    def ok(self) -> bool:
        return self.qty_ok and self.price_ok

    def __repr__(self) -> str:
        status = "OK" if self.ok else "MISMATCH"
        return (f"LineMatch({self.item_code}: {status}, "
                f"qty_diff={self.qty_diff_pct:.2f}%, price_diff={self.price_diff_pct:.2f}%)")


@dataclass
class MatchResult:
    po_number:      str
    gr_number:      str
    invoice_number: str
    status:         MatchStatus
    line_results:   List[LineMatchResult] = field(default_factory=list)
    blocking:       bool = False
    notes:          List[str] = field(default_factory=list)

    @property
    def matched(self) -> bool:  return self.status == MatchStatus.MATCHED
    @property
    def ok(self) -> bool:       return self.matched and not self.blocking
    @property
    def Matched(self): return self.matched
    @property
    def Blocked(self): return self.blocking
    @property
    def Совпадение(self): return self.matched
    @property
    def Заблокировано(self): return self.blocking
    @property
    def Збіг(self): return self.matched

    def report(self, lang: str = "en") -> str:
        hdr = {
            "en": ("3-WAY MATCH RESULT", "PO", "GR", "Invoice", "Status", "OVERALL"),
            "ru": ("РЕЗУЛЬТАТ ТРЁХСТОРОННЕГО СОПОСТАВЛЕНИЯ", "Заказ", "Приход", "Счёт", "Статус", "ИТОГ"),
            "uk": ("РЕЗУЛЬТАТ ТРИСТОРОННЬОГО ЗІСТАВЛЕННЯ", "Замовлення", "Прихід", "Рахунок", "Статус", "ПІДСУМОК"),
        }.get(lang, ("3-WAY MATCH RESULT", "PO", "GR", "Invoice", "Status", "OVERALL"))
        lines = [
            hdr[0], "=" * 50,
            f"  {hdr[1]}: {self.po_number}",
            f"  {hdr[2]}: {self.gr_number}",
            f"  {hdr[3]}: {self.invoice_number}",
            "-" * 50,
        ]
        for lr in self.line_results:
            status_str = "OK" if lr.ok else "MISMATCH"
            lines.append(
                f"  {lr.item_code:<15} {hdr[4]}: {status_str:<10} "
                f"qty_diff={lr.qty_diff_pct:.1f}%  price_diff={lr.price_diff_pct:.1f}%"
            )
        lines += ["=" * 50,
                  f"  {hdr[5]}: {self.status.value.upper()}",
                  f"  Blocking: {self.blocking}"]
        if self.notes:
            lines += [f"  Note: {n}" for n in self.notes]
        return "\n".join(lines)

    Report       = report
    Отчет        = report
    Звіт         = report


@dataclass
class MatchConfig:
    qty_tolerance_pct:   Decimal = Decimal("3")     # ±3%
    price_tolerance_pct: Decimal = Decimal("2")     # ±2%
    hard_block:          bool    = True


class ThreeWayMatch:
    """
    Reconciles PurchaseOrder ↔ ReceivingOrder ↔ SupplierInvoice.
    Returns MatchResult with line-by-line comparison.
    """

    def __init__(self, config: Optional[MatchConfig] = None):
        self._config = config or MatchConfig()

    def match(
        self,
        po:      PurchaseOrder,
        gr:      ReceivingOrder,
        invoice: SupplierInvoice,
    ) -> MatchResult:
        cfg = self._config

        # Build lookup: item_code → line data
        po_lines: Dict[str, dict] = {
            ln.item_code: {"qty": ln.qty, "price": ln.unit_price}
            for ln in po.lines
        }
        gr_qty: Dict[str, Decimal] = {}
        # ReceivingOrder.lines stores dicts with key "code" and "qty"
        for rcpt in gr.lines:
            code = rcpt.get("code", rcpt.get("item_code", ""))
            gr_qty[code] = gr_qty.get(code, Decimal("0")) + Decimal(str(rcpt.get("qty", rcpt.get("quantity", 0))))

        line_results: List[LineMatchResult] = []
        all_ok = True

        for inv_line in invoice.lines:
            code = inv_line.item_code
            po_data   = po_lines.get(code)
            received  = gr_qty.get(code, Decimal("0"))

            if po_data is None:
                all_ok = False
                line_results.append(LineMatchResult(
                    item_code=code,
                    po_qty=Decimal("0"),    gr_qty=received,
                    inv_qty=inv_line.quantity,
                    po_price=Decimal("0"),  inv_price=inv_line.unit_price,
                    qty_diff_pct=Decimal("100"), price_diff_pct=Decimal("100"),
                    qty_ok=False, price_ok=False,
                ))
                continue

            po_qty    = po_data["qty"]
            po_price  = po_data["price"]
            inv_qty   = inv_line.quantity
            inv_price = inv_line.unit_price

            # Quantity: compare received vs invoiced
            if inv_qty == 0:
                qty_diff_pct = Decimal("0")
            else:
                qty_diff_pct = abs(received - inv_qty) / inv_qty * 100

            # Price: compare PO price vs invoice price
            if po_price == 0:
                price_diff_pct = Decimal("0") if inv_price == 0 else Decimal("100")
            else:
                price_diff_pct = abs(inv_price - po_price) / po_price * 100

            qty_ok   = qty_diff_pct   <= cfg.qty_tolerance_pct
            price_ok = price_diff_pct <= cfg.price_tolerance_pct

            if not (qty_ok and price_ok):
                all_ok = False

            line_results.append(LineMatchResult(
                item_code=code,
                po_qty=po_qty, gr_qty=received, inv_qty=inv_qty,
                po_price=po_price, inv_price=inv_price,
                qty_diff_pct=qty_diff_pct.quantize(Decimal("0.01")),
                price_diff_pct=price_diff_pct.quantize(Decimal("0.01")),
                qty_ok=qty_ok, price_ok=price_ok,
            ))

        status  = MatchStatus.MATCHED if all_ok else MatchStatus.MISMATCH
        blocking = (not all_ok) and cfg.hard_block
        notes: List[str] = []
        if blocking:
            notes.append("Invoice payment BLOCKED — discrepancies exceed tolerance")

        return MatchResult(
            po_number=po.number, gr_number=gr.number,
            invoice_number=invoice.number,
            status=status, line_results=line_results,
            blocking=blocking, notes=notes,
        )

    def configure(self, qty_tol: float = 3.0, price_tol: float = 2.0,
                  hard_block: bool = True) -> None:
        self._config = MatchConfig(
            qty_tolerance_pct=Decimal(str(qty_tol)),
            price_tolerance_pct=Decimal(str(price_tol)),
            hard_block=hard_block,
        )

    # ── English method aliases ───────────────────────────────────────────────
    Match     = match
    Configure = configure

    # ── Russian method aliases ───────────────────────────────────────────────
    def Сопоставить(self, po, gr, invoice): return self.match(po, gr, invoice)
    def Настроить(self, qty=3.0, price=2.0, block=True): return self.configure(qty, price, block)

    # ── Ukrainian method aliases ─────────────────────────────────────────────
    def Зіставити(self, po, gr, invoice): return self.match(po, gr, invoice)
    def Налаштувати(self, qty=3.0, price=2.0, block=True): return self.configure(qty, price, block)

    def __repr__(self) -> str:
        return (f"ThreeWayMatch(qty_tol={self._config.qty_tolerance_pct}%, "
                f"price_tol={self._config.price_tolerance_pct}%, "
                f"hard_block={self._config.hard_block})")


# ── Trilingual class aliases ─────────────────────────────────────────────────
ТрёхстороннееСопоставление = ThreeWayMatch
ТристороннєЗіставлення     = ThreeWayMatch
СчётПоставщика             = SupplierInvoice
РахунокПостачальника       = SupplierInvoice
РезультатСопоставления     = MatchResult
РезультатЗіставлення       = MatchResult
