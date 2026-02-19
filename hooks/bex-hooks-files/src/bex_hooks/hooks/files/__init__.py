from __future__ import annotations

from typing import TYPE_CHECKING

from bex_hooks.hooks.files.file import archive, download, inline

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bex_hooks.hooks.files._interface import HookFunc


def get_hooks() -> Mapping[str, HookFunc]:
    return {
        "files/archive": archive,
        "files/download": download,
        "files/inline": inline,
    }
