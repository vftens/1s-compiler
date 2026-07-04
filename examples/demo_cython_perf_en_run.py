"""Auto-generated runner for compiled 1S module: demo_cython_perf_en"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # project root

try:
    import demo_cython_perf_en
except ImportError as e:
    print(f"ERROR: Could not import compiled module: {e}")
    print("Did you run:  python setup_1s.py build_ext --inplace ?")
    sys.exit(1)
