"""
1S: ERP Free Edition — Logistics & Transportation Module (SAP TM/SD analogue).

Covers:
  • TransportOrder  — планирование доставки
  • DeliveryRoute   — маршрут с точками остановки
  • Carrier         — перевозчик / carrier
  • LogisticsAnalytics — KPI доставок (SLA, % в срок, стоимость/км)

Workflow states: Draft → Planned → InTransit → Delivered | Failed | Cancelled

All classes expose Russian / Ukrainian / English aliases.
"""
from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from .workflow import WorkflowDocument, WF, WFEntry


# ── Status constants ──────────────────────────────────────────────────────────

class TM:
    """Transport Management status constants."""
    DRAFT      = "draft"
    PLANNED    = "planned"
    IN_TRANSIT = "in_transit"
    DELIVERED  = "delivered"
    FAILED     = "failed"
    CANCELLED  = "cancelled"

    _LABELS = {
        "ru": {
            DRAFT: "Черновик", PLANNED: "Запланирован",
            IN_TRANSIT: "В пути", DELIVERED: "Доставлен",
            FAILED: "Срыв", CANCELLED: "Отменён",
        },
        "uk": {
            DRAFT: "Чернетка", PLANNED: "Заплановано",
            IN_TRANSIT: "В дорозі", DELIVERED: "Доставлено",
            FAILED: "Зрив", CANCELLED: "Скасовано",
        },
        "en": {
            DRAFT: "Draft", PLANNED: "Planned",
            IN_TRANSIT: "In Transit", DELIVERED: "Delivered",
            FAILED: "Failed", CANCELLED: "Cancelled",
        },
    }

    @classmethod
    def label(cls, status: str, lang: str = "ru") -> str:
        return cls._LABELS.get(lang, cls._LABELS["en"]).get(status, status)


# ── Carrier ───────────────────────────────────────────────────────────────────

@dataclass
class Carrier:
    """Перевозчик / Перевізник / Carrier."""
    name: str
    code: str
    rate_per_km: Decimal = Decimal("0")      # cost per km
    max_weight_kg: Decimal = Decimal("20000")
    reliability: float = 1.0                 # 0..1, SLA compliance rate
    contact: str = ""

    # Russian
    @property
    def Наименование(self): return self.name
    @property
    def Код(self): return self.code
    @property
    def СтавкаЗаКм(self): return self.rate_per_km

    # Ukrainian
    @property
    def Назва(self): return self.name
    @property
    def ТарифЗаКм(self): return self.rate_per_km

    def __repr__(self):
        return f"Carrier({self.code}, {self.name!r}, {self.rate_per_km}/km)"


# ── Route Stop ────────────────────────────────────────────────────────────────

@dataclass
class RouteStop:
    """Точка маршрута / Точка маршруту / Route Stop."""
    sequence: int
    address: str
    planned_arrival: Optional[datetime.datetime] = None
    actual_arrival: Optional[datetime.datetime] = None
    weight_kg: Decimal = Decimal("0")
    completed: bool = False

    def arrive(self, ts: Optional[datetime.datetime] = None) -> None:
        self.actual_arrival = ts or datetime.datetime.now()
        self.completed = True

    @property
    def delay_minutes(self) -> Optional[float]:
        if self.planned_arrival and self.actual_arrival:
            delta = self.actual_arrival - self.planned_arrival
            return delta.total_seconds() / 60
        return None

    @property
    def on_time(self) -> bool:
        d = self.delay_minutes
        return d is not None and d <= 0


# ── Delivery Route ────────────────────────────────────────────────────────────

