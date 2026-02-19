from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    NoReturn,
    Protocol,
    Self,
    TypeGuard,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType


class Context(Protocol):
    working_dir: str
    metadata: dict[str, Any]
    environ: dict[str, str]

    def register(self, fn: Callable[[Exception], None]) -> None: ...
    def is_cancelled(self) -> bool: ...
    def get_error(self) -> Exception | None: ...
    def raise_if_cancelled(self): ...
    def wait(self, timeout: float | None) -> Exception | None: ...


class CancelledContext(Context, Protocol):
    def is_cancelled(self) -> Literal[True]: ...
    def get_error(self) -> Exception: ...
    def raise_if_cancelled(self) -> NoReturn: ...
    def wait(self, timeout: float | None) -> Exception: ...


class UI(Protocol):
    def scope(self, status: str) -> UIScope: ...
    def progress(self) -> UIProgress: ...
    def log(self, *objects: Any, end: str = "\n") -> None: ...
    def print(self, *objects: Any, end: str = "\n") -> None: ...


class UIScope(Protocol):
    def update(self, status: str | None) -> None: ...
    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...


class UIProgress(Protocol):
    def add_task(self, description: str, /, *, total: float | None = None) -> Any: ...

    def update(
        self,
        token: Any,
        /,
        *,
        description: str | None = None,
        total: float | None = None,
        completed: float | None = None,
        advance: float | None = None,
    ) -> None: ...

    def advance(self, token: Any, advance: float) -> None: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...


def is_context_cancelled(ctx: Context) -> TypeGuard[CancelledContext]:
    return ctx.is_cancelled()
