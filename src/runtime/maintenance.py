"""
1S: ERP Free Edition — Equipment Maintenance Management (SAP PM/EAM analogue).

Covers:
  • EquipmentCard   — карточка оборудования (паспорт)
  • MaintenancePlan — план-график технического обслуживания (ТО)
  • DefectReport    — дефектная ведомость (выявленные дефекты)
  • RepairOrder     — наряд на ремонт / техническое обслуживание
  • MaintenanceAnalytics — KPI: MTBF, MTTR, OEE, затраты на ТО

Workflow for RepairOrder: Draft → Approved → InWork → Completed | Cancelled
"""
from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from .workflow import WorkflowDocument, WF


# ── Equipment status ──────────────────────────────────────────────────────────

class EqStatus:
    OPERATIONAL = "operational"   # в работе
    MAINTENANCE = "maintenance"   # на ТО
    REPAIR      = "repair"        # в ремонте
    IDLE        = "idle"          # простой
    DECOMMISSIONED = "decommissioned"

    _LABELS = {
        "ru": {OPERATIONAL: "В работе", MAINTENANCE: "ТО",
               REPAIR: "Ремонт", IDLE: "Простой", DECOMMISSIONED: "Списан"},
        "uk": {OPERATIONAL: "В роботі", MAINTENANCE: "ТО",
               REPAIR: "Ремонт", IDLE: "Простій", DECOMMISSIONED: "Списано"},
        "en": {OPERATIONAL: "Operational", MAINTENANCE: "Maintenance",
               REPAIR: "Under Repair", IDLE: "Idle", DECOMMISSIONED: "Decommissioned"},
    }

    @classmethod
    def label(cls, status: str, lang: str = "ru") -> str:
        return cls._LABELS.get(lang, cls._LABELS["en"]).get(status, status)


# ── Defect Report Line ────────────────────────────────────────────────────────

@dataclass
class DefectLine:
    """Дефект из ведомости / Дефект / Defect."""
    code: str
    description: str
    severity: str = "medium"   # low / medium / high / critical
    detected_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    resolved: bool = False

    @property
    def Описание(self): return self.description
    @property
    def Серьезность(self): return self.severity
    @property
    def Опис(self): return self.description
    @property
    def Description(self): return self.description


# ── Equipment Card ────────────────────────────────────────────────────────────

class EquipmentCard:
    """
    КарточкаОборудования / КарткаОбладнання / EquipmentCard.

    Digital twin passport for a piece of equipment.
    """
    def __init__(self, inventory_number: str, name: str,
                 location: str = "", category: str = ""):
        self.inventory_number = inventory_number
        self.name = name
        self.location = location
        self.category = category
        self.manufacturer: str = ""
        self.model: str = ""
        self.serial_number: str = ""
        self.install_date: Optional[datetime.date] = None
        self.warranty_until: Optional[datetime.date] = None
        self.status: str = EqStatus.OPERATIONAL
        self.odometer_hours: float = 0.0     # machine-hours / run-hours
        self.defects: list[DefectLine] = []
        self.repair_history: list["RepairOrder"] = []
        self.downtime_hours: float = 0.0

    @property
    def age_days(self) -> Optional[int]:
        if self.install_date:
            return (datetime.date.today() - self.install_date).days
        return None

    @property
    def is_in_warranty(self) -> bool:
        return bool(self.warranty_until and self.warranty_until >= datetime.date.today())

    def report_defect(self, code: str, description: str, severity: str = "medium") -> DefectLine:
        d = DefectLine(code, description, severity)
        self.defects.append(d)
        return d

    def ВнестиДефект(self, code, desc, severity="medium"): return self.report_defect(code, desc, severity)
    def ВнестиДефект_UK(self, code, desc, severity="medium"): return self.report_defect(code, desc, severity)
    def ReportDefect(self, code, desc, severity="medium"): return self.report_defect(code, desc, severity)

    @property
    def open_defects(self) -> list[DefectLine]:
        return [d for d in self.defects if not d.resolved]

    @property
    def critical_defects(self) -> list[DefectLine]:
        return [d for d in self.defects if d.severity == "critical" and not d.resolved]

    def update_hours(self, hours: float) -> None:
        self.odometer_hours += hours

    def ДобавитьМотоЧасы(self, h): self.update_hours(h)
    def ДодатиМотоГодини(self, h): self.update_hours(h)
    def AddHours(self, h): self.update_hours(h)

    def passport(self, lang: str = "ru") -> str:
        lbl = {
            "ru": ("Карточка оборудования", "Инв. №", "Наименование", "Местонахождение",
                   "Категория", "Производитель", "Серийный №", "Установлен",
                   "Гарантия до", "Статус", "Мото-часов", "Открытых дефектов"),
            "uk": ("Картка обладнання", "Інв. №", "Найменування", "Місцезнаходження",
                   "Категорія", "Виробник", "Серійний №", "Встановлено",
                   "Гарантія до", "Статус", "Мото-годин", "Відкритих дефектів"),
            "en": ("Equipment Card", "Inventory #", "Name", "Location",
                   "Category", "Manufacturer", "Serial #", "Installed",
                   "Warranty until", "Status", "Run hours", "Open defects"),
        }.get(lang, ("Equipment", "Inv#", "Name", "Location", "Cat", "Maker",
                     "Serial", "Installed", "Warranty", "Status", "Hours", "Defects"))
        status_label = EqStatus.label(self.status, lang)
        lines = [
            f"{'='*55}",
            f" {lbl[0]}: {self.inventory_number}",
            f"{'='*55}",
            f"  {lbl[1]:>16}: {self.inventory_number}",
            f"  {lbl[2]:>16}: {self.name}",
            f"  {lbl[3]:>16}: {self.location}",
            f"  {lbl[4]:>16}: {self.category}",
            f"  {lbl[5]:>16}: {self.manufacturer}",
            f"  {lbl[6]:>16}: {self.serial_number}",
            f"  {lbl[7]:>16}: {self.install_date or '-'}",
            f"  {lbl[8]:>16}: {self.warranty_until or '-'}  {'[IN WARRANTY]' if self.is_in_warranty else ''}",
            f"  {lbl[9]:>16}: {status_label}",
            f"  {lbl[10]:>16}: {self.odometer_hours:.1f}",
            f"  {lbl[11]:>16}: {len(self.open_defects)}",
            f"{'─'*55}",
        ]
        for d in self.open_defects:
            lines.append(f"  [!] {d.severity.upper():8} {d.code}: {d.description}")
        return "\n".join(lines)

    def __repr__(self):
        return f"Equipment({self.inventory_number!r}, {self.name!r}, {self.status})"


