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

## ✅ v0.4 — Sprint 7 complete (June 2026)

- [x] **SaaS deployment** — Docker + Nginx (`nginx/`), `deploy.sh` one-liner
- [x] **`pip install 1s-erp`** — `pyproject.toml` with extras: `[desktop,cython]`
- [x] **Landing page** — `landing/index.html` for www.1s-compiler.ru
- [ ] **Stripe/LiqPay payment** — online billing for SaaS tiers ← next
- [ ] **Demo video** — 5-min screencast
- [ ] **Migration CLI** — `python -m src.cli migrate myfile.bsl`

## ✅ v0.5 — Sprint 7 complete (June 2026)

- [x] **SQLite-backed registers** — `src/runtime/persistence.py`
- [ ] **Query engine** — full `ВЫБРАТЬ / ОБЕРІТЬ` SQL dialect ← next
- [x] **REST API** — `/api/v1/ping, /run, /eval, /scripts, /analytics-data`
- [x] **VS Code extension** — `vscode-1s/` grammar + snippets + Run button
- [x] **Excel export** — `src/runtime/excel.py` + openpyxl, CSV fallback

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
