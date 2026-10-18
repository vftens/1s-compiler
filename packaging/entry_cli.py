"""Entry point for the frozen `1s` command-line build (packaging/linux.spec).

src/cli.py uses package-relative imports, so it cannot be the script itself.
"""
from src.cli import main

if __name__ == "__main__":
    main()