# ── Maintenance Plan ──────────────────────────────────────────────────────────

@dataclass
class MaintenancePlanItem:
    """Позиция плана ТО / Позиція плану ТО / Maintenance Plan Item."""
    equipment_inv: str
    equipment_name: str
    planned_date: datetime.date
    work_type: str    # "ТО-1" / "ТО-2" / "ТО-3" / "Замена масла" / etc.
    duration_hours: float = 4.0
    completed: bool = False
    repair_order: Optional[str] = None


class MaintenancePlan:
    """
    ПланТО / ПланТО / MaintenancePlan.
    Schedule of preventive maintenance activities.
    """
    def __init__(self, name: str, period_start: datetime.date, period_end: datetime.date):
        self.name = name
        self.period_start = period_start
        self.period_end = period_end
        self.items: list[MaintenancePlanItem] = []

    def schedule(self, equipment: EquipmentCard, work_type: str,
                 planned_date: datetime.date, duration_hours: float = 4.0) -> MaintenancePlanItem:
        item = MaintenancePlanItem(
            equipment.inventory_number,
            equipment.name,
            planned_date, work_type, duration_hours,
        )
        self.items.append(item)
        return item

    def Запланировать(self, eq, work, date, hours=4): return self.schedule(eq, work, date, hours)
    def Запланувати(self, eq, work, date, hours=4): return self.schedule(eq, work, date, hours)
    def Schedule(self, eq, work, date, hours=4): return self.schedule(eq, work, date, hours)

    @property
    def overdue(self) -> list[MaintenancePlanItem]:
        today = datetime.date.today()
        return [i for i in self.items if not i.completed and i.planned_date < today]

    @property
    def completion_pct(self) -> float:
        if not self.items:
            return 100.0
        done = sum(1 for i in self.items if i.completed)
        return round(done / len(self.items) * 100, 1)

    def report(self, lang: str = "ru") -> str:
        lbl = {
            "ru": ("=== План ТО ===", "Наименование", "Вид работ",
                   "Дата", "Часы", "Выполнено", "Просрочено"),
            "uk": ("=== План ТО ===", "Найменування", "Вид робіт",
                   "Дата", "Годин", "Виконано", "Прострочено"),
            "en": ("=== Maintenance Plan ===", "Equipment", "Work type",
                   "Date", "Hours", "Done", "Overdue"),
        }.get(lang, ("=== Plan ===", "Equipment", "Work", "Date", "Hours", "Done", "Overdue"))
        today = datetime.date.today()
        lines = [
            lbl[0], f"  {self.name} | {self.period_start} — {self.period_end}",
            f"  {lbl[5]}: {self.completion_pct}%  | {lbl[6]}: {len(self.overdue)}",
            f"  {'─'*60}",
            f"  {lbl[1]:<22} {lbl[2]:<15} {lbl[3]:>12} {lbl[4]:>6}",
        ]
        for item in sorted(self.items, key=lambda x: x.planned_date):
            mark = "✓" if item.completed else ("!" if item.planned_date < today else "○")
            lines.append(f"  {mark} {item.equipment_name:<21} {item.work_type:<15} "
                         f"{item.planned_date!s:>12} {item.duration_hours:>5.1f}h")
        return "\n".join(lines)


