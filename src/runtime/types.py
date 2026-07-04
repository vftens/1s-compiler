"""
1S: ERP Free Edition — Core runtime types
Mirrors 1C built-in types closely enough to run ported scripts.
"""
from __future__ import annotations
import datetime
from decimal import Decimal
from typing import Any, Iterator


# ── Undefined sentinel ───────────────────────────────────────────────────────

class _Undefined:
    """Represents 1C Неопределено / Undefined."""
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    def __bool__(self): return False
    def __repr__(self): return "Undefined"
    def __eq__(self, other): return isinstance(other, _Undefined)

Undefined = _Undefined()


# ── 1S Exception wrapper ─────────────────────────────────────────────────────

class _1SException(Exception):
    def __init__(self, msg=""):
        super().__init__(msg)
        self.message = str(msg)

    def Description(self) -> str:
        return self.message

    # 1C compat aliases
    @property
    def ОписаниеОшибки(self): return self.Description()


# ── Date helpers ─────────────────────────────────────────────────────────────

def _parse_date(s: str) -> datetime.date:
    """Parse 1C date literal 'YYYYMMDD' → Python date."""
    return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def CurrentDate() -> datetime.date:
    return datetime.date.today()

def CurrentDateAndTime() -> datetime.datetime:
    return datetime.datetime.now()

def BegOfDay(dt) -> datetime.datetime:
    d = dt if isinstance(dt, datetime.date) else dt.date()
    return datetime.datetime(d.year, d.month, d.day)

def EndOfDay(dt) -> datetime.datetime:
    d = dt if isinstance(dt, datetime.date) else dt.date()
    return datetime.datetime(d.year, d.month, d.day, 23, 59, 59)

def BegOfMonth(dt) -> datetime.datetime:
    d = dt if isinstance(dt, datetime.date) else dt.date()
    return datetime.datetime(d.year, d.month, 1)

def BegOfYear(dt) -> datetime.datetime:
    d = dt if isinstance(dt, datetime.date) else dt.date()
    return datetime.datetime(d.year, 1, 1)

def AddMonth(dt, n: int) -> datetime.datetime:
    import calendar
    d = dt if isinstance(dt, datetime.date) else dt.date()
    month = d.month - 1 + n
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return datetime.datetime(year, month, day)

def EndOfMonth(dt) -> datetime.datetime:
    import calendar
    d = dt if isinstance(dt, datetime.date) else dt.date()
    last = calendar.monthrange(d.year, d.month)[1]
    return datetime.datetime(d.year, d.month, last, 23, 59, 59)

def AddDays(dt, n: int) -> datetime.datetime:
    d = dt if isinstance(dt, (datetime.datetime, datetime.date)) else dt
    return d + datetime.timedelta(days=n)

def TimeNow() -> float:
    """Return current Unix timestamp in seconds (float). For timing/benchmarks."""
    import time as _time
    return _time.time()

# Russian / Ukrainian aliases
ЧасЗараз  = TimeNow   # Ukrainian: time now
ВремяСейчас = TimeNow  # Russian

def DayOfWeek(dt) -> int:
    """Returns 1=Mon … 7=Sun (1C convention)."""
    d = dt if isinstance(dt, datetime.date) else dt.date()
    return d.weekday() + 1

# Russian aliases
ТекущаяДата           = CurrentDate
ТекущаяДатаИВремя     = CurrentDateAndTime
НачалоДня             = BegOfDay
КонецДня              = EndOfDay
НачалоМесяца          = BegOfMonth
КонецМесяца           = EndOfMonth
НачалоГода            = BegOfYear
ДобавитьМесяц         = AddMonth
ДобавитьДни           = AddDays
ДеньНедели            = DayOfWeek


def DateFromString(s: str, fmt: str = "YYYY-MM-DD") -> datetime.date:
    """Parse date string with 1C-style format mask (ГГГГ-ММ-ДД → %Y-%m-%d)."""
    py_fmt = (fmt
        .replace("ГГГГ", "%Y").replace("ГГ", "%y")
        .replace("ММ", "%m").replace("ДД", "%d")
        .replace("YYYY", "%Y").replace("MM", "%m").replace("DD", "%d"))
    return datetime.datetime.strptime(str(s), py_fmt).date()

ДатаОтСтроки  = DateFromString   # Russian
ДатаЗРядка    = DateFromString   # Ukrainian


# ── String functions ─────────────────────────────────────────────────────────

