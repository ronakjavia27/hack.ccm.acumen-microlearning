"""Content module registry for the hack.CCM Console.

Each content type (summaries / pearls / theory / future: antibiotics) is a
self-contained module with this shape:
    - list_items(filters)  -> list[dict]      used by GET /<kind>
    - get_item(id)         -> dict            used by GET /<kind>/{id}
    - update_item(id, fields) -> dict         used by PUT /<kind>/{id}
    - extra_endpoints                         optional extra endpoints

The dashboard FastAPI sub-app walks this registry to mount every module's
endpoints automatically, so adding a new content type is "drop in module +
call register()" — no changes to app.py / dashboard.html needed (the UI
reads `/api/modules` for the sidebar spec).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


class ItemNotFound(Exception):
    pass


@dataclass
class ModuleSpec:
    name: str                                    # display name (Title Case)
    kind: str                                    # short id used in URLs (summaries, pearls, theory)
    id_field: str                                # which field is the primary id (serial_number / id)
    list_fn: Callable[[Optional[Dict[str, str]]], List[Dict[str, Any]]]
    get_fn: Callable[[str], Dict[str, Any]]
    update_fn: Callable[[str, Dict[str, Any]], Dict[str, Any]]
    delete_fn: Callable[[str], Dict[str, Any]] = lambda id: {"deleted": False}
    bulk_delete_fn: Callable[[List[str]], Dict[str, Any]] = lambda ids: {"deleted": 0}
    bulk_status_fn: Callable[[List[str], str], None] = lambda ids, st: None
    list_columns: List[Dict[str, Any]] = field(default_factory=list)
    drawer_fields: List[Dict[str, Any]] = field(default_factory=list)
    has_visibility_flag: bool = True
    visible_value_field: str = ""               # if has_visibility_flag is True and this is set,
                                                # the field holding Yes/No (eg summaries).
    extra_endpoints: Dict[str, Tuple[str, str, Callable]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "id_field": self.id_field,
            "list_columns": self.list_columns,
            "drawer_fields": self.drawer_fields,
            "has_visibility_flag": self.has_visibility_flag,
            "visible_value_field": self.visible_value_field,
            "extra_endpoints": list(self.extra_endpoints.keys()),
        }


_REGISTRY: Dict[str, ModuleSpec] = {}


def register(spec: ModuleSpec) -> None:
    _REGISTRY[spec.kind] = spec


def all_kinds() -> List[ModuleSpec]:
    return list(_REGISTRY.values())


def get_spec(kind: str) -> ModuleSpec:
    if kind not in _REGISTRY:
        raise ItemNotFound(f"unknown module kind: {kind}")
    return _REGISTRY[kind]


def list_specs() -> List[Dict[str, Any]]:
    return [s.to_dict() for s in _REGISTRY.values()]


def bootstrap() -> None:
    """Idempotent — safe to call on every reload."""
    from .summaries import SPEC as summaries_spec
    from .pearls import SPEC as pearls_spec
    from .theory import SPEC as theory_spec
    register(summaries_spec)
    register(pearls_spec)
    register(theory_spec)
