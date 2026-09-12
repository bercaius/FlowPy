"""Plugin discovery — entry_points + directory scan.

Patterns:
- CorvinOS: importlib.metadata.entry_points()
- angr-management: directory-based plugin loading
"""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .base import BasePlugin

if TYPE_CHECKING:
    from flowpy.app import FlowPyWindow

log = logging.getLogger(__name__)
FLOWPY_PLUGIN_GROUP = "flowpy.plugins"


def _iter_entry_points(group: str) -> list[importlib.metadata.EntryPoint]:
    try:
        return list(importlib.metadata.entry_points(group=group))
    except Exception:
        log.exception("failed to read entry_points group %r", group)
        return []


def _load_entry_point_class(ep: importlib.metadata.EntryPoint, group: str) -> type | None:
    try:
        return ep.load()
    except Exception:
        log.exception("failed to load entry_point %r in group %r", ep.name, group)
        return None


def load_from_entry_points(group: str = FLOWPY_PLUGIN_GROUP) -> list[type]:
    classes: list[type] = []
    for ep in _iter_entry_points(group):
        cls = _load_entry_point_class(ep, group)
        if cls is not None:
            classes.append(cls)
    return classes


def _load_module_from_file(module_name: str, filepath: str) -> "types.ModuleType | None":
    import types

    try:
        mod_basename = os.path.basename(filepath)
        if mod_basename == "__init__.py":
            modbasename = os.path.basename(os.path.dirname(filepath))
            if "." in modbasename:
                log.error("file %s cannot be loaded - weird name", filepath)
                return None
        else:
            modbasename = os.path.basename(os.path.dirname(filepath)) + "." + os.path.splitext(mod_basename)[0]
            if modbasename.count(".") != 1:
                log.error("package %s cannot be loaded - weird name", filepath)
                return None

        modname = f"flowpy.plugins.{modbasename}"
        spec = importlib.util.spec_from_file_location(modname, filepath, submodule_search_locations=[])
        if spec is None:
            log.error("Not a python module: %s", filepath)
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[modname] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod
    except Exception as e:
        log.error("Failed to load plugin from %s: %s", filepath, e)
        return None


def _load_plugins_from_module(module: "types.ModuleType") -> list[type]:
    out: list[type] = []
    for _, cls in vars(module).items():
        if (
            isinstance(cls, type)
            and issubclass(cls, BasePlugin)
            and cls is not BasePlugin
            and not hasattr(cls, f"_{cls.__name__}__i_hold_this_abstraction_token")
        ):
            out.append(cls)
    return out


def load_plugins_from_dir(path: str, exclude: tuple[str, ...] = ()) -> list[type]:
    out: list[type] = []
    try:
        dlist = os.listdir(path)
    except OSError:
        return []
    for filename in dlist:
        if filename in exclude or filename in ("__init__.py", "__pycache__"):
            continue
        fullname = os.path.join(path, filename)
        if os.path.isfile(fullname) and fullname.endswith(".py"):
            mod = _load_module_from_file(filename, fullname)
            if mod is not None:
                out.extend(_load_plugins_from_module(mod))
        elif os.path.isdir(fullname) and os.path.isfile(os.path.join(fullname, "__init__.py")):
            mod = _load_module_from_file(filename, os.path.join(fullname, "__init__.py"))
            if mod is not None:
                out.extend(_load_plugins_from_module(mod))
    return out


def discover_plugins(window: "FlowPyWindow | None" = None) -> dict[str, type]:
    """Discover all available plugins (builtin + entry_points)."""
    discovered: dict[str, type] = {}

    builtin_dir = Path(__file__).parent / "builtin"
    if builtin_dir.exists():
        for cls in load_plugins_from_dir(str(builtin_dir)):
            discovered[cls.__name__] = cls

    for cls in load_from_entry_points():
        discovered[cls.__name__] = cls

    return discovered
