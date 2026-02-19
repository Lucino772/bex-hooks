from __future__ import annotations

from typing import TYPE_CHECKING

from bex_hooks.hooks.python.setup import setup_python

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bex_hooks.hooks.python._interface import HookFunc


def get_hooks() -> Mapping[str, HookFunc]:
    return {
        "python/setup-python": setup_python,
    }