def StrLen(s: str) -> int:       return len(str(s))
def Left(s: str, n: int) -> str: return str(s)[:n]
def Right(s: str, n: int) -> str: return str(s)[-n:]
def Mid(s: str, start: int, length: int = -1) -> str:
    s = str(s)
    idx = start - 1   # 1C is 1-indexed
    return s[idx:] if length < 0 else s[idx:idx + length]
def TrimAll(s: str) -> str: return str(s).strip()
def TrimL(s: str) -> str:   return str(s).lstrip()
def TrimR(s: str) -> str:   return str(s).rstrip()
def Upper(s: str) -> str:   return str(s).upper()
def Lower(s: str) -> str:   return str(s).lower()
def Find(s: str, sub: str) -> int:
    idx = str(s).find(str(sub))
    return idx + 1 if idx >= 0 else 0   # 1C 1-indexed, 0 = not found
def StrReplace(s: str, old: str, new: str) -> str:
    return str(s).replace(str(old), str(new))
def StrCount(s: str, sub: str) -> int:
    return str(s).count(str(sub))
def StrSplit(s: str, sep: str = ",", include_empty: bool = True):
    parts = str(s).split(str(sep))
    if not include_empty:
        parts = [p for p in parts if p]
    arr = _Array()
    arr._items = parts
    return arr

def Format(value, fmt_str: str) -> str:
    """1C Формат() — date and number formatting."""
    import re as _re
    import datetime as _dt

    if not fmt_str:
        return str(value)

    # Parse semicolon-separated key=value (values may be single-quoted)
    opts: dict[str, str] = {}
    for part in fmt_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            opts[k.strip()] = v.strip().strip("'")

    # ── Date / datetime formatting ────────────────────────────────────
    df = opts.get("ДФ", "")
    if df and isinstance(value, (_dt.datetime, _dt.date)):
        d = value.date() if isinstance(value, _dt.datetime) else value
        _RU_MON = ["", "Январь", "Февраль", "Март", "Апрель", "Май",
                   "Июнь", "Июль", "Август", "Сентябрь",
                   "Октябрь", "Ноябрь", "Декабрь"]
        # Single-pass substitution to prevent re-matching inside replaced text
        _date_sub = [
            ("ММММ", _RU_MON[d.month]),
            ("МММ",  _RU_MON[d.month][:3]),
            ("ММ",   f"{d.month:02d}"),
            ("М",    str(d.month)),
            ("дд",   f"{d.day:02d}"),
            ("ДД",   f"{d.day:02d}"),
            ("гггг", str(d.year)),
            ("гг",   str(d.year)[-2:]),
        ]
        _map = dict(_date_sub)
        _pat = _re.compile("|".join(_re.escape(k) for k, _ in _date_sub))
        return _pat.sub(lambda m: _map[m.group(0)], df)

    # ── Number formatting ─────────────────────────────────────────────
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)

    чдц_s = opts.get("ЧДЦ", "").strip()
    decimals = int(чдц_s) if чдц_s.isdigit() else None

    if decimals is not None:
        num_str = f"{num:.{decimals}f}"
    else:
        # Remove unnecessary trailing zeros
        num_str = f"{num:g}" if num == int(num) else str(num)

    чц_s = opts.get("ЧЦ", "").strip()
    if чц_s.isdigit():
        num_str = num_str.rjust(int(чц_s))

    return num_str

def StrTemplate(template: str, *args) -> str:
    """
    1C СтрШаблон — two modes:
      • 1C style:    %1, %2, ... in template  → positional substitution
      • printf style: %-30s, %6s, ...          → Python % operator
    Detect which mode by checking whether %N (digit, non-digit) occurs.
    """
    import re as _re
    result = str(template)
    # Detect 1C positional style: bare %N not followed by another digit or letter
    has_1c = bool(_re.search(r"%\d+(?!\d|[a-zA-Z])", result))
    if has_1c:
        # Replace longest numbers first to avoid %1 eating %10
        for i in sorted(range(1, len(args) + 1), reverse=True):
            result = result.replace(f"%{i}", str(args[i - 1]))
        result = result.replace("%%", "%")
    else:
        # Printf-style: pass all args
        try:
            result = result % tuple(str(a) for a in args)
        except Exception:
            pass
    return result

def StrRepeat(s: str, n: int) -> str:
    """1C СтрПовтор — repeat string n times."""
    return str(s) * int(n)

