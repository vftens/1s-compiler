"""
Tests for src.runtime.catalogs — Catalog and Document classes.
"""
import datetime
import pytest
from src.runtime.catalogs import (
    Catalog, Document, TabularSection,
    Справочник, Довідник, Документ,
)
from src.runtime.types import Undefined


# ── Catalog ───────────────────────────────────────────────────────────────────

class TestCatalog:
    def test_create_item(self):
        c = Catalog("Goods")
        item = c.Create("001", "Flour")
        assert item.Code == "001"
        assert item.Name == "Flour"

    def test_auto_code(self):
        c = Catalog("Test")
        item = c.Create(name="Auto")
        assert item.Code != ""
        assert item.Name == "Auto"

    def test_find_by_code(self):
        c = Catalog("Goods")
        c.Create("001", "Flour")
        found = c.FindByCode("001")
        assert found.Name == "Flour"

    def test_find_by_code_missing(self):
        c = Catalog("Goods")
        assert c.FindByCode("999") is Undefined

    def test_find_by_name(self):
        c = Catalog("Goods")
        c.Create("001", "Flour")
        found = c.FindByName("Flour")
        assert found.Code == "001"

    def test_find_by_name_missing(self):
        c = Catalog("Goods")
        assert c.FindByName("NonExistent") is Undefined

    def test_count(self):
        c = Catalog("Goods")
        c.Create("001", "Flour")
        c.Create("002", "Sugar")
        assert c.Count() == 2

    def test_iteration(self):
        c = Catalog("Goods")
        c.Create("001", "Flour")
        c.Create("002", "Sugar")
        names = [item.Name for item in c]
        assert "Flour" in names
        assert "Sugar" in names

    def test_select(self):
        c = Catalog("Goods")
        c.Create("001", "Flour")
        sel = c.Select()
        results = []
        while sel.Next():
            results.append(sel.Current().Name)
        assert results == ["Flour"]

    def test_extra_attributes(self):
        c = Catalog("Goods")
        item = c.Create("001", "Flour")
        item.Unit = "kg"
        item.Price = 45.0
        assert item.Unit == "kg"
        assert item.Price == 45.0

    def test_missing_attribute_returns_undefined(self):
        c = Catalog("Goods")
        item = c.Create("001", "Flour")
        assert item.NonExistentField is Undefined

    def test_cyrillic_code(self):
        c = Catalog("Товари")
        item = c.Створити("Т001", "Борошно")
        assert item.Код == "Т001"
        assert item.Назва == "Борошно"

    def test_russian_aliases(self):
        c = Справочник("Контрагенты")
        item = c.Создать("001", "ООО Альфа")
        assert c.Количество() == 1
        assert c.НайтиПоКоду("001").Наименование == "ООО Альфа"

    def test_ukrainian_aliases(self):
        c = Довідник("Контрагенти")
        item = c.Створити("001", "ТОВ Альфа")
        assert c.Кількість() == 1
        assert c.НайтиЗаКодом("001").Назва == "ТОВ Альфа"

    def test_item_equality_by_code(self):
        c = Catalog("Goods")
        a = c.Create("001", "Flour v1")
        b = c.Create("001", "Flour v2")   # same code → replaces
        # Both point to same code
        assert a == b

    def test_item_str_is_name(self):
        c = Catalog("Goods")
        item = c.Create("001", "Flour")
        assert str(item) == "Flour"

    def test_len(self):
        c = Catalog("Test")
        c.Create("1", "A")
        c.Create("2", "B")
        assert len(c) == 2


# ── Document ──────────────────────────────────────────────────────────────────

