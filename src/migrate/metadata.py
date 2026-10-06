"""Read 1C/BAS metadata from a configuration dumped to files (Sprint 19).

Designer -> "Выгрузить конфигурацию в файлы" writes one XML per object:
    Catalogs/Номенклатура.xml, Documents/РеализацияТоваровУслуг.xml, ...
Each holds <MetaDataObject><Catalog|Document|...><Properties>...</Properties>
<ChildObjects> with Attribute / TabularSection / Dimension / Resource.

Parsing is namespace-agnostic (only local tag names are used), so dumps from
different platform versions read the same way. Unknown or broken files are
reported, never fatal.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from .audit import METADATA_DIRS

_SCALAR_TYPES = {
    "xs:string": "string", "xs:decimal": "number", "xs:dateTime": "date",
    "xs:boolean": "boolean", "xs:base64Binary": "binary",
    "v8:ValueStorage": "storage", "v8:UUID": "uuid",
}


@dataclass
class Field:
    name: str
    type: str  # "string", "number", "date", "ref:Catalog.Контрагенты", "a|b" for composite


@dataclass
class ObjectMeta:
    kind: str                     # catalog, document, accumulation_register, ...
    name: str
    synonym: str = ""
    attributes: list[Field] = field(default_factory=list)
    tabular_sections: dict[str, list[Field]] = field(default_factory=dict)
    dimensions: list[Field] = field(default_factory=list)
    resources: list[Field] = field(default_factory=list)
    path: str = ""
    error: str | None = None

    @property
    def references(self) -> list[str]:
        """Other objects this one points to (ref:Catalog.X), for migration order."""
        refs: set[str] = set()
        every = self.attributes + self.dimensions + self.resources
        for rows in self.tabular_sections.values():
            every = every + rows
        for f in every:
            for t in f.type.split("|"):
                if t.startswith("ref:"):
                    refs.add(t[4:])
        return sorted(refs)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(el: ET.Element, name: str) -> ET.Element | None:
    return next((c for c in el if _local(c.tag) == name), None)


def _children(el: ET.Element | None, name: str) -> list[ET.Element]:
    return [] if el is None else [c for c in el if _local(c.tag) == name]


def _text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


def _norm_type(raw: str) -> str:
    raw = raw.strip()
    if raw in _SCALAR_TYPES:
        return _SCALAR_TYPES[raw]
    if ":" in raw:
        raw = raw.split(":", 1)[1]           # cfg:CatalogRef.X -> CatalogRef.X
    head, _, name = raw.partition(".")
    if head.endswith("Ref") and name:
        return f"ref:{head[:-3]}.{name}"      # CatalogRef.X -> ref:Catalog.X
    return raw or "unknown"


def _field(el: ET.Element) -> Field:
    props = _child(el, "Properties")
    name = _text(_child(props, "Name")) if props is not None else ""
    type_el = _child(props, "Type") if props is not None else None
    types = [_norm_type(_text(t)) for t in _children(type_el, "Type") if _text(t)]
    return Field(name=name, type="|".join(types) or "unknown")


def _synonym(props: ET.Element | None) -> str:
    syn = _child(props, "Synonym") if props is not None else None
    if syn is None:
        return ""
    for item in syn:
        content = _child(item, "content")
        if content is not None and _text(content):
            return _text(content)
    return ""


def read_object(path: Path, kind: str) -> ObjectMeta:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        return ObjectMeta(kind=kind, name=path.stem, path=str(path), error=f"{type(exc).__name__}: {exc}")
    obj = root if _child(root, "Properties") is not None else next(iter(root), None)
    if obj is None:
        return ObjectMeta(kind=kind, name=path.stem, path=str(path), error="empty MetaDataObject")
    props = _child(obj, "Properties")
    meta = ObjectMeta(kind=kind, name=_text(_child(props, "Name")) or path.stem,
                      synonym=_synonym(props), path=str(path))
    kids = _child(obj, "ChildObjects")
    meta.attributes = [_field(a) for a in _children(kids, "Attribute")]
    meta.dimensions = [_field(a) for a in _children(kids, "Dimension")]
    meta.resources = [_field(a) for a in _children(kids, "Resource")]
    for ts in _children(kids, "TabularSection"):
        ts_props = _child(ts, "Properties")
        ts_name = _text(_child(ts_props, "Name")) if ts_props is not None else "?"
        meta.tabular_sections[ts_name] = [_field(a) for a in _children(_child(ts, "ChildObjects"), "Attribute")]
    return meta


def read_metadata(root: Path | str) -> list[ObjectMeta]:
    """All object XMLs directly under the metadata folders of a dump."""
    root = Path(root)
    out: list[ObjectMeta] = []
    for folder, kind in METADATA_DIRS.items():
        d = root / folder
        if d.is_dir():
            out += [read_object(p, kind) for p in sorted(d.glob("*.xml"))]
    return out
