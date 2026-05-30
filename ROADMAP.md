# Roadmap

## ✅ Done (v0.3 — current)

- Trilingual lexer + recursive-descent parser
- Python + Cython transpiler backends
- Full 1C-compatible runtime: Array, Map, Structure, ValueTable, ValueList
- Double-entry accounting register (ПланРахунків, ОСВ, АналізРахунку)
- Accumulation + Information registers
- Work schedules (weekly / shift)
- Flask Web UI with SSE live output, user auth, admin panel
- 384 automated tests (lexer → parser → runtime → transpiler → integration)
- Ukrainian 🇺🇦 keyword set (full parity with Russian)
- Cython type inference + `cdef`/`cpdef` generation
- GPL v3 license
- GitHub: github.com/vftens/1s-compiler

---

## 🔜 v0.4 — First paying clients (Q3 2026)

- [ ] **SaaS deployment** — Docker + nginx, one-click deploy on VPS
- [ ] **`pip install 1s-erp`** — distribute runtime as a PyPI package
- [ ] **Landing page** — simple HTML page explaining the offer
- [ ] **Stripe/LiqPay payment** — online billing for SaaS tiers
- [ ] **Demo video** — 5-min screencast: install → run accounting_uk → web UI
- [ ] **Migration CLI** — `python -m src.cli migrate myfile.bsl` with compat report
- [ ] **`#Использовать` / `#Область`** preprocessor directives (needed for real 1C codebases)

---

## 🔮 v0.5 — Production-ready (Q4 2026)

- [ ] **SQLite-backed registers** — persist accounting data between runs
- [ ] **Query engine** — full `ВЫБРАТЬ / ОБЕРІТЬ` SQL dialect over registers
- [ ] **REST API** — POST /run, GET /balance, POST /post (for external integrations)
- [ ] **VS Code extension** — syntax highlighting + run button for `.1s` files
- [ ] **Excel import/export** — read `.xlsx` into ValueTable, export reports

---

## 🌍 v1.0 — Open ecosystem (2027)

- [ ] **Module registry** — community-published accounting rules, payroll formulas
- [ ] **1C infobase reader** — import data from real 1C `.dt` / `.cf` files
- [ ] **Multi-tenant SaaS** — isolated workspaces per company
- [ ] **Java/ANTLR runtime** — JVM-based alternative (grammar already written)
- [ ] **Mobile UI** — React Native or PWA for reports on phone

---

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) if it exists, or open an issue.  
Key areas that need help: query engine, VS Code extension, Excel I/O.
