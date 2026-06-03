"""1S: ERP Free Edition — Russian desktop launcher."""
import os, sys
os.environ["1S_DEFAULT_LANG"] = "ru"
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from gui.desktop_app import main
if __name__ == "__main__":
    main()