def Char(code: int) -> str:
    """1C Символ — character by Unicode code point."""
    return chr(int(code))

# Russian aliases
СтрШаблон  = StrTemplate
СтрПовтор  = StrRepeat
Символ     = Char

# Russian aliases (existing)
СтрДлина    = StrLen
Лев         = Left
Прав        = Right
Сред        = Mid
СокрЛП      = TrimAll
СокрЛ       = TrimL
СокрП       = TrimR
ВРег        = Upper
НРег        = Lower
Найти       = Find
СтрЗаменить = StrReplace
СтрЧисло    = StrCount
СтрРазделить = StrSplit
Формат      = Format


# ── Numeric ──────────────────────────────────────────────────────────────────

def Int(n) -> int:   return int(n)
def Round(n, digits: int = 0): return round(float(n), digits)
def Abs(n):  return abs(n)
def Log(n):
    import math; return math.log(n)
def Log10(n):
    import math; return math.log10(n)
def Pow(base, exp):  return base ** exp
def Sqrt(n):
    import math; return math.sqrt(n)
def Sin(n):
    import math; return math.sin(n)
def Cos(n):
    import math; return math.cos(n)
def Tan(n):
    import math; return math.tan(n)
def Max(*args): return max(args)
def Min(*args): return min(args)

# Russian aliases
Цел        = Int
Окр        = Round
Макс       = Max
Мин        = Min


# ── Type conversion ──────────────────────────────────────────────────────────

def String(v) -> str:
    if v is None or isinstance(v, _Undefined): return ""
    return str(v)

def Number(v) -> Decimal:
    try: return Decimal(str(v))
    except: return Decimal(0)

def Boolean(v) -> bool:
    return bool(v)

def TypeOf(v) -> str:
    if isinstance(v, bool):          return "Boolean"
    if isinstance(v, int):           return "Number"
    if isinstance(v, float):         return "Number"
    if isinstance(v, Decimal):       return "Number"
    if isinstance(v, str):           return "String"
    if isinstance(v, datetime.date): return "Date"
    if isinstance(v, _Undefined):    return "Undefined"
    if v is None:                    return "Null"
    return type(v).__name__

def TypeValue(type_name: str):
    """Return a type description object (simplified)."""
    return type_name

# Russian aliases
Строка  = String
Число   = Number
Булево  = Boolean
ТипЗнч  = TypeOf
ТипЗначения = TypeOf
# Ukrainian alias
ТипЗначення = TypeOf


# ── Array / ValueList ────────────────────────────────────────────────────────

class _Array:
    """1C МассивArrays — 0-indexed internally, but 1C access is 0-indexed too."""
    def __init__(self):
        self._items: list = []

    def Add(self, v=None):
        self._items.append(v)
        return v

    def Insert(self, idx: int, v=None):
        self._items.insert(idx, v)

    def Delete(self, idx: int):
        del self._items[idx]

    def Find(self, v) -> int | _Undefined:
        try: return self._items.index(v)
        except ValueError: return Undefined

    def Count(self) -> int:
        return len(self._items)

    def Clear(self):
        self._items.clear()

    def Get(self, idx: int):
        return self._items[idx]

    def Set(self, idx: int, v):
        self._items[idx] = v

    def __getitem__(self, idx): return self._items[idx]
    def __setitem__(self, idx, v): self._items[idx] = v
    def __len__(self): return len(self._items)
    def __iter__(self): return iter(self._items)
    def __repr__(self): return f"Array({self._items})"

    # Russian method aliases
    Добавить  = Add
    Вставить  = Insert
    Удалить   = Delete
    Найти     = Find
    Количество = Count
    Очистить  = Clear
    Получить  = Get
    Установить = Set
    # Ukrainian method aliases
    Додати    = Add
    Вставити  = Insert
    Видалити  = Delete
    Знайти    = Find
    Кількість = Count
    Очистити  = Clear
    Отримати  = Get
    Встановити = Set

# Constructor aliases
Массив = _Array
Масив  = _Array
Array  = _Array