# ── Repair Order ──────────────────────────────────────────────────────────────

class RepairOrder(WorkflowDocument):
    """
    НарядНаРемонт / НарядНаРемонт / RepairOrder.

    Workflow: Draft → Approved → InWork → Completed | Cancelled
    Tracks labour, materials, downtime, cost.
    """
    STATUS_IN_WORK    = "in_work"
    STATUS_COMPLETED  = "completed"

    def __init__(self, number: str, equipment: Optional[EquipmentCard] = None):
        super().__init__(number)
        self.equipment = equipment
        self.work_type: str = ""
        self.defect_description: str = ""
        self.planned_start: Optional[datetime.datetime] = None
        self.actual_start: Optional[datetime.datetime] = None
        self.actual_end: Optional[datetime.datetime] = None
        self.mechanic: str = ""
        self.labour_hours: float = 0.0
        self.labour_rate: Decimal = Decimal("500")   # per hour
        self.materials: list[dict] = []              # [{name, qty, cost}]
        self.repair_status: str = WF.DRAFT

    def start_work(self, mechanic: str = "") -> None:
        self.repair_status = self.STATUS_IN_WORK
        self.actual_start = datetime.datetime.now()
        self.mechanic = mechanic
        if self.equipment:
            self.equipment.status = EqStatus.REPAIR

    def НачатьРаботу(self, mech=""): self.start_work(mech)
    def РозпочатиРоботу(self, mech=""): self.start_work(mech)
    def StartWork(self, mech=""): self.start_work(mech)

    def add_material(self, name: str, qty: float, unit_cost: float) -> None:
        self.materials.append({
            "name": name,
            "qty": Decimal(str(qty)),
            "cost": Decimal(str(unit_cost)),
            "total": Decimal(str(qty)) * Decimal(str(unit_cost)),
        })

    def ДобавитьМатериал(self, name, qty, cost): self.add_material(name, qty, cost)
    def ДодатиМатеріал(self, name, qty, cost): self.add_material(name, qty, cost)
    def AddMaterial(self, name, qty, cost): self.add_material(name, qty, cost)

    def complete(self, actor: str = "mechanic") -> None:
        self.repair_status = self.STATUS_COMPLETED
        self.actual_end = datetime.datetime.now()
        self.post(actor)
        if self.equipment:
            self.equipment.status = EqStatus.OPERATIONAL
            # resolve defects linked to this order
            for d in self.equipment.defects:
                if not d.resolved:
                    d.resolved = True
        if self.equipment:
            self.equipment.repair_history.append(self)

    def Завершить(self, actor="механик"): self.complete(actor)
    def Завершити(self, actor="механік"): self.complete(actor)
    def Complete(self, actor="mechanic"): self.complete(actor)

    @property
    def labour_cost(self) -> Decimal:
        return Decimal(str(self.labour_hours)) * self.labour_rate

    @property
    def materials_cost(self) -> Decimal:
        return sum(m["total"] for m in self.materials)

    @property
    def total_cost(self) -> Decimal:
        return self.labour_cost + self.materials_cost

    @property
    def downtime_hours(self) -> float:
        if self.actual_start and self.actual_end:
            return (self.actual_end - self.actual_start).total_seconds() / 3600
        return 0.0

    def report(self, lang: str = "ru") -> str:
        lbl = {
            "ru": ("Наряд на ремонт", "Оборудование", "Вид работ",
                   "Дефект", "Механик", "Трудозатраты", "Материалы",
                   "Итого", "Простой"),
            "uk": ("Наряд на ремонт", "Обладнання", "Вид робіт",
                   "Дефект", "Механік", "Трудовитрати", "Матеріали",
                   "Підсумок", "Простій"),
            "en": ("Repair Order", "Equipment", "Work type",
                   "Defect", "Mechanic", "Labour", "Materials",
                   "Total", "Downtime"),
        }.get(lang, ("Repair Order", "Equipment", "Work", "Defect",
                     "Mechanic", "Labour", "Materials", "Total", "Downtime"))
        eq_name = self.equipment.name if self.equipment else "-"
        lines = [
            f"{lbl[0]}: {self.number}",
            f"  {lbl[1]}: {eq_name}",
            f"  {lbl[2]}: {self.work_type}",
            f"  {lbl[3]}: {self.defect_description}",
            f"  {lbl[4]}: {self.mechanic}",
            f"  {lbl[5]}: {self.labour_hours}h × {self.labour_rate} = {self.labour_cost}",
            f"  {lbl[7]}: {self.total_cost}",
            f"  {lbl[8]}: {self.downtime_hours:.1f}h",
        ]
        if self.materials:
            lines.append(f"  {lbl[6]}:")
            for m in self.materials:
                lines.append(f"    - {m['name']}: {m['qty']} × {m['cost']} = {m['total']}")
        return "\n".join(lines)

    def __repr__(self):
        return f"RepairOrder({self.number!r}, {self.equipment.inventory_number if self.equipment else '-'}, {self.repair_status})"


