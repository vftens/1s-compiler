"""
Tests for src.runtime.types — runtime built-ins.
"""
import datetime
import pytest
from src.runtime.types import (
    # Undefined
    Undefined, _Undefined,
    # Strings
    StrLen, Left, Right, Mid, TrimAll, TrimL, TrimR,
    Upper, Lower, Find, StrReplace, StrCount, StrSplit,
    StrTemplate, StrRepeat, Format, Char,
    # Numeric
    Int, Round, Abs, Max, Min, Pow, Sqrt,
    # Type conversion
    String, Number, Boolean, TypeOf,
    # Date
    CurrentDate, BegOfDay, EndOfDay, BegOfMonth, AddMonth, AddDays, DayOfWeek,
    # Collections
    _Array, _Map, _Structure, _ValueTable, _ValueList,
    # Exception
    _1SException,
    # Russian/Ukrainian aliases
    СтрШаблон, ШаблонРядка, Повідомити, Сообщить,
    Масив, Відповідність,
)
# Some aliases may differ — import selectively
from src.runtime.types import Массив as RuArray
from src.runtime.types import Масив


# ── Undefined ────────────────────────────────────────────────────────────────

class TestUndefined:
    def test_singleton(self):
        assert Undefined is _Undefined()

    def test_falsy(self):
        assert not Undefined

    def test_repr(self):
        assert repr(Undefined) == "Undefined"

    def test_equality(self):
        assert Undefined == _Undefined()

    def test_not_equal_to_none(self):
        assert Undefined != None  # noqa: E711


# ── 1SException ───────────────────────────────────────────────────────────────

class TestException:
    def test_message(self):
        exc = _1SException("test error")
        assert exc.message == "test error"
        assert exc.Description() == "test error"

    def test_catch_as_exception(self):
        with pytest.raises(Exception):
            raise _1SException("boom")


# ── String functions ──────────────────────────────────────────────────────────

class TestStrLen:
    def test_ascii(self):
        assert StrLen("hello") == 5

    def test_empty(self):
        assert StrLen("") == 0

    def test_cyrillic(self):
        assert StrLen("Привет") == 6


class TestLeft:
    def test_basic(self):
        assert Left("abcdef", 3) == "abc"

    def test_longer_than_string(self):
        assert Left("ab", 10) == "ab"

    def test_zero(self):
        assert Left("abc", 0) == ""


class TestRight:
    def test_basic(self):
        assert Right("abcdef", 3) == "def"

    def test_longer_than_string(self):
        assert Right("ab", 10) == "ab"


class TestMid:
    def test_basic(self):
        assert Mid("abcdef", 2, 3) == "bcd"

    def test_1indexed(self):
        assert Mid("abcdef", 1, 1) == "a"

    def test_no_length(self):
        assert Mid("abcdef", 4) == "def"


class TestTrim:
    def test_trimall(self):
        assert TrimAll("  hello  ") == "hello"

    def test_triml(self):
        assert TrimL("  hello  ") == "hello  "

    def test_trimr(self):
        assert TrimR("  hello  ") == "  hello"


class TestCase:
    def test_upper(self):
        assert Upper("hello") == "HELLO"

    def test_lower(self):
        assert Lower("HELLO") == "hello"


class TestFind:
    def test_found(self):
        assert Find("hello world", "world") == 7  # 1-indexed

    def test_not_found(self):
        assert Find("hello", "xyz") == 0

    def test_at_start(self):
        assert Find("abc", "a") == 1


class TestStrReplace:
    def test_basic(self):
        assert StrReplace("hello world", "world", "1S") == "hello 1S"

    def test_no_match(self):
        assert StrReplace("hello", "xyz", "abc") == "hello"


class TestStrCount:
    def test_count(self):
        assert StrCount("abcabc", "abc") == 2

    def test_not_found(self):
        assert StrCount("hello", "xyz") == 0


class TestStrSplit:
    def test_basic(self):
        arr = StrSplit("a,b,c", ",")
        assert arr.Count() == 3
        assert arr[0] == "a"
        assert arr[2] == "c"

    def test_no_split(self):
        arr = StrSplit("abc", ",")
        assert arr.Count() == 1


class TestChar:
    def test_latin_a(self):
        assert Char(65) == "A"

    def test_newline(self):
        assert Char(10) == "\n"


# ── StrTemplate ───────────────────────────────────────────────────────────────