class TestDocument:
    def setup_method(self):
        # Reset counters for deterministic numbering in each test
        Document._counters.clear()

    def test_auto_number(self):
        doc = Document("Invoice")
        assert doc.Number == "000001"
        doc2 = Document("Invoice")
        assert doc2.Number == "000002"

    def test_different_types_independent_counters(self):
        Document._counters.clear()
        inv = Document("Invoice")
        po  = Document("PurchaseOrder")
        assert inv.Number == "000001"
        assert po.Number  == "000001"

    def test_default_date_is_today(self):
        doc = Document("Test")
        assert doc.Date == datetime.date.today()

    def test_set_date(self):
        doc = Document("Invoice")
        doc.Date = datetime.date(2025, 1, 15)
        assert doc.Date == datetime.date(2025, 1, 15)

    def test_arbitrary_attributes(self):
        doc = Document("Invoice")
        doc.Customer = "Alpha LLC"
        doc.Amount   = 50000
        assert doc.Customer == "Alpha LLC"
        assert doc.Amount   == 50000

    def test_missing_attribute_returns_undefined(self):
        doc = Document("Invoice")
        assert doc.NonExistent is Undefined

    def test_post(self):
        doc = Document("Invoice")
        assert not doc.IsPosted
        result = doc.Post()
        assert result is True
        assert doc.IsPosted
        assert doc.Проведён

    def test_unpost(self):
        doc = Document("Invoice")
        doc.Post()
        doc.Unpost()
        assert not doc.IsPosted

    def test_write_does_not_raise(self):
        doc = Document("Invoice")
        doc.Write()   # in-memory no-op — should not raise

    def test_tab_section_create(self):
        doc = Document("Invoice")
        lines = doc.TabSection("Lines", "Product, Qty, Price")
        assert lines is not None
        assert "Product" in lines.Columns

    def test_tab_section_get_same_instance(self):
        doc = Document("Invoice")
        t1 = doc.TabSection("Lines", "Product, Qty")
        t2 = doc.TabSection("Lines")   # get existing
        assert t1 is t2

    def test_tab_section_add_rows(self):
        doc = Document("Invoice")
        lines = doc.TabSection("Lines", "Product, Qty, Price, Amount")
        row = lines.Add()
        row["Product"] = "Flour"
        row["Qty"]     = 100
        row["Price"]   = 45.0
        row["Amount"]  = 4500
        assert lines.Count() == 1
        assert lines[0]["Product"] == "Flour"

    def test_tab_section_total(self):
        doc = Document("Invoice")
        lines = doc.TabSection("Lines", "Product, Amount")
        for amt in [1000, 2000, 3000]:
            row = lines.Add()
            row["Amount"] = amt
        from decimal import Decimal
        assert lines.Total("Amount") == Decimal("6000")

    def test_tab_section_iteration(self):
        doc = Document("Invoice")
        lines = doc.TabSection("Lines", "Name")
        for name in ["A", "B", "C"]:
            r = lines.Add()
            r["Name"] = name
        names = [r["Name"] for r in lines]
        assert names == ["A", "B", "C"]

    def test_cyrillic_aliases(self):
        doc = Документ("Видаткова")
        lines = doc.ТабличнаЧастина("Товари", "Назва, Кількість")
        рядок = lines.Додати()
        рядок["Назва"] = "Борошно"
        рядок["Кількість"] = 500
        assert lines.Кількість() == 1

    def test_russian_aliases(self):
        doc = Документ("Расходная")
        lines = doc.ТабличнаяЧасть("Товары", "Наим, Кол")
        r = lines.Добавить()
        r["Наим"] = "Мука"
        r["Кол"]  = 500
        assert lines.Количество() == 1

    def test_repr(self):
        doc = Document("Invoice")
        assert "Invoice" in repr(doc)
        assert "000001" in repr(doc)

    def test_str(self):
        doc = Document("SalesOrder")
        assert "SalesOrder" in str(doc)
        assert "000001" in str(doc)


# ── Full pipeline: Catalog + Document ────────────────────────────────────────

class TestCatalogDocumentPipeline:
    def setup_method(self):
        Document._counters.clear()

    def test_catalog_item_as_doc_attribute(self):
        customers = Catalog("Customers")
        alpha = customers.Create("001", "Alpha LLC")
        alpha.TaxId = "1234567890"

        invoice = Document("Invoice")
        invoice.Customer = alpha

        assert invoice.Customer.Name == "Alpha LLC"
        assert invoice.Customer.TaxId == "1234567890"

    def test_full_sales_flow(self):
        goods = Catalog("Goods")
        flour = goods.Create("G001", "Flour")
        flour.Price = 45.0

        inv = Document("SalesInvoice")
        lines = inv.TabSection("Lines", "Product, Qty, Price, Amount")

        row = lines.Add()
        row["Product"] = flour.Name
        row["Qty"]     = 100
        row["Price"]   = flour.Price * 1.2   # 20% markup
        row["Amount"]  = 100 * flour.Price * 1.2

        inv.Post()

        from decimal import Decimal
        total = lines.Total("Amount")
        assert total == Decimal("5400.0")
        assert inv.IsPosted
