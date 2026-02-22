from __future__ import annotations

import functools
import importlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping

from stdlibx import option, result
from stdlibx.compose import flow, pipe

from bex_hooks.exec.errors import BexPluginError

if TYPE_CHECKING:
    from stdlibx.result.types import Result

    from bex_hooks.exec._interface import HookFunc

_ENTRYPOINT_PATTERN = re.compile(
    r"(?P<module>[\w.]+)\s*"
    r"(:\s*(?P<attr>[\w.]+)\s*)?"
    r"((?P<extras>\[.*\])\s*)?$"
)


@dataclass(frozen=True)
class PluginInfo:
    name: str
    hooks: Mapping[str, HookFunc]


def plugin_from_entrypoint(entrypoint: str):
    def _map_errors(error: Exception):
        match error:
            case ImportError():
                return BexPluginError(f"Failed to import plugin from '{entrypoint}'")
            case AttributeError():
                return BexPluginError(f"Failed to import plugin from '{entrypoint}'")
            case _:
                return error

    return flow(
        result.try_(_ENTRYPOINT_PATTERN.match, entrypoint),
        result.and_then(
            lambda match: (
                result.ok(match)
                if match is not None
                else result.error(
                    BexPluginError(f"Invalid plugin entrypoint format '{entrypoint}'")
                )
            )
        ),
        result.and_then(
            result.safe(
                lambda match_: functools.reduce(
                    getattr,
                    filter(None, (match_.group("attr") or "").split(".")),
                    importlib.import_module(match_.group("module")),
                )
            )
        ),
        result.and_then(
            lambda module: result.collect(
                result.ok(getattr(module, "__plugin_name__", module.__name__)),
                _load_hooks(module),
            )
        ),
        result.map_(lambda value: PluginInfo(value[0], value[1])),
        result.map_err(_map_errors),
    )


def _load_hooks(module: Any) -> Result[dict[str, HookFunc], Exception]:
    return flow(
        option.maybe(getattr, module, "get_hooks", None),
        option.map_or_else(
            lambda: result.ok({}),
            pipe(
                result.safe(lambda callback: callback()),
                result.map_(lambda value: value if isinstance(value, dict) else {}),
            ),
        ),
    )