class DeliveryRoute:
    """
    МаршрутДоставки / МаршрутДоставки / DeliveryRoute.

    Multi-stop delivery route with distance and cost tracking.
    """
    def __init__(self, name: str, carrier: Optional[Carrier] = None):
        self.name = name
        self.carrier = carrier
        self.stops: list[RouteStop] = []
        self.total_distance_km: Decimal = Decimal("0")
        self.created_at: datetime.datetime = datetime.datetime.now()

    def add_stop(self, address: str, planned_arrival: Optional[datetime.datetime] = None,
                 weight_kg: float = 0) -> RouteStop:
        stop = RouteStop(
            sequence=len(self.stops) + 1,
            address=address,
            planned_arrival=planned_arrival,
            weight_kg=Decimal(str(weight_kg)),
        )
        self.stops.append(stop)
        return stop

    # RU / UK aliases
    def ДобавитьТочку(self, address, planned_arrival=None, weight_kg=0):
        return self.add_stop(address, planned_arrival, weight_kg)
    def ДодатиТочку(self, address, planned_arrival=None, weight_kg=0):
        return self.add_stop(address, planned_arrival, weight_kg)

    @property
    def transport_cost(self) -> Decimal:
        if self.carrier:
            rate = Decimal(str(self.carrier.rate_per_km))
            dist = Decimal(str(self.total_distance_km))
            return rate * dist
        return Decimal("0")

    @property
    def completed_stops(self) -> int:
        return sum(1 for s in self.stops if s.completed)

    @property
    def sla_ok(self) -> bool:
        done = [s for s in self.stops if s.completed]
        if not done:
            return True
        return all(s.on_time for s in done)

    def summary(self, lang: str = "ru") -> str:
        labels = {
            "ru": ("Маршрут", "км", "точек", "Перевозчик", "Стоимость"),
            "uk": ("Маршрут", "км", "точок", "Перевізник", "Вартість"),
            "en": ("Route",   "km", "stops", "Carrier",    "Cost"),
        }.get(lang, ("Route", "km", "stops", "Carrier", "Cost"))
        lines = [
            f"{labels[0]}: {self.name}",
            f"  {labels[4]}: {self.transport_cost} | {self.total_distance_km} {labels[1]}",
            f"  {labels[3]}: {self.carrier.name if self.carrier else '-'}",
            f"  {self.completed_stops}/{len(self.stops)} {labels[2]}",
        ]
        for s in self.stops:
            mark = "✓" if s.completed else "○"
            lines.append(f"  {mark} [{s.sequence}] {s.address}")
        return "\n".join(lines)

    def __repr__(self):
        return f"DeliveryRoute({self.name!r}, stops={len(self.stops)})"


# ── Transport Order ───────────────────────────────────────────────────────────

class TransportOrder(WorkflowDocument):
    """
    ТранспортнаяЗаявка / ТранспортнаЗаявка / TransportOrder.

    Inherits full WorkflowDocument state machine (Draft→Approved→Posted)
    and adds logistics-specific tracking.
    """
    def __init__(self, number: str, carrier: Optional[Carrier] = None,
                 route: Optional[DeliveryRoute] = None):
        super().__init__(number)
        self.carrier = carrier
        self.route = route
        self.cargo_description: str = ""
        self.weight_kg: Decimal = Decimal("0")
        self.volume_m3: Decimal = Decimal("0")
        self.transport_status: str = TM.DRAFT
        self.planned_date: Optional[datetime.date] = None
        self.actual_date: Optional[datetime.date] = None

    def plan(self, actor: str = "dispatcher") -> None:
        self.transport_status = TM.PLANNED
        self.submit(actor)

    def start_transit(self, actor: str = "driver") -> None:
        self.transport_status = TM.IN_TRANSIT

    def deliver(self, actor: str = "driver") -> None:
        self.transport_status = TM.DELIVERED
        self.actual_date = datetime.date.today()
        self.post(actor)

    def fail(self, reason: str = "", actor: str = "driver") -> None:
        self.transport_status = TM.FAILED
        self.reject(actor, reason)

    @property
    def transport_cost(self) -> Decimal:
        return self.route.transport_cost if self.route else Decimal("0")

    def report(self, lang: str = "ru") -> str:
        status_label = TM.label(self.transport_status, lang)
        lines = {
            "ru": [
                f"Транспортная заявка: {self.number}",
                f"  Статус:     {status_label}",
                f"  Перевозчик: {self.carrier.name if self.carrier else '-'}",
                f"  Груз:       {self.cargo_description}",
                f"  Вес:        {self.weight_kg} кг",
                f"  Стоимость:  {self.transport_cost}",
            ],
            "uk": [
                f"Транспортна заявка: {self.number}",
                f"  Статус:     {status_label}",
                f"  Перевізник: {self.carrier.name if self.carrier else '-'}",
                f"  Вантаж:     {self.cargo_description}",
                f"  Вага:       {self.weight_kg} кг",
                f"  Вартість:   {self.transport_cost}",
            ],
            "en": [
                f"Transport Order: {self.number}",
                f"  Status:   {status_label}",
                f"  Carrier:  {self.carrier.name if self.carrier else '-'}",
                f"  Cargo:    {self.cargo_description}",
                f"  Weight:   {self.weight_kg} kg",
                f"  Cost:     {self.transport_cost}",
            ],
        }.get(lang, [])
        return "\n".join(lines)

    def __repr__(self):
        return f"TransportOrder({self.number!r}, {self.transport_status})"