class TestStrTemplate:
    def test_1c_single_placeholder(self):
        assert StrTemplate("Hello %1!", "world") == "Hello world!"

    def test_1c_multiple_placeholders(self):
        assert StrTemplate("%1 + %2 = %3", 1, 2, 3) == "1 + 2 = 3"

    def test_1c_percent_escape(self):
        assert StrTemplate("100%%") == "100%"

    def test_1c_order_independent(self):
        # %2 before %1 should still work
        assert StrTemplate("%2-%1", "A", "B") == "B-A"

    def test_1c_double_digit_not_split(self):
        # %10 should use arg[9], not %1 + "0"
        args = [str(i) for i in range(1, 11)]
        result = StrTemplate("%10", *args)
        assert result == "10"

    def test_printf_style(self):
        # printf style when no bare %N
        result = StrTemplate("%-5s|", "hi")
        assert result == "hi   |"

    def test_alias_strshablone(self):
        assert СтрШаблон("x=%1", 42) == "x=42"

    def test_alias_ukrainian(self):
        assert ШаблонРядка("x=%1", 42) == "x=42"


# ── Format ────────────────────────────────────────────────────────────────────

class TestFormat:
    def test_decimal_places(self):
        assert Format(3.14159, "ЧДЦ=2") == "3.14"

    def test_zero_decimal_places(self):
        assert Format(42, "ЧДЦ=0") == "42"

    def test_right_justify(self):
        result = Format(5, "ЧЦ=5")
        assert result == "    5"

    def test_date_format_dd_mm_yyyy(self):
        d = datetime.date(2025, 1, 15)
        assert Format(d, "ДФ=дд.ММ.гггг") == "15.01.2025"

    def test_no_format(self):
        assert Format(42, "") == "42"


# ── Numeric functions ─────────────────────────────────────────────────────────

class TestNumeric:
    def test_int_truncates(self):
        assert Int(3.9) == 3

    def test_int_negative(self):
        assert Int(-3.9) == -3

    def test_round_half(self):
        assert Round(2.5) == 2 or Round(2.5) == 3  # banker's rounding or standard

    def test_round_decimals(self):
        assert Round(3.14159, 2) == 3.14

    def test_abs_positive(self):
        assert Abs(-5) == 5
        assert Abs(5) == 5

    def test_max(self):
        assert Max(1, 5, 3) == 5

    def test_min(self):
        assert Min(1, 5, 3) == 1

    def test_pow(self):
        assert Pow(2, 10) == 1024

    def test_sqrt(self):
        assert abs(Sqrt(9) - 3.0) < 1e-9


# ── Type conversion ───────────────────────────────────────────────────────────

class TestTypeConversion:
    def test_string_int(self):
        assert String(42) == "42"

    def test_string_undefined(self):
        assert String(Undefined) == ""

    def test_number_string(self):
        from decimal import Decimal
        assert Number("42") == Decimal("42")

    def test_boolean_truthy(self):
        assert Boolean(1) is True
        assert Boolean("") is False

    def test_typeof_int(self):
        assert TypeOf(1) == "Number"

    def test_typeof_str(self):
        assert TypeOf("hello") == "String"

    def test_typeof_bool(self):
        assert TypeOf(True) == "Boolean"

    def test_typeof_date(self):
        assert TypeOf(datetime.date.today()) == "Date"

    def test_typeof_undefined(self):
        assert TypeOf(Undefined) == "Undefined"


# ── Date functions ────────────────────────────────────────────────────────────

class TestDateFunctions:
    def test_beg_of_day(self):
        d = datetime.date(2025, 6, 15)
        bd = BegOfDay(d)
        assert bd == datetime.datetime(2025, 6, 15, 0, 0, 0)

    def test_end_of_day(self):
        d = datetime.date(2025, 6, 15)
        ed = EndOfDay(d)
        assert ed.hour == 23 and ed.minute == 59

    def test_beg_of_month(self):
        d = datetime.date(2025, 3, 20)
        bm = BegOfMonth(d)
        assert bm.day == 1

    def test_add_month(self):
        d = datetime.date(2025, 1, 31)
        result = AddMonth(d, 1)
        assert result.month == 2

    def test_add_days(self):
        d = datetime.date(2025, 1, 1)
        result = AddDays(d, 10)
        assert result.day == 11

    def test_day_of_week_monday(self):
        monday = datetime.date(2025, 1, 6)  # Monday
        assert DayOfWeek(monday) == 1

    def test_day_of_week_sunday(self):
        sunday = datetime.date(2025, 1, 5)  # Sunday
        assert DayOfWeek(sunday) == 7


# ── Array ─────────────────────────────────────────────────────────────────────

