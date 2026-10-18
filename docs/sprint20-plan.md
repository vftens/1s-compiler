# Sprint 20 — Packaging for every platform, built by CI

## Theme

Sprint 19 replaced four root specs with `packaging/windows.spec`. This sprint makes
`packaging/` the single home of all PyInstaller specs, builds them on real Windows,
macOS and Linux machines in GitHub Actions, and closes a security hole that every
shipped build had.

## Goals

### G1 — `packaging/linux.spec`: the `1s` command for servers
`dist/1s/1s` — migrate audit, run, compile, serve — with no Python installed.
Entry `packaging/entry_cli.py` (src/cli.py uses relative imports). Every `src` module
is a hidden import (the CLI imports server/migrate lazily). **Folder mode (onedir)**:
config/ and data/ live next to the app and survive restarts; a one-file build unpacks
into a temp folder that is wiped on exit.

Checked in the sandbox with an empty environment (`env -i`, no Python on PATH):
`about`, `migrate audit examples` (91 procedures, 94% portable), `run hello_uk.1s`,
`run accounting_uk.1s`, `serve` (ping 200, login page 200). 29 MB.

### G2 — `packaging/macos.spec`: `1S-ERP.app`
Same desktop launcher as Windows (`gui/desktop_app.py`, pywebview → WebKit, browser
fallback), `BUNDLE` with bundle id `io.github.vftens.1s-erp`, icon converted from PNG by
Pillow. Not signed or notarised (first launch: right click → Open). Built in CI only.

### G3 — Security: no shared Flask secret key
`config/secret.key` was committed and bundled into every Windows build (`datas` had
`config/`). It signs the Flask session, and the session carries the user role, so with
the public key anyone could forge an admin session on any 1S install.
- No spec ships `config/` any more; each install creates its own key on first run
  (`src/server._secret_key` already did, once the file is absent).
- `config/secret.key` is no longer tracked (it was in `.gitignore` but committed earlier).
- **Action for running instances (hosted demo, SaaS):** delete `config/secret.key` and
  restart, so a fresh key is generated; existing sessions are logged out. The old key
  stays in git history, so treat it as public.

### G4 — GitHub Actions
- `build.yml`: Windows ×4 editions (base/ru/uk/en), Linux CLI (ubuntu-22.04 for an older
  glibc, smoke test without Python), macOS app (bundle check, `ditto` zip). Artifacts on
  every run; a **GitHub Release with all files on a `v*` tag**. Runs on tags, manual
  dispatch, and pushes/PRs that touch packaging, gui, installer or the workflow.
- `ci.yml`: tests now run on **every branch** (they only ran on main/develop, so the work
  branch was never tested); installs glpk-utils, reportlab, pyyaml, openpyxl. The old
  `release` job never ran (no tag trigger, wrong zip pattern) and moved to build.yml.
- Both workflows pass `actionlint`.

### G5 — A green test suite on Linux
`test_corrupt_db_raises` used `SELECT 1`, which never reads the file; newer SQLite opens
lazily, so it passed on a corrupt file. It now reads `sqlite_master`. With reportlab
installed: **756 passed, 0 failed**.

## Release

```
git tag v1.3.0 && git push origin v1.3.0
```
→ Actions builds 1S-ERP(.exe, -RU, -UK, -EN), 1s-linux-x86_64.tar.gz, 1S-ERP-macos.zip
and attaches them to the v1.3.0 release.

## Next (Sprint 21)

1. Windows/macOS desktop builds keep users and erp.db inside the app bundle (one-file exe
   unpacks to a temp folder): move user data to `%APPDATA%\1S-ERP` / `~/Library/Application
   Support/1S-ERP` for frozen builds.
2. Code signing (Windows Authenticode, Apple notarisation) before selling desktop builds.
3. Back to variant A: audit on 3 real BAS configurations, ОСВ reconciliation, Odoo import files.