# ── Logistics Analytics ───────────────────────────────────────────────────────

class LogisticsAnalytics:
    """
    АналитикаЛогистики / АналітикаЛогістики / LogisticsAnalytics.

    Aggregates KPIs from a list of transport orders.
    """
    def __init__(self, orders: Optional[list[TransportOrder]] = None):
        self.orders: list[TransportOrder] = orders or []

    def add(self, order: TransportOrder) -> None:
        self.orders.append(order)

    # RU/UK aliases
    def Добавить(self, o): self.add(o)
    def Додати(self, o): self.add(o)

    @property
    def total_orders(self) -> int:
        return len(self.orders)

    @property
    def delivered(self) -> int:
        return sum(1 for o in self.orders if o.transport_status == TM.DELIVERED)

    @property
    def failed(self) -> int:
        return sum(1 for o in self.orders if o.transport_status == TM.FAILED)

    @property
    def sla_pct(self) -> float:
        done = [o for o in self.orders if o.transport_status in (TM.DELIVERED, TM.FAILED)]
        if not done:
            return 100.0
        ok = sum(1 for o in done if o.transport_status == TM.DELIVERED)
        return round(ok / len(done) * 100, 1)

    @property
    def total_cost(self) -> Decimal:
        return sum((o.transport_cost for o in self.orders), Decimal("0"))

    def bar(self, value: float, max_val: float = 100, width: int = 20) -> str:
        filled = int(round(value / max_val * width)) if max_val else 0
        return "[" + "#" * filled + "-" * (width - filled) + "]"

    def dashboard(self, lang: str = "ru") -> str:
        labels = {
            "ru": ("=== Аналитика логистики ===", "Всего заявок", "Доставлено",
                   "Срывов", "SLA выполнение", "Общая стоимость"),
            "uk": ("=== Аналітика логістики ===", "Всього заявок", "Доставлено",
                   "Зривів", "SLA виконання", "Загальна вартість"),
            "en": ("=== Logistics Analytics ===", "Total orders", "Delivered",
                   "Failed", "SLA compliance", "Total cost"),
        }.get(lang, ("=== Logistics Analytics ===", "Total", "Delivered",
                     "Failed", "SLA", "Cost"))
        sla = self.sla_pct
        lines = [
            labels[0],
            f"  {labels[1]}: {self.total_orders}",
            f"  {labels[2]}: {self.delivered}",
            f"  {labels[3]}: {self.failed}",
            f"  {labels[4]}: {self.bar(sla)} {sla}%",
            f"  {labels[5]}: {self.total_cost}",
        ]
        return "\n".join(lines)


# ── Russian aliases ───────────────────────────────────────────────────────────
ТранспортнаяЗаявка = TransportOrder
МаршрутДоставки   = DeliveryRoute
Перевозчик         = Carrier
АналитикаЛогистики = LogisticsAnalytics
СтатусТМ           = TM

# ── Ukrainian aliases ─────────────────────────────────────────────────────────
ТранспортнаЗаявка  = TransportOrder
МаршрутДоставки_UK = DeliveryRoute
Перевізник         = Carrier
АналітикаЛогістики = LogisticsAnalytics
