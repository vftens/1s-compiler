"""Suggest Odoo models for 1C/BAS objects (Sprint 19).

Target: Odoo 17/18 Community core models. The suggestion is a starting point
for an integrator, matched by object kind and name stems (Russian, Ukrainian,
English). Every suggestion carries a note on what usually needs checking.
Objects with no rule are reported as "custom" — they need an Odoo module or
custom fields, and that list is the real migration scope.
"""
from __future__ import annotations

from dataclasses import dataclass

# (kinds, name stems in lower case, Odoo model, note). First match wins, so
# specific rules come before broad ones.
RULES: list[tuple[frozenset[str], tuple[str, ...], str, str]] = [
    # ── catalogs ────────────────────────────────────────────────────────────
    (frozenset({"catalog"}), ("банковскиесчета", "банківськірахунки", "bankaccount"), "res.partner.bank", "bank accounts of partners and the company"),
    (frozenset({"catalog"}), ("договор", "contract"), "custom", "checked before partners (ДоговорыКонтрагентов); no core contract model: sale.order terms, a field on res.partner, or an OCA contract module"),
    (frozenset({"catalog"}), ("номенклатур", "товар", "product", "item"), "product.template", "variants -> product.product; units -> uom.uom"),
    (frozenset({"catalog"}), ("контрагент", "партнер", "партнер", "покупател", "поставщик", "постачальник", "клієнт", "клиент", "counterpart", "partner", "customer", "vendor"), "res.partner", "one model for customers and vendors; check ЄДРПОУ/ІПН in vat/company_registry"),
    (frozenset({"catalog"}), ("организаци", "організаці", "company"), "res.company", "multi-company: one res.company per legal entity"),
    (frozenset({"catalog"}), ("подразделени", "підрозділ", "department"), "hr.department", ""),
    (frozenset({"catalog"}), ("должност", "посад", "position", "jobtitle"), "hr.job", ""),
    (frozenset({"catalog"}), ("сотрудник", "співробітник", "працівник", "физическиелица", "фізичніособи", "employee"), "hr.employee", "personal data: check what may be migrated"),
    (frozenset({"catalog"}), ("склад", "warehouse"), "stock.warehouse", "bins/cells -> stock.location"),
    (frozenset({"catalog"}), ("валют", "currenc"), "res.currency", "rates -> res.currency.rate"),
    (frozenset({"catalog"}), ("банк", "bank"), "res.bank", ""),
    (frozenset({"catalog"}), ("единицыизмерения", "одиницівиміру", "единицизмерения", "классификаторединиц", "unitsofmeasure", "uom"), "uom.uom", ""),
    (frozenset({"catalog"}), ("ставкиндс", "ставкипдв", "налог", "податк", "taxrate"), "account.tax", "map each rate to an account.tax with the right accounts"),
    (frozenset({"catalog"}), ("статьидвижения", "статтірух", "статьизатрат", "статтівитрат", "cashflowitem", "costitem"), "account.analytic.account", "or analytic plans/tags, depending on reporting"),
    (frozenset({"catalog"}), ("стран", "країн", "countr"), "res.country", "usually already present in Odoo"),
    (frozenset({"catalog"}), ("кассы", "каси", "cashdesk", "cashbox"), "account.journal", "type=cash"),
    # ── documents ───────────────────────────────────────────────────────────
    (frozenset({"document"}), ("реализаци", "реалізаці", "видаткованакладна", "расходнаянакладная", "отгрузк", "sales", "shipment"), "sale.order + account.move", "delivery -> stock.picking; invoice -> account.move (out_invoice)"),
    (frozenset({"document"}), ("поступлени", "надходжен", "прибуткованакладна", "приходнаянакладная", "purchase", "receipt"), "purchase.order + account.move", "receipt -> stock.picking; bill -> account.move (in_invoice)"),
    (frozenset({"document"}), ("заказклиента", "заказпокупател", "замовленняклієнта", "замовленняпокупця", "salesorder", "customerorder"), "sale.order", ""),
    (frozenset({"document"}), ("заказпоставщик", "замовленняпостачальник", "purchaseorder"), "purchase.order", ""),
    (frozenset({"document"}), ("счетнаоплату", "рахунокнаоплату", "invoice"), "sale.order", "quotation stage, or account.move draft"),
    (frozenset({"document"}), ("платежноепоручени", "платіжнедорученн", "платіжнедоручення", "списаниесрасчетного", "поступлениенарасчетный", "payment", "bankstatement"), "account.payment", "bank statements -> account.bank.statement.line"),
    (frozenset({"document"}), ("кассовыйордер", "касовийордер", "приходныйкассов", "расходныйкассов", "прибутковийкасов", "видатковийкасов", "cashreceipt", "cashpayment"), "account.payment", "journal of type cash"),
    (frozenset({"document"}), ("перемещени", "переміщенн", "transfer"), "stock.picking", "picking type: internal"),
    (frozenset({"document"}), ("инвентаризаци", "інвентаризаці", "inventory"), "stock.quant", "inventory adjustment"),
    (frozenset({"document"}), ("списаниетовар", "списаннятовар", "writeoff", "scrap"), "stock.scrap", ""),
    (frozenset({"document"}), ("операциябух", "операціябух", "ручнаяоперация", "ручнаоперація", "journalentry", "manualoperation"), "account.move", "move_type=entry"),
    (frozenset({"document"}), ("начислениезарплат", "нарахуваннязарплат", "зарплат", "payroll"), "hr.payslip", "payroll is not in Odoo Community core: Enterprise or OCA payroll + a UA localisation"),
    (frozenset({"document"}), ("авансовыйотчет", "авансовийзвіт", "expensereport"), "hr.expense", ""),
    # ── registers ───────────────────────────────────────────────────────────
    (frozenset({"accounting_register"}), ("",), "account.move.line", "posted journal items; check opening balances"),
    (frozenset({"chart_of_accounts"}), ("",), "account.account", "UA chart of accounts: l10n_ua or a custom chart"),
    (frozenset({"accumulation_register"}), ("товарынаскладах", "остаткитовар", "товаринаскладах", "залишкитовар", "stock", "inventory"), "stock.quant", "history -> stock.move.line"),
    (frozenset({"accumulation_register"}), ("взаиморасчет", "взаєморозрахунк", "расчетыс", "розрахункиз", "settlement"), "account.move.line", "receivable/payable lines"),
    (frozenset({"accumulation_register"}), ("продажи", "продажі", "sales"), "sale.report", "report view; recompute from orders/invoices"),
    (frozenset({"information_register"}), ("ценыноменклатур", "ціниноменклатур", "цены", "ціни", "price"), "product.pricelist.item", ""),
    (frozenset({"information_register"}), ("курсывалют", "курсивалют", "exchangerate", "currencyrate"), "res.currency.rate", ""),
    # ── enums and constants ─────────────────────────────────────────────────
    (frozenset({"enum"}), ("",), "selection field", "becomes a Selection on the model that uses it"),
    (frozenset({"constant"}), ("",), "res.config.settings", "or ir.config_parameter"),
]

# Objects that carry no data to migrate.
SKIP_KINDS = frozenset({"common_module", "common_form", "role", "subsystem", "report", "data_processor"})


@dataclass
class Suggestion:
    model: str      # Odoo model(s), "custom", or "" for kinds that carry no data
    note: str
    matched: str    # the stem that matched ("" = by kind only)


def _norm(name: str) -> str:
    return name.lower().replace("_", "").replace(" ", "").replace("'", "").replace("ʼ", "")


def suggest(kind: str, name: str) -> Suggestion:
    if kind in SKIP_KINDS:
        return Suggestion("", "no data to migrate (code, forms, roles)", "")
    n = _norm(name)
    for kinds, stems, model, note in RULES:
        if kind in kinds:
            for stem in stems:
                if stem in n:
                    return Suggestion(model, note, stem)
    return Suggestion("custom", "no core equivalent found: custom model or fields", "")
