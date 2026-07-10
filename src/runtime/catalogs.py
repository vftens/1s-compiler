"""
1S: ERP Free Edition — Catalogs (Справочники) and Documents (Документы).

These two object types are the heart of 1C's data model.
Every reference value (counterparty, product, employee) lives in a Catalog.
Every business transaction is recorded as a Document.

Catalog  (Справочник / Довідник):
    A named directory of items.  Each item has Код/Code and
    Наименование/Name plus arbitrary user-defined attributes.

Document (Документ):
    An auto-numbered, date-stamped transactional object.
    Has a main header (arbitrary attributes) and optional
    tabular sections (ТабличнаяЧасть / TabularSection).
    Can be "posted" (Провести / Post) which marks it as valid.
"""
from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from typing import Any, Optional
from .types import _Undefined, Undefined, _ValueTable, _Structure


# ── Catalog item ─────────────────────────────────────────────────────────────

class _CatalogItem:
    """
    One entry in a Catalog.
    Has built-in Код/Code + Наименование/Name.
    Any extra attribute can be set freely (like _Structure).
    """

    def __init__(self, code: str = "", name: str = ""):
        # Use object.__setattr__ to bypass our custom __setattr__
        object.__setattr__(self, "_code", code)
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_extra", {})

    # ── Property shortcuts ───────────────────────────────────────────

    @property
    def Код(self) -> str:          return self._code
    @property
    def Code(self) -> str:         return self._code
    @property
    def Наименование(self) -> str: return self._name
    @property
    def Name(self) -> str:         return self._name
    @property
    def Назва(self) -> str:        return self._name       # Ukrainian
    @property
    def Найменування(self) -> str: return self._name       # Ukrainian

    # ── Dynamic attribute access ─────────────────────────────────────

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._extra.get(name, Undefined)

    def __setattr__(self, name: str, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        elif name in ("Код", "Code"):
            object.__setattr__(self, "_code", value)
        elif name in ("Наименование", "Name", "Назва", "Найменування"):
            object.__setattr__(self, "_name", value)
        else:
            self._extra[name] = value

    def __repr__(self):
        return f"CatalogItem({self._code!r}, {self._name!r})"

    def __str__(self):
        return self._name

    def __hash__(self):
        return hash(self._code)

    def __eq__(self, other):
        if isinstance(other, _CatalogItem):
            return self._code == other._code
        if isinstance(other, str):
            return self._code == other or self._name == other
        return NotImplemented


class _CatalogSelection:
    """Iterator over catalog items."""
    def __init__(self, items: list[_CatalogItem]):
        self._items = items
        self._pos = -1

    def Next(self) -> bool:
        self._pos += 1
        return self._pos < len(self._items)

    def Current(self) -> Optional[_CatalogItem]:
        if 0 <= self._pos < len(self._items):
            return self._items[self._pos]
        return None

    Следующий = Next
    Текущий   = Current
    Наступний = Next
    Поточний  = Current


# ── Catalog ───────────────────────────────────────────────────────────────────

class Catalog:
    """
    Справочник / Довідник / Catalog

    A named reference directory.  Items are created with Create() / Создать() /
    Створити() and retrieved with FindByCode() / НайтиПоКоду() / НайтиЗаКодом().

    Example (Ukrainian):
        Товари = Справочник("Товари")
        Борошно = Товари.Створити("0001", "Борошно пшеничне в/с")
        Борошно.Одиниця = "кг"
        Борошно.Ціна    = 45.0

    Example (English):
        Goods = Catalog("Goods")
        Flour = Goods.Create("0001", "Wheat flour")
        Flour.Unit  = "kg"
        Flour.Price = 45.0
    """

    def __init__(self, name: str = ""):
        self.name = name
        self._items: dict[str, _CatalogItem] = {}   # code → item
        self._seq = 0

    # ── Create ───────────────────────────────────────────────────────

    def Create(self, code: str = "", name: str = "") -> _CatalogItem:
        """Create a new item. Auto-generates code if empty."""
        if not code:
            self._seq += 1
            code = f"{self._seq:06d}"
        item = _CatalogItem(code=code, name=name)
        self._items[code] = item
        return item

    # ── Find ─────────────────────────────────────────────────────────

    def FindByCode(self, code: str) -> "_CatalogItem | _Undefined":
        return self._items.get(code, Undefined)

    def FindByName(self, name: str) -> "_CatalogItem | _Undefined":
        for item in self._items.values():
            if item.Name == name or item.Наименование == name:
                return item
        return Undefined

    # ── Select / iterate ─────────────────────────────────────────────

    def Select(self) -> _CatalogSelection:
        return _CatalogSelection(list(self._items.values()))

    def Count(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items.values())

    def __len__(self):
        return len(self._items)

    def __repr__(self):
        return f"Catalog({self.name!r}, {len(self._items)} items)"

    # Russian aliases
    Создать              = Create
    НайтиПоКоду         = FindByCode
    НайтиПоНаименованию = FindByName
    Выбрать             = Select
    Количество          = Count

    # Ukrainian aliases
    Створити              = Create
    НайтиЗаКодом         = FindByCode
    НайтиЗаНайменуванням = FindByName
    Вибрати              = Select
    Кількість            = Count


# Constructor aliases (Russian / Ukrainian / English)
Справочник = Catalog
Довідник   = Catalog


# ── Tabular section ───────────────────────────────────────────────────────────

class TabularSection(_ValueTable):
    """
    ТабличнаяЧасть / ТабличнаЧастина / TabularSection
    A table embedded in a Document (like an invoice line list).
    Inherits all ValueTable methods.
    """

    def __init__(self, name: str, columns: str = ""):
        super().__init__()
        self._tab_name = name
        if columns:
            for col in columns.split(","):
                self.Columns.Add(col.strip())

    def __repr__(self):
        return f"TabularSection({self._tab_name!r}, {len(self._rows)} rows)"

    # Ukrainian alias
    ТабличнаЧастина = property(lambda self: self)


# ── Document ──────────────────────────────────────────────────────────────────

class Document:
    """
    Документ / Документ / Document

    An auto-numbered, date-stamped business transaction.
    Has arbitrary header attributes + optional tabular sections.

    Example (Ukrainian):
        ВН = Документ("ВидатковаНакладна")
        ВН.Дата        = '20250115'
        ВН.Контрагент  = ТОВ_Альфа
        Товари = ВН.ТабличнаЧастина("Товари", "Товар, Кількість, Ціна, Сума")
        Рядок = Товари.Додати()
        Рядок["Товар"] = "Борошно"
        Рядок["Кількість"] = 100
        ВН.Провести()

    Example (English):
        Inv = Document("SalesInvoice")
        Inv.Date       = '20250115'
        Inv.Customer   = Alpha_LLC
        Lines = Inv.TabSection("Lines", "Product, Qty, Price, Amount")
        Row = Lines.Add()
        Row["Product"] = "Flour"
        Row["Qty"]     = 100
        Inv.Post()
    """

    _counters: dict[str, int] = {}   # type_name → last number

    def __init__(self, doc_type: str = ""):
        Document._counters[doc_type] = Document._counters.get(doc_type, 0) + 1
        num_int = Document._counters[doc_type]

        object.__setattr__(self, "_type",   doc_type)
        object.__setattr__(self, "_num",    num_int)
        object.__setattr__(self, "_posted", False)
        object.__setattr__(self, "_tabs",   {})
        label = f"{num_int:06d}"
        object.__setattr__(self, "_data",   {
            "Номер":    label,
            "Number":   label,
            "number":   label,
            "Дата":     datetime.date.today(),
            "Date":     datetime.date.today(),
            "date":     datetime.date.today(),
            "Проведён": False,
            "IsPosted": False,
        })

    # ── Header attribute access ──────────────────────────────────────

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        data = object.__getattribute__(self, "_data")
        return data.get(name, Undefined)

    def __setattr__(self, name: str, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            data = object.__getattribute__(self, "_data")
            data[name] = value

    # ── Tabular sections ─────────────────────────────────────────────

    def TabSection(self, name: str, columns: str = "") -> TabularSection:
        """Get-or-create a tabular section."""
        tabs = object.__getattribute__(self, "_tabs")
        if name not in tabs:
            tabs[name] = TabularSection(name, columns)
        return tabs[name]

    def GetTabSection(self, name: str) -> TabularSection:
        tabs = object.__getattribute__(self, "_tabs")
        return tabs.get(name, TabularSection(name))

    # ── Lifecycle ────────────────────────────────────────────────────

    def Post(self) -> bool:
        """Mark as posted (Провести)."""
        data = object.__getattribute__(self, "_data")
        data["Проведён"] = True
        data["IsPosted"] = True
        object.__setattr__(self, "_posted", True)
        return True

    def Unpost(self) -> None:
        """Cancel posting (Отменить проведение)."""
        data = object.__getattribute__(self, "_data")
        data["Проведён"] = False
        data["IsPosted"] = False
        object.__setattr__(self, "_posted", False)

    def Write(self) -> None:
        """Write/save document (in-memory; persistent storage in future)."""
        pass

    # ── Properties ───────────────────────────────────────────────────

    @property
    def Номер(self) -> str:
        return object.__getattribute__(self, "_data").get("Номер", "")

    @property
    def Number(self) -> str:
        return object.__getattribute__(self, "_data").get("Number", "")

    @property
    def Дата(self):
        return object.__getattribute__(self, "_data").get("Дата")

    @property
    def Date(self):
        return object.__getattribute__(self, "_data").get("Date")

    @property
    def IsPosted(self) -> bool:
        return object.__getattribute__(self, "_posted")

    @property
    def Проведён(self) -> bool:
        return object.__getattribute__(self, "_posted")

    def __repr__(self):
        t = object.__getattribute__(self, "_type")
        n = object.__getattribute__(self, "_data").get("Номер", "?")
        return f"Document({t!r} #{n})"

    def __str__(self):
        t = object.__getattribute__(self, "_type")
        n = object.__getattribute__(self, "_data").get("Номер", "?")
        return f"{t} N{n}"

    # Russian aliases
    ТабличнаяЧасть          = TabSection
    ПолучитьТабличнуюЧасть  = GetTabSection
    Провести                 = Post
    ОтменитьПроведение       = Unpost
    Записать                 = Write

    # Ukrainian aliases
    ТабличнаЧастина         = TabSection
    ОтриматиТабличнуЧастину = GetTabSection
    # Провести same spelling in both
    СкасуватиПроведення     = Unpost
    Записати                = Write


# Aliases
Документ  = Document    # Russian / Ukrainian
