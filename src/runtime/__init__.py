"""
1S Runtime — everything imported by transpiled modules.
"""
from .types import *
from .types import (
    _Undefined, Undefined, _1SException, _parse_date,
    _Array, _Map, _Structure, _ValueTable, _VTRow, _VTColumnCollection,
    _ValueList, _ValueListItem, _KeyValue,
)
from .registers import (
    Account, ChartOfAccounts, AccountingRegister, AccumulationRegister,
    InformationRegister, WorkSchedule,
    AccountingEntry, AccumulationEntry, InformationEntry,
    # Russian names
    ПланСчетов, РегистрБухгалтерии, РегистрНакопления,
    РегистрСведений, ГрафикРаботы,
    # Ukrainian names
    ПланРахунків, РегістрБухгалтерії, РегістрНакопичення,
    РегістрВідомостей, ГрафікРоботи,
)
from .query import _Query, QueryResult, Запрос, Query
from .catalogs import (
    Catalog, Document, TabularSection,
    _CatalogItem, _CatalogSelection,
    Справочник, Довідник, Документ,
)
from .workflow import (
    WorkflowDocument, WF, WFEntry,
    ДокументЗМаршрутом, ДокументСМаршрутом,
)
from .audit import AuditLog, AuditEntry, АудитЖурнал
from .persistence import (
    save_register, load_register,
    save_accounting, load_accounting,
    save_accumulation, load_accumulation,
    СохранитьРегистр, ЗагрузитьРегистр,
    ЗберегтиРегістр, ЗавантажитиРегістр,
    # Sprint 11 — ERP module persistence
    save_org_chart, load_org_chart,
    save_budget, load_budget,
    save_payroll_results, load_payroll_results,
    save_workflow_config, load_workflow_config,
    СохранитьОргСтруктуру, ЗагрузитьОргСтруктуру,
    ЗберегтиОргСтруктуру, ЗавантажитиОргСтруктуру,
    СохранитьБюджет, ЗагрузитьБюджет,
    ЗберегтиБюджет, ЗавантажитиБюджет,
    СохранитьРасчетыЗП, ЗагрузитьРасчетыЗП,
    ЗберегтиРозрахункиЗП, ЗавантажитиРозрахункиЗП,
    СохранитьМаршрут, ЗагрузитьМаршрут,
    ЗберегтиМаршрут, ЗавантажитиМаршрут,
)
from .erp_query import (
    ERPQuery,
    ЗапросERPe, ЗапитERPe, ERPЗапрос,
)
from .excel import (
    ExcelWorkbook, ExcelSheet, ExportCSV,
    КнигаExcel, ЕксельЗбереження, ЭкспортCSV,
)
from .logistics import (
    TransportOrder, DeliveryRoute, Carrier, LogisticsAnalytics, TM,
    ТранспортнаяЗаявка, МаршрутДоставки, Перевозчик, АналитикаЛогистики,
    ТранспортнаЗаявка, Перевізник, АналітикаЛогістики,
)
from .procurement import (
    PurchaseOrder, ReceivingOrder, Supplier, ProcurementAnalytics,
    ЗаказПоставщику, ПриходнаяНакладная, Поставщик, АналитикаЗакупок,
    ЗамовленняПостачальнику, ПрибутковаНакладна, Постачальник, АналітикаЗакупівель,
)
from .warehouse import (
    Warehouse, WarehouseCell, StockMovement, ABCAnalysis, InventoryCheck, MoveType,
    Склад, ЯчейкаСклада, ДвижениеТовара, АВС_Анализ, Инвентаризация,
    КомірkаСкладу, РухТовару, АВС_Аналіз, Інвентаризація,
)
from .maintenance import (
    EquipmentCard, RepairOrder, MaintenancePlan, MaintenanceAnalytics, EqStatus,
    КарточкаОборудования, НарядНаРемонт, ПланТО, АналитикаТО,
    КарткаОбладнання, АналітикаТО, СтатусОбладнання,
)