class _Map:
    """1C Соответствие / Map — like Python dict."""
    def __init__(self):
        self._data: dict = {}

    def Insert(self, key, value=None):
        self._data[key] = value

    def Get(self, key):
        return self._data.get(key, Undefined)

    def Delete(self, key):
        self._data.pop(key, None)

    def Count(self) -> int:
        return len(self._data)

    def Clear(self):
        self._data.clear()

    def __getitem__(self, key):       return self._data.get(key, Undefined)
    def __setitem__(self, key, val):  self._data[key] = val

    def __iter__(self):
        for k, v in self._data.items():
            kv = _KeyValue(k, v)
            yield kv

    def __repr__(self): return f"Map({self._data})"

    # Russian aliases
    Вставить   = Insert
    Получить   = Get
    Удалить    = Delete
    Количество = Count
    Очистить   = Clear
    # Ukrainian aliases
    Вставити   = Insert
    Отримати   = Get
    Видалити   = Delete
    Кількість  = Count
    Очистити   = Clear

Соответствие = _Map
Відповідність = _Map
Map = _Map           # English alias


class _KeyValue:
    def __init__(self, key, value):
        self.Key      = key
        self.Value    = value
        self.Ключ     = key    # Russian
        self.Значение = value  # Russian
        self.Значення = value  # Ukrainian


class _Structure:
    """1C Структура / Structure — named properties."""
    def __init__(self, keys: str = "", *values):
        self._data: dict = {}
        if keys:
            key_list = [k.strip() for k in keys.split(",")]
            for i, k in enumerate(key_list):
                self._data[k] = values[i] if i < len(values) else Undefined

    def Insert(self, key: str, value=None):
        self._data[key] = value

    def Delete(self, key: str):
        self._data.pop(key, None)

    def Property(self, key: str, out=None) -> bool:
        return key in self._data

    def Count(self) -> int:
        return len(self._data)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._data.get(name, Undefined)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def __getitem__(self, key):        return self._data.get(key, Undefined)
    def __setitem__(self, key, value): self._data[key] = value

    def __iter__(self):
        for k, v in self._data.items():
            yield _KeyValue(k, v)

    def __repr__(self): return f"Structure({self._data})"

    # Russian aliases
    Вставить   = Insert
    Удалить    = Delete
    Свойство   = Property
    Количество = Count
    # Ukrainian aliases
    Вставити   = Insert
    Видалити   = Delete
    Властивість = Property
    Кількість  = Count

Структура = _Structure
Structure = _Structure


class _ValueTable:
    """1C ТаблицаЗначений / ValueTable — a 2D data structure."""
    def __init__(self):
        self.Columns = _VTColumnCollection()
        self.Колонки = self.Columns   # Russian alias
        self._rows: list[_VTRow] = []

    def Add(self) -> "_VTRow":
        row = _VTRow(self.Columns)
        self._rows.append(row)
        return row

    def Count(self) -> int:
        return len(self._rows)

    def Clear(self):
        self._rows.clear()

    def Delete(self, row):
        self._rows.remove(row)

    def Find(self, value, column: str):
        for row in self._rows:
            if row[column] == value:
                return row
        return Undefined

    def FindRows(self, criteria: _Structure) -> "_Array":
        result = _Array()
        for row in self._rows:
            match = True
            for kv in criteria:
                if row[kv.Key] != kv.Value:
                    match = False
                    break
            if match:
                result.Add(row)
        return result

    def Total(self, column: str) -> Decimal:
        from decimal import Decimal
        return sum((Decimal(str(r[column])) for r in self._rows if r[column] not in (None, Undefined)), Decimal(0))

    def Sort(self, column: str, direction: str = "ASC"):
        reverse = direction.upper() == "DESC"
        self._rows.sort(key=lambda r: r[column], reverse=reverse)

    def __iter__(self): return iter(self._rows)
    def __len__(self): return len(self._rows)
    def __getitem__(self, idx): return self._rows[idx]

    # Russian aliases
    Добавить     = Add
    Количество   = Count
    Очистить     = Clear
    Удалить      = Delete
    Найти        = Find
    НайтиСтроки  = FindRows
    Итог         = Total
    Сортировать  = Sort
    # Ukrainian aliases
    Додати       = Add
    Кількість    = Count
    Очистити     = Clear
    Видалити     = Delete
    Знайти       = Find
    ЗнайтиРядки  = FindRows
    Підсумок     = Total
    Сортувати    = Sort

ТаблицаЗначений  = _ValueTable
ТаблицяЗначень   = _ValueTable


