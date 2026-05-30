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

__all__ = [
    # Types
    "Undefined", "_1SException", "Array",
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
    "ДобавитьДни", "ДеньНедели",
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
]