# ── Sprint 10: SAP/Oracle-comparable configuration layer ────────────────────
from .org import (
    OrgChart, OrgNode, OrgType,
    HOLDING, LEGAL_ENTITY, PLANT, DEPARTMENT, COST_CENTER, PROFIT_CENTER,
    ОрганизационнаяСтруктура, ОрганізаційнаСтруктура,
    ХОЛДИНГ, ЮРИДИЧЕСКОЕ_ЛИЦО, ЗАВОД, ОТДЕЛ, МВЗ, ЦЕНТР_ПРИБЫЛИ,
    ПІДПРИЄМСТВО, ЦЕХ, ВІДДІЛ, МВВ,
)
from .tax_engine import (
    TaxEngine, TaxResult, TaxLine,
    НалоговыйДвижок, ПодатковийДвижок,
    РезультатНалога, РезультатПодатку,
)
from .budget import (
    BudgetControl, BudgetBalance, BudgetAllocation, BudgetEntry,
    КонтрольБюджета, КонтрольБюджету,
)
from .workflow_config import (
    WorkflowConfig, WFRule,
    НастройкиМаршрута, НалаштуванняМаршруту,
)
from .payroll import (
    PayrollEngine, Employee, Absence, BonusScheme, Payslip, PayslipLine,
    PayrollResult, PayPeriod, AbsenceType,
    РасчетЗарплаты, РозрахунокЗарплати,
    Сотрудник, Працівник,
    Отсутствие, Відсутність,
    Премия, Премія,
    РасчетныйЛист, РозрахунковийЛист,
    ПериодОплаты, ПеріодОплати,
    ТипОтсутствия, ТипВідсутності,
)
from .three_way_match import (
    ThreeWayMatch, SupplierInvoice, MatchResult, MatchStatus, MatchConfig,
    InvoiceLine,
    ТрёхстороннееСопоставление, ТристороннєЗіставлення,
    СчётПоставщика, РахунокПостачальника,
)
from .industry_profile import (
    IndustryProfile, load_profile,
    ОтраслевойПрофиль, ГалузевийПрофіль,
    ЗагрузитьПрофиль, ЗавантажитиПрофіль,
)

