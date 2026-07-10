<!-- /autoplan restore point: /c/Users/DrVITAL/.gstack/projects/1s-compiler/sprint-14-lp-solver-autoplan-restore-20260710-155223.md -->
# Sprint 14 Plan — Linear Programming Solver + ERP Optimization

**Branch:** `sprint-14-lp-solver`
**Target date:** 2026-07-11

---

## Context

Sprint 13 lands Excel/PDF export, Bearer token auth, and script persistence. The
REST API is now machine-callable without a browser session. Sprint 14 adds the
mathematical optimization layer: a Linear Programming engine that `.1s` scripts
and REST clients can use to solve allocation and planning problems directly against
ERP data.

**Gap:** ERP systems do budgeting, payroll, and procurement — but they cannot
*optimize* those processes. An accountant can see that dept-01 consumed 90% of
its budget and dept-02 only 40%, but cannot ask the system "how should we
reallocate these funds to maximize output subject to constraints?" LP fills that gap.

---

## Sprint 14 Scope

### Deliverable 1 — `LPSolver` class (`src/runtime/lp.py`)

A `.1s`-scriptable LP solver backed by `scipy.optimize.linprog` (HiGHS, already
installed). The public API follows the 1C pattern: create an object, configure it,
call Solve.

```
Солвер = НовыйСолвер()                         // Russian
Солвер.Минимизировать([1, 2, 3])                // objective: min x0 + 2*x1 + 3*x2
Солвер.ДобавитьОграничениеНеравенство([1, 1, 0], 100)   // x0 + x1 ≤ 100
Солвер.ДобавитьОграничениеРавенство([0, 0, 1], 50)      // x2 = 50
Солвер.УстановитьГраницы(0, Неопределено, 0)    // x0 ≥ 0, x1 ≥ 0, x2 ≥ 0
Результат = Солвер.Решить()
Повідомити(Результат.Статус)                    // "optimal"
Повідомити(Результат.Значения)                  // [x0, x1, x2]
Повідомити(Результат.ЦелевоеЗначение)           // objective value
```

**Solver API methods** (each trilingual RU/UK/EN):

| Method (EN) | What it does |
|-------------|--------------|
| `Minimize(c)` | Set objective coefficients (list), minimize |
| `Maximize(c)` | Negate coefficients, minimize (scipy convention) |
| `AddInequalityConstraint(row, rhs)` | Add A_ub row and b_ub value (≤) |
| `AddEqualityConstraint(row, rhs)` | Add A_eq row and b_eq value (=) |
| `SetBounds(lo, hi, var_index)` | Set lower/upper bound on one variable; None = unbounded |
| `SetVarCount(n)` | Declare n variables (optional if inferred from objective) |
| `Solve()` | Call scipy.optimize.linprog, return `LPResult` |

**`LPResult` attributes:**

| Attribute (EN) | Type | Meaning |
|----------------|------|---------|
| `Status` | str | `"optimal"`, `"infeasible"`, `"unbounded"`, `"error"` |
| `Values` | list[float] | Decision variable values (None if not optimal) |
| `ObjectiveValue` | float | c·x at solution (None if not optimal) |
| `ShadowPrices` | list[float] | Dual variables for inequality constraints (sensitivity) |
| `Message` | str | Solver message for non-optimal cases |

**Trilingual aliases — full set:**

RU: `НовыйСолвер` / `Минимизировать` / `Максимизировать` / `ДобавитьОграничениеНеравенство` /
`ДобавитьОграничениеРавенство` / `УстановитьГраницы` / `КоличествоПеременных` / `Решить` /
`Статус` / `Значения` / `ЦелевоеЗначение` / `ТеневыеЦены` / `Сообщение`

UK: `НовийСолвер` / `Мінімізувати` / `Максимізувати` / `ДодатиОбмеженняНерівності` /
`ДодатиОбмеженняРівності` / `ВстановитиМежі` / `КількістьЗмінних` / `Вирішити` /
`Статус` / `Значення` / `ЦільовеЗначення` / `ТіньовіЦіни` / `Повідомлення`

EN: `LPSolver` / `Minimize` / `Maximize` / `AddInequalityConstraint` /
`AddEqualityConstraint` / `SetBounds` / `SetVarCount` / `Solve` /
`Status` / `Values` / `ObjectiveValue` / `ShadowPrices` / `Message`

**Internal design:**
- `LPSolver.__init__` stores `_c`, `_A_ub`, `_b_ub`, `_A_eq`, `_b_eq`, `_bounds`
- `Solve()` calls `scipy.optimize.linprog(c, A_ub, b_ub, A_eq, b_eq, bounds, method="highs")`
- `method="highs"` is default in scipy 1.7+; returns dual values via `result.ineqlin.marginals`
- Infeasible/unbounded: return `LPResult` with appropriate `Status`, no crash
- Input validation: all rows must have same length as `_c`; raise `ValueError` on mismatch

