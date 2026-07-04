# 1S: ERP Free Edition — ERP Modules Reference

> Sprint 9 — SAP-comparable ERP modules via Workflow engine.
> All modules support **Russian 🇷🇺 / Ukrainian 🇺🇦 / English** keywords.

---

## Overview

| Module | File | SAP Analogue | Key Classes |
|--------|------|-------------|-------------|
| [Procurement](#procurement-sap-mm) | `runtime/procurement.py` | MM / ME | `PurchaseOrder`, `ReceivingOrder`, `Supplier` |
| [Warehouse](#warehouse-sap-wmewm) | `runtime/warehouse.py` | WM / EWM | `Warehouse`, `ABCAnalysis`, `InventoryCheck` |
| [Logistics](#logistics-sap-tmsd) | `runtime/logistics.py` | TM / SD | `TransportOrder`, `DeliveryRoute`, `Carrier` |
| [Payroll](#payroll-sap-hcm) | *(built-in arithmetic)* | HCM / PY | `Structure`, `Array` + formulas |
| [Maintenance](#maintenance-sap-pmeam) | `runtime/maintenance.py` | PM / EAM | `EquipmentCard`, `RepairOrder`, `MaintenancePlan` |
| [Workflow Engine](#workflow-engine) | `runtime/workflow.py` | BPM / WF | `WorkflowDocument` |

All document classes inherit **WorkflowDocument** and follow the same approval cycle:

```
Draft → Pending → Approved → Posted
          ↓
       Rejected / Revision
```

---

## Workflow Engine

**File:** `src/runtime/workflow.py`

Every business document that needs approval extends `WorkflowDocument`.

### State constants (`WF`)

| Constant | Value | RU label | EN label |
|----------|-------|----------|----------|
| `WF.DRAFT` | `"draft"` | Черновик | Draft |
| `WF.PENDING` | `"pending"` | На согласовании | Pending Approval |
| `WF.APPROVED` | `"approved"` | Согласован | Approved |
| `WF.REJECTED` | `"rejected"` | Отклонён | Rejected |
| `WF.POSTED` | `"posted"` | Проведён | Posted |
| `WF.CANCELLED` | `"cancelled"` | Отменён | Cancelled |
| `WF.REVISION` | `"revision"` | На доработке | Needs Revision |

### WorkflowDocument methods

Every document class exposes these in three languages:

| English | Russian | Ukrainian | Description |
|---------|---------|-----------|-------------|
| `submit(actor, comment)` | `Подать` | `Надіслати` | Draft → Pending |
| `approve(actor, comment)` | `Согласовать` | `Погодити` | Pending → Approved |
| `reject(actor, reason)` | `Отклонить` | `Відхилити` | Pending → Rejected |
| `post(actor)` | `Провести` | `Провести` | Approved → Posted |
| `cancel(actor, reason)` | `Отменить` | `Скасувати` | Any → Cancelled |
| `recall(actor)` | `Отозвать` | `Відкликати` | Pending → Draft |
| `revise(actor)` | `НаДоработку` | `НаДоопрацювання` | Pending → Revision |

**Properties:** `Status`, `History`, `IsDraft`, `IsPending`, `IsApproved`, `IsPosted`

### Example

```1s
Перем ЗП;
ЗП = ЗаказПоставщику("ЗП-001", Поставщик1);
ЗП.submit("Иванов");       // Draft → Pending
ЗП.approve("Директор");    // Pending → Approved
ЗП.post("Бухгалтер");      // Approved → Posted
Сообщить(ЗП.Status);       // → "posted"
```

---

## Procurement (SAP MM)

**File:** `src/runtime/procurement.py`

### Supplier / Поставщик / Постачальник

```1s
Перем Пост;
Пост = Поставщик("АО Металлсервис", "SUPP-001");
Пост.rating       = 9.2;
Пост.payment_days = 30;
Пост.currency     = "RUB";
```

| Property | Alias RU | Alias UK | Type |
|----------|----------|----------|------|
| `name` | `Наименование` | `Назва` | str |
| `code` | `Код` | `Код` | str |
| `rating` | `Рейтинг` | `Рейтинґ` | float (1–10) |
| `payment_days` | `ДниОплаты` | — | int |
| `currency` | — | — | str |

### PurchaseOrder / ЗаказПоставщику / ЗамовленняПостачальнику

```1s
Перем ЗП;
ЗП = ЗаказПоставщику("ЗП-2025-001", Пост);
ЗП.ДобавитьСтроку("STL-001", "Сталь 4мм", 500, 85, "лист");
ЗП.ДобавитьСтроку("BOLT-M12", "Болт М12", 200, 45);
ЗП.submit("Иванов");
ЗП.approve("Директор");
Сообщить(ЗП.report("ru"));
```

| Method | EN | RU | UK |
|--------|----|----|----|
| Add line | `AddLine(code, name, qty, price, unit)` | `ДобавитьСтроку` | `ДодатиРядок` |
| Receive goods | `receive(line_code, qty)` | `Принять` | `Прийняти` |
| Report | `report(lang)` | `report("ru")` | `report("uk")` |

**Key properties:** `number`, `total_amount`, `lines`, `supplier`, `currency`, `po_status`

**Completion tracking:** each line stores `received_qty`; `PurchaseOrder.completion_pct` returns 0–100.

### ReceivingOrder / ПриходнаяНакладная / ПрибутковаНакладна

```1s
Перем ПН;
ПН = ПриходнаяНакладная("ПН-2025-001", ЗП);
ПН.ДобавитьПриход("STL-001", "Сталь 4мм", 500, 85);
ПН.submit("склад");
ПН.post("склад");
```

Calling `add_receipt` / `ДобавитьПриход` automatically updates `PurchaseOrder.received_qty` on the matching line.

### ProcurementAnalytics / АналитикаЗакупок / АналітикаЗакупівель

```1s
Перем АЗ;
АЗ = АналитикаЗакупок();
АЗ.add_order(ЗП);
Сообщить(АЗ.by_supplier("ru"));
```

---

## Warehouse (SAP WM/EWM)

**File:** `src/runtime/warehouse.py`

### Warehouse / Склад

```1s
Перем СКЛ;
СКЛ = Склад("Главный склад", "WH-01");
Перем Я1;
Я1 = СКЛ.ДобавитьЯчейку("A", 1, 1, 5000);   // стеллаж A, ряд 1, ячейка 1, макс 5000 кг
СКЛ.Принять("STL-001", "Сталь 4мм", 500, 85, Я1, "ПН-001");
СКЛ.Отпустить("STL-001", 120, "Производство #12");
Сообщить(СКЛ.ОстатокТовара("STL-001"));   // → 380
```

| Method | EN | RU | UK |
|--------|----|----|----|
| Add cell | `AddCell(rack, row, slot, max_kg)` | `ДобавитьЯчейку` | `ДодатиКомірку` |
| Receive | `Receive(code, name, qty, price, cell, doc)` | `Принять` | `Прийняти` |
| Issue | `Issue(code, qty, reason)` | `Отпустить` | `Відпустити` |
| Balance | `Balance(code)` | `ОстатокТовара` | `ЗалишокТовару` |

**Key properties:** `stock_count` (number of SKUs), `total_stock_value`, `movements` (full history)

### ABCAnalysis / АВС_Анализ / АВС_Аналіз

Pareto classification by turnover: A = top 80%, B = next 15%, C = remaining 5%.

```1s
Перем АВС;
АВС = АВС_Анализ(СКЛ);
АВС.Run();
Сообщить(АВС.report("ru"));
```

### InventoryCheck / Инвентаризация / Інвентаризація

Book vs. actual count with shortage (!) and surplus (+) flagging.

```1s
Перем ИНВ;
ИНВ = Инвентаризация(СКЛ);
ИНВ.Пересчитать("STL-001", 375);   // book 380, actual 375 → shortage -5
ИНВ.Пересчитать("PIPE-50",  82);   // book 80,  actual 82  → surplus +2
Сообщить(ИНВ.report("ru"));
```

---

## Logistics (SAP TM/SD)

**File:** `src/runtime/logistics.py`

### Carrier / Перевозчик / Перевізник

```1s
Перем Пер;
Пер = Перевозчик("ООО АвтоТранс", "CARR-01");
Пер.rate_per_km  = 53.50;
Пер.reliability  = 0.91;
```

### DeliveryRoute / МаршрутДоставки

```1s
Перем МАР;
МАР = МаршрутДоставки("Киев — Харьков — Днепр", Пер);
МАР.total_distance_km = 480;
МАР.ДобавитьТочку("Киев, склад отправления",   Неопределено, 4500);
МАР.ДобавитьТочку("Харьков, завод",             Неопределено, 2000);
МАР.ДобавитьТочку("Днепр, склад получателя",    Неопределено, 2500);
```

### TransportOrder / ТранспортнаяЗаявка / ТранспортнаЗаявка

```1s
Перем ТЗ;
ТЗ = ТранспортнаяЗаявка("ТЗ-2025-001", Пер, МАР);
ТЗ.cargo_description = "Сталь листовая + трубы";
ТЗ.weight_kg = 4500;

// Workflow: Draft → Planned → In Transit → Delivered
ТЗ.plan("диспетчер");
ТЗ.approve("Логист");
ТЗ.start_transit("Водитель Ков.");
ТЗ.deliver("Водитель Ков.");

Сообщить(ТЗ.report("ru"));
```

| Transition method | From → To |
|-------------------|-----------|
| `plan(actor)` | Draft → Planned |
| `approve(actor)` | Pending → Approved |
| `start_transit(actor)` | Approved → In Transit |
| `deliver(actor)` | In Transit → Delivered |
| `fail(reason, actor)` | In Transit → Failed |

**Key properties:** `transport_cost`, `weight_kg`, `cargo_description`, `transport_status`, `actual_date`

### LogisticsAnalytics / АналитикаЛогистики / АналітикаЛогістики

```1s
Перем АЛ;
АЛ = АналитикаЛогистики();
АЛ.add(ТЗ1);
АЛ.add(ТЗ2);
Сообщить(АЛ.dashboard("ru"));
// → total orders, delivered, failed, SLA%, total cost
```

---

## Payroll (SAP HCM/PY)

Payroll is implemented directly with built-in 1S primitives — no separate class needed.

### Russian (НДФЛ 13%, ПФР 22%, ОМС 5.1%)

```1s
Перем Список;
Список = Массив();
Перем Зап1;
Зап1 = Структура();
Зап1.Вставить("Имя",    "Иванов И.И.");
Зап1.Вставить("Оклад",  85000);
Список.Добавить(Зап1);

Перем Н;
Для Н = 0 По Список.Количество() - 1 Цикл
    Перем Сотр, Оклад, НДФЛ, ПФР, ОМС, НаРуки;
    Сотр   = Список[Н];
    Оклад  = Сотр.Оклад;
    НДФЛ   = Округлить(Оклад * 0.13, 2);
    ПФР    = Округлить(Оклад * 0.22, 2);
    ОМС    = Округлить(Оклад * 0.051, 2);
    НаРуки = Оклад - НДФЛ;
    Сообщить(СтрШаблон("%1: оклад %2, на руки %3", Сотр.Имя, Оклад, НаРуки));
КонецЦикла;
```

### Ukrainian (ПДФО 18%, ЄСВ 22%)

```1s
Зап1.Вставити("Ім'я",  "Іваненко І.І.");
Зап1.Вставити("Оклад", 42000);
// ...
ПДФО   = Округлити(Оклад * 0.18, 2);
ЄСВ    = Округлити(Оклад * 0.22, 2);
НаРуки = Оклад - ПДФО;
```

### English (Federal+State 22%, FICA 7.65%)

```1s
E1 = Structure();
E1.Insert("Name",   "John Smith");
E1.Insert("Salary", 6500);
// ...
Tax  = Round(Gross * 0.22, 2);
Fica = Round(Gross * 0.0765, 2);
Net  = Gross - Tax - Fica;
```

---

## Maintenance (SAP PM/EAM)

**File:** `src/runtime/maintenance.py`

### EquipmentCard / КарточкаОборудования / КарткаОбладнання

```1s
Перем Обор;
Обор = КарточкаОборудования("EQ-001", "Токарный станок DMG CTX 310");
Обор.location       = "Цех №1, позиция 3";
Обор.category       = "Металлообработка";
Обор.manufacturer   = "DMG Mori";
Обор.serial_number  = "CTX-2019-83751";
Обор.install_date   = ДатаОтСтроки("2019-03-15", "ГГГГ-ММ-ДД");
Обор.odometer_hours = 14250;

// Register defects
Обор.ВнестиДефект("DEF-001", "Биение шпинделя > 0.05мм", "high");
Обор.ВнестиДефект("DEF-002", "Износ резцедержателя", "medium");

Сообщить(Обор.passport("ru"));
```

**Defect severity:** `"low"`, `"medium"`, `"high"`, `"critical"`

**Equipment status:** `"active"` (В работе), `"maintenance"` (ТО), `"repair"` (Ремонт), `"decommissioned"` (Списан)

### RepairOrder / НарядНаРемонт

```1s
Перем НР;
НР = НарядНаРемонт("НР-2025-047", Обор);
НР.work_type           = "Средний ремонт";
НР.defect_description  = "Биение шпинделя, износ резцедержателя";
НР.labour_hours        = 8;
НР.labour_rate         = 650;

// Workflow
НР.submit("мастер смены");
НР.approve("Главный механик");
НР.НачатьРаботу("Сергеев А.В.");

// Add materials
НР.ДобавитьМатериал("Подшипник 6208",     2, 1850);
НР.ДобавитьМатериал("Резцедержатель BT40", 1, 4200);
НР.ДобавитьМатериал("Смазка Shell Gadus", 0.5, 680);

НР.Завершить("Сергеев А.В.");
Сообщить(НР.report("ru"));
```

| Method | EN | RU | UK |
|--------|----|----|----|
| Start work | `StartWork(mechanic)` | `НачатьРаботу` | `РозпочатиРоботу` |
| Add material | `AddMaterial(name, qty, price)` | `ДобавитьМатериал` | `ДодатиМатеріал` |
| Complete | `Complete(mechanic)` | `Завершить` | `Завершити` |

**KPIs after `.Complete()`:**

| Property | Description |
|----------|-------------|
| `labour_cost` | `labour_hours × labour_rate` |
| `materials_cost` | sum of materials |
| `total_cost` | labour + materials |
| `downtime_hours` | hours equipment was unavailable |
| `mttr` | Mean Time To Repair (from `start_work` to `complete`) |

Completing a repair automatically:
- Sets equipment status back to `"active"`
- Resolves all defects linked to this repair order
- Posts the workflow (`Draft → Pending → Approved → Posted`)

### MaintenancePlan / ПланТО

```1s
Перем ПТО;
ПТО = ПланТО(Обор);
ПТО.ДобавитьРаботу("ТО-1000", "ТО каждые 1000 мото-часов", 1000, 4);  // каждые 1000ч
ПТО.ДобавитьРаботу("ТО-5000", "Плановый ремонт каждые 5000ч", 5000, 16);
Сообщить(ПТО.next_due(Обор.odometer_hours, "ru"));
```

### MaintenanceAnalytics / АналитикаТО

```1s
Перем АТО;
АТО = АналитикаТО();
АТО.add_equipment(Обор1);
АТО.add_equipment(Обор2);
АТО.add_repair(НР);
Сообщить(АТО.dashboard("ru"));
// → total equipment, repair orders, total cost, MTTR, per-order table
```

---

## Language Alias Reference

All ERP classes follow this naming convention:

| English class | Russian alias | Ukrainian alias |
|---------------|--------------|-----------------|
| `Supplier` | `Поставщик` | `Постачальник` |
| `PurchaseOrder` | `ЗаказПоставщику` | `ЗамовленняПостачальнику` |
| `ReceivingOrder` | `ПриходнаяНакладная` | `ПрибутковаНакладна` |
| `ProcurementAnalytics` | `АналитикаЗакупок` | `АналітикаЗакупівель` |
| `Warehouse` | `Склад` | `Склад` |
| `WarehouseCell` | `ЯчейкаСклада` | `КомірkаСкладу` |
| `StockMovement` | `ДвижениеТовара` | `РухТовару` |
| `ABCAnalysis` | `АВС_Анализ` | `АВС_Аналіз` |
| `InventoryCheck` | `Инвентаризация` | `Інвентаризація` |
| `Carrier` | `Перевозчик` | `Перевізник` |
| `DeliveryRoute` | `МаршрутДоставки` | `МаршрутДоставки` |
| `TransportOrder` | `ТранспортнаяЗаявка` | `ТранспортнаЗаявка` |
| `LogisticsAnalytics` | `АналитикаЛогистики` | `АналітикаЛогістики` |
| `EquipmentCard` | `КарточкаОборудования` | `КарткаОбладнання` |
| `RepairOrder` | `НарядНаРемонт` | `НарядНаРемонт` |
| `MaintenancePlan` | `ПланТО` | `ПланТО` |
| `MaintenanceAnalytics` | `АналитикаТО` | `АналітикаТО` |

---

## Running the Demo Scripts

```bash
# Full ERP cycle in Russian (SAP MM/WM/TM/HCM/PM)
python -m src.cli run examples/demo_erp_full_ru.1s

# Ukrainian
python -m src.cli run examples/demo_erp_full_uk.1s

# English
python -m src.cli run examples/demo_erp_full_en.1s
```

Or via the BAT launchers (Windows):
```
demos\DEMO-ERP-FULL-RU.bat
demos\DEMO-ERP-FULL-UK.bat
demos\DEMO-ERP-FULL-EN.bat
```

---

## See Also

- [workflow.md](workflow.md) — Workflow engine deep-dive
- [runtime.md](runtime.md) — Full runtime API reference
- [../examples/](../examples/) — All demo scripts