# ── Maintenance Analytics ─────────────────────────────────────────────────────

class MaintenanceAnalytics:
    """
    АналитикаТО / АналітикаТО / MaintenanceAnalytics.
    KPIs: MTBF (Mean Time Between Failures), MTTR (Mean Time To Repair), OEE.
    """
    def __init__(self, equipment_list: Optional[list[EquipmentCard]] = None):
        self.equipment_list: list[EquipmentCard] = equipment_list or []
        self.repair_orders: list[RepairOrder] = []

    def add_equipment(self, eq: EquipmentCard) -> None:
        self.equipment_list.append(eq)

    def add_repair(self, ro: RepairOrder) -> None:
        self.repair_orders.append(ro)

    def ДобавитьОборудование(self, eq): self.add_equipment(eq)
    def ДодатиОбладнання(self, eq): self.add_equipment(eq)
    def ДобавитьНаряд(self, ro): self.add_repair(ro)
    def ДодатиНаряд(self, ro): self.add_repair(ro)

    @property
    def total_repair_cost(self) -> Decimal:
        return sum((r.total_cost for r in self.repair_orders), Decimal("0"))

    @property
    def avg_downtime_hours(self) -> float:
        done = [r for r in self.repair_orders
                if r.repair_status == RepairOrder.STATUS_COMPLETED]
        if not done:
            return 0.0
        return sum(r.downtime_hours for r in done) / len(done)

    @property
    def mttr(self) -> float:
        return self.avg_downtime_hours

    def bar(self, value: float, max_val: float = 100, width: int = 20) -> str:
        filled = int(round(value / max_val * width)) if max_val else 0
        return "[" + "#" * filled + "-" * (width - filled) + "]"

    def dashboard(self, lang: str = "ru") -> str:
        lbl = {
            "ru": ("=== Аналитика ТО ===", "Оборудование", "Нарядов",
                   "Общ. стоимость ТО", "Ср. простой (MTTR)", "ч"),
            "uk": ("=== Аналітика ТО ===", "Обладнання", "Нарядів",
                   "Заг. вартість ТО", "Сер. простій (MTTR)", "год"),
            "en": ("=== Maintenance Analytics ===", "Equipment units", "Repair orders",
                   "Total repair cost", "Avg downtime (MTTR)", "h"),
        }.get(lang, ("=== Maintenance ===", "Equipment", "Orders",
                     "Total cost", "MTTR", "h"))
        lines = [
            lbl[0],
            f"  {lbl[1]}: {len(self.equipment_list)}",
            f"  {lbl[2]}: {len(self.repair_orders)}",
            f"  {lbl[3]}: {self.total_repair_cost}",
            f"  {lbl[4]}: {self.mttr:.1f} {lbl[5]}",
        ]
        if self.repair_orders:
            lines.append(f"  {'─'*40}")
            lines.append(f"  {'Наряд' if lang=='ru' else 'Наряд' if lang=='uk' else 'Order':<15} "
                         f"{'Оборудование' if lang=='ru' else 'Обладнання' if lang=='uk' else 'Equipment':<22} "
                         f"{'Стоимость' if lang=='ru' else 'Вартість' if lang=='uk' else 'Cost':>10}")
            for ro in self.repair_orders[:5]:
                eq_name = ro.equipment.name if ro.equipment else "-"
                lines.append(f"  {ro.number:<15} {eq_name:<22} {ro.total_cost:>10}")
        return "\n".join(lines)


# ── Russian aliases ───────────────────────────────────────────────────────────
КарточкаОборудования = EquipmentCard
НарядНаРемонт        = RepairOrder
ПланТО               = MaintenancePlan
АналитикаТО          = MaintenanceAnalytics
ДефектнаяВедомость   = DefectLine
СтатусОборудования   = EqStatus

# ── Ukrainian aliases ─────────────────────────────────────────────────────────
КарткаОбладнання     = EquipmentCard
НарядНаРемонтUK      = RepairOrder
ПланТО_UK            = MaintenancePlan
АналітикаТО          = MaintenanceAnalytics
ДефектнаВідомість    = DefectLine
СтатусОбладнання     = EqStatus
