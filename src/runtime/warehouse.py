"""
1S: ERP Free Edition — Warehouse Management & Analytics (SAP WM/EWM analogue).

Covers:
  • WarehouseCell    — ячейка склада (zone/row/cell addressing)
  • StockItem        — остаток товара в ячейке
  • StockMovement    — движение товара (receipt / transfer / issue)
  • InventoryCheck   — инвентаризация
  • ABCAnalysis      — ABC-классификация товаров по оборачиваемости
  • WarehouseAnalytics — KPI: заполненность, оборачиваемость, потери

All classes expose RU / UK / EN aliases.
"""
from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


# ── Movement types ────────────────────────────────────────────────────────────

class MoveType:
    RECEIPT   = "receipt"    # приход  / прихід
    ISSUE     = "issue"      # расход  / видаток
    TRANSFER  = "transfer"   # перемещение / переміщення
    WRITE_OFF = "write_off"  # списание / списання

    _LABELS = {
        "ru": {RECEIPT: "Приход", ISSUE: "Расход",
               TRANSFER: "Перемещение", WRITE_OFF: "Списание"},
        "uk": {RECEIPT: "Прихід", ISSUE: "Видаток",
               TRANSFER: "Переміщення", WRITE_OFF: "Списання"},
        "en": {RECEIPT: "Receipt", ISSUE: "Issue",
               TRANSFER: "Transfer", WRITE_OFF: "Write-off"},
    }

    @classmethod
    def label(cls, move_type: str, lang: str = "ru") -> str:
        return cls._LABELS.get(lang, cls._LABELS["en"]).get(move_type, move_type)


# ── Warehouse Cell ────────────────────────────────────────────────────────────

@dataclass
class WarehouseCell:
    """ЯчейкаСклада / КомірkaСкладу / WarehouseCell."""
    zone: str     # A, B, C …
    row: int
    cell: int
    capacity: Decimal = Decimal("1000")   # max weight / volume units

    @property
    def address(self) -> str:
        return f"{self.zone}{self.row:02d}-{self.cell:02d}"

    @property
    def Адрес(self): return self.address
    @property
    def Адреса(self): return self.address
    @property
    def Address(self): return self.address

    def __repr__(self):
        return f"Cell({self.address}, cap={self.capacity})"

    def __hash__(self): return hash(self.address)
    def __eq__(self, o): return isinstance(o, WarehouseCell) and self.address == o.address


# ── Stock Movement ────────────────────────────────────────────────────────────

@dataclass
class StockMovement:
    """ДвижениеТовара / РухТовару / StockMovement."""
    date: datetime.datetime
    move_type: str
    item_code: str
    description: str
    qty: Decimal
    unit_cost: Decimal
    cell: Optional[WarehouseCell] = None
    target_cell: Optional[WarehouseCell] = None
    document: str = ""

    @property
    def total_cost(self) -> Decimal:
        return self.qty * self.unit_cost

    @property
    def ТипДвижения(self): return self.move_type
    @property
    def Количество(self): return self.qty
    @property
    def Сумма(self): return self.total_cost


# ── Stock Item (balance in cell) ──────────────────────────────────────────────

@dataclass
class StockItem:
    """Остаток товара в ячейке / Залишок товару / Stock balance."""
    item_code: str
    description: str
    qty: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")
    cell: Optional[WarehouseCell] = None
    unit: str = "шт"

    @property
    def total_value(self) -> Decimal:
        return self.qty * self.unit_cost

    @property
    def Стоимость(self): return self.total_value
    @property
    def Вартість(self): return self.total_value
    @property
    def Value(self): return self.total_value

    def __repr__(self):
        return f"Stock({self.item_code}, qty={self.qty}, val={self.total_value})"


# ── Warehouse ─────────────────────────────────────────────────────────────────