### Deliverable 1a — ERP LP helpers (`src/runtime/lp.py`, same file)

Two higher-level classes that pull from `erp.db` and formulate LP problems automatically:

**`BudgetAllocator`** — given a period, reads `budget_allocations` and `budget_entries`
from `erp.db`, formulates the LP problem "reallocate remaining budget across org units
to maximize weighted utilization subject to total budget cap", returns optimal allocation
per org unit.

```
Аллокатор = НовыйАллокаторБюджета("erp.db", "2024-01")
Аллокатор.УстановитьВеса({"dept-01": 1.5, "dept-02": 1.0})   // priority weights
Результат = Аллокатор.Оптимизировать()
Для каждого Строка Из Результат.Строки() Цикл
    Повідомити(Строка["org_id"] + ": " + Строка["recommended_allocation"])
КонецЦикла;
```

**`ResourceAllocator`** — given a list of tasks (demand) and resources (capacity),
formulates the assignment LP (transportation problem variant) and solves it.

```
РА = НовыйАллокаторРесурсов()
РА.ДобавитьРесурс("Иванов", 160)    // name, capacity (hours)
РА.ДобавитьРесурс("Петров", 120)
РА.ДобавитьЗадачу("Проект А", 80)   // name, demand
РА.ДобавитьЗадачу("Проект Б", 100)
Результат = РА.Решить()
```

### Deliverable 2 — REST endpoint `POST /api/v1/lp/solve`

Machine-callable LP solver via REST (no browser session needed; accepts Bearer token):

```
POST /api/v1/lp/solve
Authorization: Bearer <token>
Content-Type: application/json

{
  "objective": [1, 2, 3],
  "direction": "minimize",          // "minimize" | "maximize"
  "inequality_constraints": [
    {"coefficients": [1, 1, 0], "rhs": 100}
  ],
  "equality_constraints": [
    {"coefficients": [0, 0, 1], "rhs": 50}
  ],
  "bounds": [[0, null], [0, null], [0, null]]  // [lo, hi] per variable; null = unbounded
}

→ 200 {
    "status": "optimal",
    "values": [50.0, 0.0, 50.0],
    "objective_value": 200.0,
    "shadow_prices": [-1.0],
    "message": "Optimization terminated successfully.",
    "variables_count": 3,
    "constraints_count": 2
  }
→ 400 {"error": "Row length mismatch: objective has 3 variables, constraint row has 2"}
→ 422 {"status": "infeasible", "message": "The problem is infeasible.", "values": null}
→ 401 {"error": "Unauthorized", "hint": "Use Authorization: Bearer <token> or log in via /login"}
```

Validation rules:
- All constraint `coefficients` arrays must be same length as `objective`
- `direction` must be `"minimize"` or `"maximize"`
- `bounds` array (if provided) must be same length as `objective`
- Empty `objective` → 400

### Deliverable 3 — `/lp-solver` dashboard page

Browser-based LP problem builder. Accessible from the nav bar (after `/erp-dashboard`).

Layout:
- **Objective section**: direction toggle (Min/Max), coefficient inputs (dynamic: add/remove variable buttons)
- **Constraints section**: inequality (≤) tab and equality (=) tab; add constraint row button; each row has coefficient inputs + RHS input
- **Bounds section**: per-variable lower/upper bound inputs
- **Solve button**: POSTs to `/api/v1/lp/solve`, displays result in a result panel
- **Result panel**: status badge (green=optimal, red=infeasible/unbounded), variable values table, objective value, shadow prices table

No external CDN. Uses same Canvas-free pure JS pattern as ERP dashboard.

### Deliverable 4 — Demo scripts

Three new demo scripts (RU / UK / EN):

| Script | What it demonstrates |
|--------|---------------------|
| `demo_lp_budget_ru.1s` | Budget reallocation LP — RU: maximize weighted utilization |
| `demo_lp_resources_uk.1s` | Resource assignment LP — UK: min cost assignment |
| `demo_lp_solver_en.1s` | General LP — EN: classic diet problem (min cost, nutrition constraints) |

---

## Architecture

```
src/
  server.py              ← 2 new routes: POST /api/v1/lp/solve, GET /lp-solver
  runtime/
    lp.py                ← NEW: LPSolver, LPResult, BudgetAllocator, ResourceAllocator
                            + trilingual RU/UK/EN aliases
  __init__.py            ← add LPSolver, НовыйСолвер, НовийСолвер exports
src/templates/
  lp_solver.html         ← NEW: LP problem builder UI
  base.html              ← add LP Solver nav link
examples/
  demo_lp_budget_ru.1s
  demo_lp_resources_uk.1s
  demo_lp_solver_en.1s
```

