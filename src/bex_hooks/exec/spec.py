from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BexExecError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__()
        self.msg = msg


class BexPluginError(BexExecError): ...


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