class TestArray:
    def test_add_and_count(self):
        a = _Array()
        a.Add(1)
        a.Add(2)
        assert a.Count() == 2

    def test_get_item(self):
        a = _Array()
        a.Add("hello")
        assert a[0] == "hello"
        assert a.Get(0) == "hello"

    def test_set_item(self):
        a = _Array()
        a.Add(1)
        a.Set(0, 99)
        assert a[0] == 99

    def test_delete(self):
        a = _Array()
        a.Add(1)
        a.Add(2)
        a.Delete(0)
        assert a.Count() == 1
        assert a[0] == 2

    def test_find_found(self):
        a = _Array()
        a.Add("x")
        a.Add("y")
        assert a.Find("x") == 0

    def test_find_not_found(self):
        a = _Array()
        a.Add("x")
        assert a.Find("z") is Undefined

    def test_iteration(self):
        a = _Array()
        for i in range(5):
            a.Add(i)
        assert list(a) == [0, 1, 2, 3, 4]

    def test_clear(self):
        a = _Array()
        a.Add(1)
        a.Clear()
        assert a.Count() == 0

    def test_insert(self):
        a = _Array()
        a.Add(1)
        a.Add(3)
        a.Insert(1, 2)
        assert list(a) == [1, 2, 3]

    def test_russian_aliases(self):
        a = RuArray()
        a.Добавить(10)
        assert a.Количество() == 1

    def test_ukrainian_aliases(self):
        a = Масив()
        a.Додати(10)
        assert a.Кількість() == 1


# ── Map ───────────────────────────────────────────────────────────────────────

class TestMap:
    def test_insert_and_get(self):
        m = _Map()
        m.Insert("key", "value")
        assert m.Get("key") == "value"

    def test_subscript(self):
        m = _Map()
        m["a"] = 1
        assert m["a"] == 1

    def test_missing_key_returns_undefined(self):
        m = _Map()
        assert m.Get("missing") is Undefined

    def test_delete(self):
        m = _Map()
        m["x"] = 1
        m.Delete("x")
        assert m["x"] is Undefined

    def test_count(self):
        m = _Map()
        m["a"] = 1
        m["b"] = 2
        assert m.Count() == 2

    def test_iteration_yields_key_value(self):
        m = _Map()
        m["USD"] = 41.5
        pairs = list(m)
        assert pairs[0].Key == "USD"
        assert pairs[0].Value == 41.5

    def test_ukrainian_alias(self):
        m = Відповідність()
        m["к"] = "в"
        assert m["к"] == "в"


# ── Structure ─────────────────────────────────────────────────────────────────

class TestStructure:
    def test_init_with_keys(self):
        s = _Structure("Name, Age", "Ivan", 30)
        assert s.Name == "Ivan"
        assert s.Age == 30

    def test_set_attribute(self):
        s = _Structure()
        s.City = "Kyiv"
        assert s.City == "Kyiv"

    def test_missing_attribute_returns_undefined(self):
        s = _Structure()
        assert s.NonExistent is Undefined

    def test_count(self):
        s = _Structure("A, B, C", 1, 2, 3)
        assert s.Count() == 3

    def test_iteration(self):
        s = _Structure("X", 42)
        kv_list = list(s)
        assert kv_list[0].Key == "X"
        assert kv_list[0].Value == 42

    def test_insert_method(self):
        s = _Structure()
        s.Insert("Key", "Val")
        assert s.Key == "Val"

    def test_delete_method(self):
        s = _Structure("A, B", 1, 2)
        s.Delete("A")
        assert s.Count() == 1


# ── ValueTable ────────────────────────────────────────────────────────────────

class TestValueTable:
    def _make_table(self):
        t = _ValueTable()
        t.Columns.Add("Name")
        t.Columns.Add("Amount")
        return t

    def test_add_row(self):
        t = self._make_table()
        row = t.Add()
        row["Name"] = "Борошно"
        row["Amount"] = 100
        assert t.Count() == 1

    def test_find_row(self):
        t = self._make_table()
        r = t.Add()
        r["Name"] = "Цукор"
        r["Amount"] = 50
        found = t.Find("Цукор", "Name")
        assert found is r

    def test_find_missing(self):
        t = self._make_table()
        assert t.Find("xyz", "Name") is Undefined

    def test_total(self):
        t = self._make_table()
        for amt in [100, 200, 300]:
            r = t.Add()
            r["Amount"] = amt
        from decimal import Decimal
        assert t.Total("Amount") == Decimal("600")

    def test_iteration(self):
        t = self._make_table()
        for i in range(3):
            r = t.Add()
            r["Name"] = str(i)
        names = [row["Name"] for row in t]
        assert names == ["0", "1", "2"]

    def test_sort(self):
        t = self._make_table()
        for v in [3, 1, 2]:
            r = t.Add()
            r["Amount"] = v
        t.Sort("Amount", "ASC")
        assert t[0]["Amount"] == 1
        assert t[2]["Amount"] == 3

    def test_clear(self):
        t = self._make_table()
        t.Add()
        t.Add()
        t.Clear()
        assert t.Count() == 0


# ── ValueList ─────────────────────────────────────────────────────────────────

class TestValueList:
    def test_add_and_count(self):
        vl = _ValueList()
        vl.Add("item1")
        vl.Add("item2")
        assert vl.Count() == 2

    def test_find_by_value(self):
        vl = _ValueList()
        vl.Add("x", "X label")
        item = vl.FindByValue("x")
        assert item.Value == "x"
        assert item.Presentation == "X label"

    def test_not_found(self):
        vl = _ValueList()
        assert vl.FindByValue("missing") is Undefined