No new pip dependencies. `scipy` (1.17.0) is already installed and provides
`linprog` with the HiGHS backend that returns dual/shadow price data.

---

## Security

- `POST /api/v1/lp/solve`: all input validated before reaching scipy — array length
  checks, type coercion (`float()`), no eval, no dynamic code execution
- Bounds `null` → `None` mapping handled explicitly (JSON null must not reach scipy
  as the string `"null"`)
- Max problem size limit: `len(objective) ≤ 500` variables, `len(constraints) ≤ 1000`
  rows — prevents DoS via huge LP problems (HiGHS can take seconds on large problems)
- `BudgetAllocator` reads `erp.db` via the same read-only connection pattern from Sprint 12
- `@login_required` on `/lp-solver` page; Bearer token accepted on `/api/v1/lp/solve`

---

## Test Plan

New test file: `tests/test_sprint14.py` (target: 24+ tests)

```
TestLPSolverBasic
  test_minimize_simple
  test_maximize_simple
  test_infeasible_returns_status_not_raises
  test_unbounded_returns_status_not_raises
  test_equality_constraint
  test_bounds_respected
  test_shadow_prices_returned
  test_mismatched_row_raises_value_error

TestLPSolverERP
  test_budget_allocator_reads_erp_db
  test_budget_allocator_respects_weights
  test_resource_allocator_balances_load
  test_resource_allocator_infeasible_over_capacity

TestLPRestEndpoint
  test_solve_minimize_returns_200
  test_solve_maximize_returns_200
  test_solve_infeasible_returns_422
  test_solve_invalid_row_length_returns_400
  test_solve_empty_objective_returns_400
  test_solve_unauthenticated_returns_401
  test_solve_bounds_null_handled

TestLPDashboard
  test_lp_solver_page_returns_200
  test_lp_solver_unauthenticated_redirects

TestLPTrilingualAliases
  test_russian_aliases_minimize
  test_ukrainian_aliases_maximize
  test_english_alias_exists

TestLPDemoScripts
  test_demo_lp_solver_en_runs
```

---

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|---------|
| 1 | CEO | scipy.linprog over PuLP | Mechanical | P1+P5 | scipy already installed (1.17.0); PuLP adds a new dependency with no payoff | pip install pulp |
| 2 | CEO | HiGHS method (default in scipy 1.7+) | Mechanical | P1 | Returns dual/shadow prices via result.ineqlin.marginals; simplex does not | method="revised simplex" |
| 3 | CEO | Include BudgetAllocator + ResourceAllocator | Mechanical | P2 | ERP-specific helpers make the LP engine immediately useful to accountants, not just mathematicians | LP engine only |
| 4 | Eng | Max 500 vars / 1000 constraints DoS limit | Mechanical | P5 | HiGHS on a 1000×1000 LP can take 30s+; REST endpoint needs a size cap | Unlimited (trust client) |
| 5 | Eng | Return 422 (not 200) for infeasible/unbounded | Mechanical | P1 | 4xx signals problem to client; 200 with status field requires client to check body — easy to miss | 200 with status in body |
| 6 | Eng | `null` → `None` bounds mapping explicit | Mechanical | P5 | JSON null → Python None conversion must happen before `float()` coercion; order matters | Trust json.loads directly |
| 7 | DX | Shadow prices in response | Mechanical | P1 | Sensitivity info is standard LP output; skipping it forces a second solve or manual dual calc | Omit for simplicity |
| 8 | DX | LP dashboard page (Deliverable 3) | Mechanical | P2 | Matches pattern of ERP dashboard; makes LP accessible to non-programmers without REST client | API-only |
| 9 | DX | Return variables_count + constraints_count in solve response | Mechanical | P1 | Client can verify parsing without re-parsing; 1 extra key, zero cost | Omit |

---

## GSTACK REVIEW REPORT

| Review | Runs | Last Run | Status | Required |
|--------|------|----------|--------|----------|
| CEO Review | 1 | 2026-07-09 | APPROVED — scipy available, no new deps, DoS limit added | no |
| Eng Review | 1 | 2026-07-09 | APPROVED — HiGHS dual values, 422 for infeasible, null→None guard | YES |
| Design Review | 0 | — | N/A — UI follows ERP dashboard pattern | no |
| Adversarial | 0 | — | — | no |
| Outside Voice | 0 | — | — | no |
