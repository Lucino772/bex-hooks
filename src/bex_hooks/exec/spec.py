from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field
from stdlibx.cancel import CancellationToken, with_cancel

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import TracebackType


class BexExecError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__()
        self.msg = msg


class BexPluginError(BexExecError): ...


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


class HookFunc(Protocol):
    def __call__(self, ctx: Context, args: Mapping[str, Any], *, ui: UI) -> None: ...


class Environment(BaseModel):
    class Config(BaseModel):
        model_config = ConfigDict(extra="allow")
        plugins: list[str] = Field(default_factory=list)

    class Hook(BaseModel):
        model_config = ConfigDict(extra="allow")
        __pydantic_extra__: dict[str, Any] = Field(init=False)  # type: ignore

        id: str
        if_: str | None = Field(default=None, alias="if")

    config: Config
    hooks: list[Hook] = Field(default_factory=list)


@dataclass(frozen=True)
class PluginInfo:
    name: str
    hooks: Mapping[str, HookFunc]


class Context(BaseModel):
    working_dir: str
    metadata: dict[str, Any]
    environ: dict[str, str]

    def __init__(self, token: CancellationToken, **kwargs) -> None:
        super().__init__(**kwargs)
        self.__token, self.__cancel = with_cancel(token)

    def register(self, fn: Callable[[Exception], None]) -> None:
        return self.__token.register(fn)

    def is_cancelled(self) -> bool:
        return self.__token.is_cancelled()

    def get_error(self) -> Exception | None:
        return self.__token.get_error()

    def raise_if_cancelled(self):
        self.__token.raise_if_cancelled()

    def wait(self, timeout: float | None) -> Exception | None:
        return self.__token.wait(timeout)

    def cancel(self) -> None:
        return self.__cancel()
