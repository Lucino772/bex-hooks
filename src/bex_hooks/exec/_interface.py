from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, NoReturn, Protocol, Self, TypeGuard

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from types import TracebackType


# --- Helpers ---
@dataclass(frozen=True)
class Context:
    working_dir: str
    metadata: Mapping[str, Any]
    environ: Mapping[str, str]


def is_token_cancelled(
    token: CancellationToken,
) -> TypeGuard[CancelledCancellationToken]:
    return token.is_cancelled()


# --- Typing ---
class HookFunc(Protocol):
    def __call__(
        self,
        token: CancellationToken,
        args: Mapping[str, Any],
        ctx: ContextLike,
        *,
        ui: UI,
    ) -> ContextLike: ...


class ContextLike(Protocol):
    @property
    def working_dir(self) -> str: ...
    @property
    def metadata(self) -> Mapping[str, Any]: ...
    @property
    def environ(self) -> Mapping[str, str]: ...


class CancellationToken(Protocol):
    def register(self, fn: Callable[[Exception], None]) -> None: ...
    def is_cancelled(self) -> bool: ...
    def get_error(self) -> Exception | None: ...
    def raise_if_cancelled(self): ...
    def wait(self, timeout: float | None) -> Exception | None: ...


class CancelledCancellationToken(CancellationToken, Protocol):
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