__all__ = [
    # Types
    "Undefined", "_1SException", "Array", "Structure",
    "_parse_date",
    # Collections — English
    "_Array", "_Map", "_Structure", "_ValueTable", "_ValueList",
    # Collections — Russian
    "Массив", "Соответствие", "Структура", "ТаблицаЗначений", "СписокЗначений",
    # Collections — Ukrainian
    "Масив", "Відповідність", "ТаблицяЗначень", "СписокЗначень",

    # Date — English/Russian
    "CurrentDate", "CurrentDateAndTime",
    "BegOfDay", "EndOfDay", "BegOfMonth", "EndOfMonth", "BegOfYear",
    "AddMonth", "AddDays", "DayOfWeek",
    "ТекущаяДата", "ТекущаяДатаИВремя",
    "НачалоДня", "КонецДня", "НачалоМесяца", "КонецМесяца", "НачалоГода",
    "ДобавитьДни", "ДеньНедели", "DateFromString", "ДатаОтСтроки", "ДатаЗРядка",
    # Date — Ukrainian
    "ПоточнаДата", "ПоточнаДатаЧас",
    "ПочатокДня", "КінецьДня", "ПочатокМісяця", "КінецьМісяця", "ПочатокРоку",
    "ДодатиМісяці", "ДодатиДні", "ДеньТижня",

    # Strings — English/Russian
    "StrLen", "Left", "Right", "Mid", "TrimAll", "TrimL", "TrimR",
    "Upper", "Lower", "Find", "StrReplace", "StrCount", "StrSplit",
    "Format", "String", "StrTemplate", "StrRepeat", "Char",
    "СтрДлина", "Лев", "Прав", "Сред", "СокрЛП", "СокрЛ", "СокрП",
    "ВРег", "НРег", "Найти", "СтрЗаменить", "СтрЧисло", "СтрРазделить",
    "Формат", "Строка", "СтрШаблон", "СтрПовтор", "Символ",
    # Strings — Ukrainian
    "ДовжинаРядка", "Ліво", "Право", "Середина", "СкорЛП", "СкорЛ", "СкорП",
    "ВРегістр", "НРегістр", "Знайти", "ЗамінитиРядок",
    "КількістьПідрядків", "РозбитиРядок", "ШаблонРядка", "ПовторитиРядок",
    "Рядок",

    # Numbers — English/Russian
    "Int", "Round", "Abs", "Max", "Min", "Number",
    "Цел", "Окр", "Макс", "Мин", "Число",
    # Numbers — Ukrainian
    "Ціле", "Округлити", "Мін",

    # Type conversion
    "Boolean", "TypeOf", "Булево", "ТипЗнч", "ТипЗначення",

    # Output — English/Russian
    "Message", "Alert", "ErrorInfo", "ErrorDescription",
    "Сообщить", "Предупреждение", "ИнформацияОбОшибке", "ОписаниеОшибки",
    # Output — Ukrainian
    "Повідомити", "Попередження", "ІнформаціяПроПомилку", "ОписПомилки",

    # Registers — English/Russian
    "Account", "ChartOfAccounts", "AccountingRegister", "AccumulationRegister",
    "InformationRegister", "WorkSchedule",
    "ПланСчетов", "РегистрБухгалтерии", "РегистрНакопления",
    "РегистрСведений", "ГрафикРаботы",
    # Registers — Ukrainian
    "ПланРахунків", "РегістрБухгалтерії", "РегістрНакопичення",
    "РегістрВідомостей", "ГрафікРоботи",

    # Query
    "_Query", "QueryResult", "Запрос", "Query",

    # Catalogs + Documents
    "Catalog", "Document", "TabularSection",
    "Справочник", "Довідник", "Документ",

    # Workflow
    "WorkflowDocument", "WF", "WFEntry",
    "ДокументЗМаршрутом", "ДокументСМаршрутом",

    # Audit Log
    "AuditLog", "AuditEntry", "АудитЖурнал",

    # Excel / CSV export
    "ExcelWorkbook", "ExcelSheet", "ExportCSV",
    "КнигаExcel", "ЕксельЗбереження", "ЭкспортCSV",

    # Sprint 10 — OrgUnit
    "OrgChart", "OrgNode", "OrgType",
    "HOLDING", "LEGAL_ENTITY", "PLANT", "DEPARTMENT", "COST_CENTER", "PROFIT_CENTER",
    "ОрганизационнаяСтруктура", "ОрганізаційнаСтруктура",
    "ХОЛДИНГ", "ЮРИДИЧЕСКОЕ_ЛИЦО", "ЗАВОД", "ОТДЕЛ", "МВЗ", "ЦЕНТР_ПРИБЫЛИ",
    "ПІДПРИЄМСТВО", "ЦЕХ", "ВІДДІЛ", "МВВ",

    # Sprint 10 — TaxEngine
    "TaxEngine", "TaxResult", "TaxLine",
    "НалоговыйДвижок", "ПодатковийДвижок", "РезультатНалога", "РезультатПодатку",

    # Sprint 10 — BudgetControl
    "BudgetControl", "BudgetBalance", "BudgetAllocation", "BudgetEntry",
    "КонтрольБюджета", "КонтрольБюджету",

    # Sprint 10 — WorkflowConfig
    "WorkflowConfig", "WFRule",
    "НастройкиМаршрута", "НалаштуванняМаршруту",

    # Sprint 10 — PayrollEngine
    "PayrollEngine", "Employee", "Absence", "BonusScheme", "Payslip",
    "PayslipLine", "PayrollResult", "PayPeriod", "AbsenceType",
    "РасчетЗарплаты", "РозрахунокЗарплати",
    "Сотрудник", "Працівник", "Отсутствие", "Відсутність",
    "Премия", "Премія", "РасчетныйЛист", "РозрахунковийЛист",
    "ПериодОплаты", "ПеріодОплати", "ТипОтсутствия", "ТипВідсутності",

    # Sprint 10 — ThreeWayMatch
    "ThreeWayMatch", "SupplierInvoice", "MatchResult", "MatchStatus", "MatchConfig",
    "InvoiceLine",
    "ТрёхстороннееСопоставление", "ТристороннєЗіставлення",
    "СчётПоставщика", "РахунокПостачальника",

    # Sprint 10 — IndustryProfile
    "IndustryProfile", "load_profile",
    "ОтраслевойПрофиль", "ГалузевийПрофіль",
    "ЗагрузитьПрофиль", "ЗавантажитиПрофіль",
]