class Warehouse:
    """
    Склад / Склад / Warehouse.

    Central hub: maintains stock balances and movement journal.
    """
    def __init__(self, name: str, code: str = ""):
        self.name = name
        self.code = code
        self.cells: list[WarehouseCell] = []
        self.stock: dict[str, StockItem] = {}      # item_code → StockItem
        self.movements: list[StockMovement] = []

    def add_cell(self, zone: str, row: int, cell: int,
                 capacity: float = 1000) -> WarehouseCell:
        c = WarehouseCell(zone, row, cell, Decimal(str(capacity)))
        self.cells.append(c)
        return c

    def ДобавитьЯчейку(self, zone, row, cell, cap=1000): return self.add_cell(zone, row, cell, cap)
    def ДодатиКомірку(self, zone, row, cell, cap=1000): return self.add_cell(zone, row, cell, cap)
    def AddCell(self, zone, row, cell, cap=1000): return self.add_cell(zone, row, cell, cap)

    def receive(self, item_code: str, description: str,
                qty: float, unit_cost: float,
                cell: Optional[WarehouseCell] = None,
                document: str = "") -> StockMovement:
        q = Decimal(str(qty))
        c = Decimal(str(unit_cost))
        if item_code not in self.stock:
            self.stock[item_code] = StockItem(item_code, description, Decimal("0"), c, cell)
        self.stock[item_code].qty += q
        self.stock[item_code].unit_cost = c
        mv = StockMovement(datetime.datetime.now(), MoveType.RECEIPT,
                           item_code, description, q, c, cell, document=document)
        self.movements.append(mv)
        return mv

    def issue(self, item_code: str, qty: float, document: str = "") -> Optional[StockMovement]:
        q = Decimal(str(qty))
        if item_code not in self.stock or self.stock[item_code].qty < q:
            return None   # insufficient stock
        si = self.stock[item_code]
        si.qty -= q
        mv = StockMovement(datetime.datetime.now(), MoveType.ISSUE,
                           item_code, si.description, q, si.unit_cost,
                           si.cell, document=document)
        self.movements.append(mv)
        return mv

    # RU/UK/EN aliases for receive / issue
    def Принять(self, code, desc, qty, cost, cell=None, doc=""):
        return self.receive(code, desc, qty, cost, cell, doc)
    def Прийняти(self, code, desc, qty, cost, cell=None, doc=""):
        return self.receive(code, desc, qty, cost, cell, doc)
    def Receive(self, code, desc, qty, cost, cell=None, doc=""):
        return self.receive(code, desc, qty, cost, cell, doc)
    def Отпустить(self, code, qty, doc=""): return self.issue(code, qty, doc)
    def Відпустити(self, code, qty, doc=""): return self.issue(code, qty, doc)
    def Issue(self, code, qty, doc=""): return self.issue(code, qty, doc)

    @property
    def total_stock_value(self) -> Decimal:
        return sum(s.total_value for s in self.stock.values())

    @property
    def stock_count(self) -> int:
        return len([s for s in self.stock.values() if s.qty > 0])

    def get_balance(self, item_code: str) -> Decimal:
        return self.stock[item_code].qty if item_code in self.stock else Decimal("0")

    def ОстатокТовара(self, code): return self.get_balance(code)
    def ЗалишокТовару(self, code): return self.get_balance(code)
    def Balance(self, code): return self.get_balance(code)

    def turnover_by_item(self) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        for mv in self.movements:
            if mv.move_type == MoveType.ISSUE:
                result[mv.item_code] = result.get(mv.item_code, Decimal("0")) + mv.total_cost
        return result

    def __repr__(self):
        return f"Warehouse({self.name!r}, items={self.stock_count}, value={self.total_stock_value})"


# ── ABC Analysis ──────────────────────────────────────────────────────────────

