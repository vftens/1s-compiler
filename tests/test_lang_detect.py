"""Quick test for OS language detection logic."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.server import _detect_lang, _os_lang

CASES = [
    ("uk-UA,uk;q=0.9,en;q=0.8",  "uk"),
    ("uk",                         "uk"),
    ("uk_UA",                      "uk"),
    ("ru-RU,ru;q=0.9",            "ru"),
    ("ru",                         "ru"),
    ("be",                         "uk"),   # Belarusian → uk
    ("kk-KZ",                      "ru"),   # Kazakh → ru
    ("en-US,en;q=0.9",            "en"),
    ("de-DE,de;q=0.9,en;q=0.8",  "en"),
    ("fr-FR",                      "en"),
    ("zh-CN",                      "en"),
    ("",                           "ru"),   # empty → default
]

def test_detect_lang():
    for accept, expected in CASES:
        result = _detect_lang(accept)
        assert result == expected, f"_detect_lang({accept!r}) = {result!r}, expected {expected!r}"

def test_os_lang_returns_valid():
    result = _os_lang()
    assert result in ("ru", "uk", "en"), f"_os_lang() returned invalid: {result!r}"

if __name__ == "__main__":
    for accept, expected in CASES:
        got = _detect_lang(accept)
        mark = "OK  " if got == expected else "FAIL"
        print(f"{mark} | {accept[:35]:<35} -> {got}  (exp {expected})")
    print()
    print("OS locale:", _os_lang())
    print()
    errors = [(a, _detect_lang(a), e) for a, e in CASES if _detect_lang(a) != e]
    if errors:
        for a, g, e in errors:
            print(f"FAIL: {a!r} got {g!r} expected {e!r}")
    else:
        print("ALL PASSED")
