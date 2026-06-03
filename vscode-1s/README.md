# 1S: ERP Language Support for VS Code

Syntax highlighting, snippets and **▶ Run** button for `.1s` script files.

## Features

- 🎨 **Syntax highlighting** — keywords, builtins, strings, dates, comments
- 📝 **Snippets** — `fn`, `if`, `foreach`, `for`, `doc`, `wf`, `excel`, `cat`, `reg`…
- ▶ **Run button** — click in editor title bar or press **Ctrl+F5**
- 🌍 **Trilingual** — Russian / Ukrainian / English keywords all highlighted

## Install

### From .vsix (manual)

```bash
cd vscode-1s
npm install
npm run compile
npx vsce package          # → 1s-erp-language-0.3.0.vsix
code --install-extension 1s-erp-language-0.3.0.vsix
```

### Requirements

- VS Code 1.85+
- Python with 1s-erp installed: `pip install flask`
- Project root containing `src/cli.py`

## Usage

Open any `.1s` file — syntax highlighting activates automatically.

**Run a script**: Click the ▶ button in the editor title bar, or press `Ctrl+F5`.  
Output appears in the **1S: ERP** output panel.

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `1s-erp.pythonPath` | `python` | Python interpreter |
| `1s-erp.projectRoot` | auto | Root with `src/cli.py` |

## Snippets

| Prefix | Expands to |
|--------|-----------|
| `fn` | Function definition |
| `proc` | Procedure definition |
| `if` | If / Якщо / Если |
| `foreach` | For Each loop |
| `for` | Numeric For loop |
| `try` | Try/Except |
| `doc` | Document + TabularSection |
| `wf` | WorkflowDocument |
| `cat` | Catalog |
| `reg` | AccountingRegister |
| `excel` | Excel export |