class _VTColumnCollection:
    def __init__(self):
        self._cols: list[str] = []

    def Add(self, name: str, *args):
        self._cols.append(name)

    def Count(self) -> int:
        return len(self._cols)

    def __iter__(self): return iter(self._cols)
    def __contains__(self, item): return item in self._cols

    Добавить   = Add
    Количество = Count
    Додати     = Add
    Кількість  = Count


class _VTRow:
    def __init__(self, columns: _VTColumnCollection):
        self._data: dict = {c: Undefined for c in columns}

    def __getitem__(self, key): return self._data.get(key, Undefined)
    def __setitem__(self, key, v): self._data[key] = v
    def __getattr__(self, name):
        if name.startswith("_"): raise AttributeError(name)
        return self._data.get(name, Undefined)
    def __setattr__(self, name, v):
        if name.startswith("_"): super().__setattr__(name, v)
        else: self._data[name] = v
    def __repr__(self): return f"Row({self._data})"


# ── ValueList ────────────────────────────────────────────────────────────────

class _ValueList:
    """1C СписокЗначений / ValueList."""
    def __init__(self):
        self._items: list[_ValueListItem] = []

    def Add(self, value=None, presentation: str = "", check: bool = False):
        item = _ValueListItem(value, presentation, check)
        self._items.append(item)
        return item

    def Count(self) -> int: return len(self._items)
    def Clear(self): self._items.clear()
    def FindByValue(self, v):
        for item in self._items:
            if item.Value == v: return item
        return Undefined

    def __iter__(self): return iter(self._items)
    def __len__(self): return len(self._items)

    # Russian aliases
    Добавить          = Add
    Количество        = Count
    Очистить          = Clear
    НайтиПоЗначению   = FindByValue
    # Ukrainian aliases
    Додати            = Add
    Кількість         = Count
    Очистити          = Clear
    ЗнайтиЗаЗначенням = FindByValue

СписокЗначень  = _ValueList
СписокЗначений = _ValueList


class _ValueListItem:
    def __init__(self, value, presentation: str = "", check: bool = False):
        self.Value        = value
        self.Presentation = presentation
        self.Check        = check
        self.Значение     = value
        self.Представление = presentation
        self.Пометка      = check


# ── Misc built-ins ───────────────────────────────────────────────────────────

def Message(text: str = "", *args):
    """1C Сообщить — print to output."""
    import sys as _sys
    print(str(text), flush=True)

def Alert(text: str = ""):
    print(f"[ALERT] {text}", flush=True)

def ErrorInfo():
    """Returns current exception info (stub for except blocks)."""
    return None

def ErrorDescription() -> str:
    return ""

# Russian aliases
Сообщить         = Message
Предупреждение   = Alert
ИнформацияОбОшибке = ErrorInfo
ОписаниеОшибки   = ErrorDescription

# ── Ukrainian aliases ─────────────────────────────────────────────────────────

# Date
ПоточнаДата        = CurrentDate
ПоточнаДатаЧас     = CurrentDateAndTime
ПочатокДня         = BegOfDay
КінецьДня          = EndOfDay
ПочатокМісяця      = BegOfMonth
КінецьМісяця       = EndOfMonth
ПочатокРоку        = BegOfYear
ДодатиМісяці       = AddMonth
ДодатиДні          = AddDays
ДеньТижня          = DayOfWeek

# Strings
ДовжинаРядка       = StrLen
Ліво               = Left
Право              = Right
Середина           = Mid
СкорЛП             = TrimAll
СкорЛ              = TrimL
СкорП              = TrimR
ВРегістр           = Upper
НРегістр           = Lower
Знайти             = Find
ЗамінитиРядок      = StrReplace
КількістьПідрядків = StrCount
РозбитиРядок       = StrSplit
ШаблонРядка        = StrTemplate
ПовторитиРядок     = StrRepeat
Символ             = Char    # same as Russian

# Numbers
Ціле               = Int
Округлити          = Round
Макс               = Max    # same spelling
Мін                = Min

# Type conversion
Рядок              = String
Число              = Number  # same as Russian
Булево             = Boolean # same
ТипЗнч             = TypeOf  # same

# Output
Повідомити         = Message
Попередження       = Alert
ІнформаціяПроПомилку = ErrorInfo
ОписПомилки        = ErrorDescription

# Collections (Ukrainian type names used with Новий)
Масив              = _Array
Відповідність      = _Map
Структура          = _Structure   # identical spelling in Uk/Ru
ТаблицяЗначень     = _ValueTable
СписокЗначень      = _ValueList   # same spelling in Uk/Ru
