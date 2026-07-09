"""
IndustryProfile — loads a YAML industry configuration file and provides
convenient access to sub-settings (warehouse, payroll, procurement, budget, etc.).
"""
from __future__ import annotations
import os
import warnings
from typing import Any, Dict, Optional


_BUILTIN_PROFILES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "profiles", "industry"
)


class IndustryProfile:
    """
    Load and query an industry YAML profile.

    Usage:
        profile = IndustryProfile.load("manufacturing")
        print(profile.name)              # "Manufacturing"
        print(profile.get("payroll", {}).get("overtime_multiplier"))  # 1.5
        tax_profile = profile.tax_profile_name  # "ru_2024"
    """

    def __init__(self, data: dict, source: str = ""):
        self._data   = data
        self._source = source

    @classmethod
    def load(cls, profile_name: str, profiles_dir: Optional[str] = None) -> "IndustryProfile":
        """
        Load by name (e.g. "manufacturing") from profiles/industry/<name>.yaml.
        Falls back to empty profile if not found.
        """
        search_dirs = []
        if profiles_dir:
            search_dirs.append(profiles_dir)
        # Search relative to CWD first, then relative to this module
        search_dirs.append(os.path.join(os.getcwd(), "profiles", "industry"))
        search_dirs.append(_BUILTIN_PROFILES_DIR)

        for d in search_dirs:
            path = os.path.join(d, f"{profile_name}.yaml")
            if os.path.isfile(path):
                return cls._load_file(path)

        warnings.warn(f"IndustryProfile: profile {profile_name!r} not found — using empty profile")
        return cls(data={"name": profile_name}, source="<empty>")

    @classmethod
    def _load_file(cls, path: str) -> "IndustryProfile":
        import yaml
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Industry profile must be a YAML mapping, got {type(data)}")
        return cls(data=data, source=path)

    # ── query ──────────────────────────────────────────────────────────────
    @property
    def name(self) -> str:
        return self._data.get("name", "Unknown")

    @property
    def workflow_path(self) -> str:
        return self._data.get("workflow", "profiles/workflow/default.yaml")

    @property
    def tax_profile_name(self) -> str:
        """Extract profile name from tax path, e.g. 'profiles/tax/ru_2024.yaml' → 'ru_2024'."""
        tax_path = self._data.get("tax", "")
        return os.path.basename(tax_path).replace(".yaml", "").replace(".yml", "")

    def get(self, section: str, default: Any = None) -> Any:
        return self._data.get(section, default)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __repr__(self) -> str:
        return f"IndustryProfile({self.name!r}, source={self._source!r})"

    # ── English method aliases ───────────────────────────────────────────────
    Load             = classmethod(load.__func__)  # type: ignore[attr-defined]
    Name             = property(lambda self: self.name)
    WorkflowPath     = property(lambda self: self.workflow_path)
    TaxProfileName   = property(lambda self: self.tax_profile_name)

    # ── Russian property aliases ─────────────────────────────────────────────
    @property
    def Наименование(self): return self.name
    @property
    def ПрофильНалога(self): return self.tax_profile_name
    @property
    def ПутьМаршрута(self): return self.workflow_path

    # ── Ukrainian property aliases ───────────────────────────────────────────
    @property
    def Назва(self): return self.name
    @property
    def ПрофільПодатку(self): return self.tax_profile_name


# ── Convenience loader function (for 1S scripts) ────────────────────────────
def load_profile(name: str) -> IndustryProfile:
    return IndustryProfile.load(name)

def ЗагрузитьПрофиль(name: str) -> IndustryProfile:
    return IndustryProfile.load(name)

def ЗавантажитиПрофіль(name: str) -> IndustryProfile:
    return IndustryProfile.load(name)


# ── Trilingual class aliases ─────────────────────────────────────────────────
ОтраслевойПрофиль = IndustryProfile
ГалузевийПрофіль  = IndustryProfile
