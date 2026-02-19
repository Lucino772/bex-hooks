from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, NewType, Self

from rich.logging import RichHandler
from rich.progress import Progress as RichProgress
from rich.progress import TaskID

if TYPE_CHECKING:
    from types import TracebackType

    from rich.console import Console
    from rich.status import Status

ProgressToken = NewType("ProgressToken", TaskID)


class RichUI:
    __slots__ = ("__console",)

    def __init__(self, console: Console, *, log_level: int = logging.WARNING):
        self.__console = console

        # Configure logging
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        handler = RichHandler(
            console=console, show_path=False, omit_repeated_times=False
        )
        root_logger.addHandler(handler)

    def scope(self, status: str) -> _Scope:
        return _Scope(self.__console.status(status))

    def log(self, *objects: Any, end: str = "\n") -> None:
        self.__console.log(*objects, end=end)

    def print(self, *objects: Any, end: str = "\n") -> None:
        self.__console.print(*objects, end=end)

    def progress(self) -> _Progress:
        return _Progress(RichProgress(console=self.__console))


class _Scope:
    __slots__ = ("__status",)

    def __init__(self, status: Status) -> None:
        self.__status = status

    def update(self, status: str | None) -> None:
        self.__status.update(status)

    def __enter__(self) -> Self:
        self.__status.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.__status.__exit__(exc_type, exc_val, exc_tb)


class _Progress:
    def __init__(self, progress: RichProgress) -> None:
        self.__progress = progress

    def add_task(self, description: str, /, *, total: float | None = None) -> Any:
        return ProgressToken(self.__progress.add_task(description, total=total))

    def update(
        self,
        token: ProgressToken,
        /,
        *,
        description: str | None = None,
        total: float | None = None,
        completed: float | None = None,
        advance: float | None = None,
    ) -> None:
        self.__progress.update(
            token,
            description=description,
            total=total,
            completed=completed,
            advance=advance,
        )

    def advance(self, token: ProgressToken, advance: float) -> None:
        self.__progress.advance(token, advance)

    def __enter__(self) -> Self:
        self.__progress.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return self.__progress.__exit__(exc_type, exc_val, exc_tb)