class ABCAnalysis:
    """
    АВС_Анализ / АВС_Аналіз / ABCAnalysis.

    Pareto classification:
      A = top 80% of turnover
      B = next 15%
      C = remaining 5%
    """
    def __init__(self, warehouse: Warehouse):
        self.warehouse = warehouse
        self._result: list[tuple[str, str, Decimal, str]] = []  # (code, desc, turnover, class)

    def run(self) -> None:
        turnover = self.warehouse.turnover_by_item()
        total = sum(turnover.values()) or Decimal("1")
        ranked = sorted(turnover.items(), key=lambda x: -x[1])
        cumulative = Decimal("0")
        result = []
        for code, amount in ranked:
            desc = self.warehouse.stock.get(code, StockItem(code, code)).description
            cumulative += amount
            pct = cumulative / total
            cls = "A" if pct <= Decimal("0.80") else ("B" if pct <= Decimal("0.95") else "C")
            result.append((code, desc, amount, cls))
        self._result = result

    # RU/UK
    def Выполнить(self): self.run()
    def Виконати(self): self.run()
    def Run(self): self.run()

    def bar(self, pct: float, width: int = 15) -> str:
        filled = int(round(pct * width))
        return "[" + "#" * filled + "-" * (width - filled) + "]"

    def report(self, lang: str = "ru") -> str:
        lbl = {
            "ru": ("=== ABC-анализ склада ===", "Артикул", "Наименование",
                   "Оборот", "Класс"),
            "uk": ("=== ABC-аналіз складу ===", "Артикул", "Найменування",
                   "Оборот", "Клас"),
            "en": ("=== ABC Warehouse Analysis ===", "Code", "Description",
                   "Turnover", "Class"),
        }.get(lang, ("=== ABC ===", "Code", "Name", "Turnover", "Class"))
        if not self._result:
            self.run()
        lines = [
            lbl[0],
            f"  {lbl[1]:<14} {lbl[2]:<20} {lbl[3]:>12}  {lbl[4]}",
            "  " + "─" * 56,
        ]
        for code, desc, amount, cls in self._result:
            lines.append(f"  {code:<14} {desc:<20} {amount:>12}  [{cls}]")
        total = sum(r[2] for r in self._result)
        lines.append("  " + "─" * 56)
        lines.append(f"  {'TOTAL':<14} {'':<20} {total:>12}")
        return "\n".join(lines)


# ── Inventory Check ───────────────────────────────────────────────────────────

@dataclass
class InventoryCheckLine:
    item_code: str
    description: str
    book_qty: Decimal
    actual_qty: Decimal

    @property
    def variance(self) -> Decimal:
        return self.actual_qty - self.book_qty

    @property
    def surplus(self) -> bool:
        return self.variance > 0

    @property
    def shortage(self) -> bool:
        return self.variance < 0


class InventoryCheck:
    """
    Инвентаризация / Інвентаризація / InventoryCheck.
    Compare book balances vs physical count.
    """
    def __init__(self, warehouse: Warehouse, date: Optional[datetime.date] = None):
        self.warehouse = warehouse
        self.date = date or datetime.date.today()
        self.lines: list[InventoryCheckLine] = []

    def count(self, item_code: str, actual_qty: float) -> InventoryCheckLine:
        book = self.warehouse.get_balance(item_code)
        desc = self.warehouse.stock.get(item_code, StockItem(item_code, item_code)).description
        line = InventoryCheckLine(item_code, desc, book, Decimal(str(actual_qty)))
        self.lines.append(line)
        return line

    def Пересчитать(self, code, qty): return self.count(code, qty)
    def Перерахувати(self, code, qty): return self.count(code, qty)
    def Count(self, code, qty): return self.count(code, qty)

    def report(self, lang: str = "ru") -> str:
        lbl = {
            "ru": ("=== Инвентаризация ===", "Артикул", "Наименование",
                   "Книжн.", "Факт", "Откл."),
            "uk": ("=== Інвентаризація ===", "Артикул", "Найменування",
                   "Книжн.", "Факт", "Відх."),
            "en": ("=== Inventory Check ===", "Code", "Description",
                   "Book", "Actual", "Variance"),
        }.get(lang, ("=== Inventory ===", "Code", "Desc", "Book", "Actual", "Var"))
        lines = [
            lbl[0], f"  Date: {self.date}",
            f"  {lbl[1]:<14} {lbl[2]:<20} {lbl[3]:>8} {lbl[4]:>8} {lbl[5]:>8}",
            "  " + "─" * 62,
        ]
        for l in self.lines:
            mark = " " if l.variance == 0 else ("+" if l.surplus else "!")
            lines.append(f"  {l.item_code:<14} {l.description:<20} "
                         f"{l.book_qty:>8} {l.actual_qty:>8} {l.variance:>8} {mark}")
        return "\n".join(lines)


# ── Russian aliases ───────────────────────────────────────────────────────────
Склад             = Warehouse
ЯчейкаСклада      = WarehouseCell
ДвижениеТовара    = StockMovement
АВС_Анализ        = ABCAnalysis
Инвентаризация    = InventoryCheck
ТипДвижения       = MoveType

# ── Ukrainian aliases ─────────────────────────────────────────────────────────
КомірkаСкладу     = WarehouseCell
РухТовару         = StockMovement
АВС_Аналіз        = ABCAnalysis
Інвентаризація    = InventoryCheck
ТипРуху           = MoveType
