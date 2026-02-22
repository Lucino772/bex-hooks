from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML
from stdlibx import option, result
from stdlibx.compose import flow

from bex_hooks.exec.errors import BexExecError

if TYPE_CHECKING:
    from stdlibx.result.types import Result


def load_config(directory: Path | None, filename: Path | None):
    _directory = flow(
        option.maybe(lambda: directory),
        option.map_or_else(lambda: result.try_(Path.cwd), lambda val: result.ok(val)),
    )

    _file = flow(
        option.maybe(lambda: filename),
        option.map_or_else(
            lambda: flow(
                _directory,
                result.and_then(
                    result.safe(
                        lambda dir_: _get_next_candidate(dir_, {"bex.yaml", "bex.yml"})
                    )
                ),
                result.map_err(
                    lambda err: (
                        BexExecError("Could not find bex file")
                        if isinstance(err, StopIteration)
                        else err
                    )
                ),
            ),
            lambda val: result.ok(val),
        ),
    )

    return flow(
        result.collect(_directory, _file),
        result.and_then(lambda val: _parse_config(val[0], val[1])),
    )


def _get_next_candidate(directory: Path, candidates: set[str]) -> Path:
    return next(
        entry for candidate in candidates if (entry := directory / candidate).exists()
    )


def _parse_config(directory: Path, file: Path) -> Result[Environment, Exception]:
    return flow(
        result.try_(file.read_text),
        result.and_then(result.safe(YAML(typ="safe").load)),
        result.map_(
            lambda data: {
                **data,
                "_directory": directory,
                "_filename": file,
            }
        ),
        result.and_then(
            result.safe(partial(Environment.model_validate, from_attributes=False))
        ),
    )


class Environment(BaseModel):
    class Config(BaseModel):
        model_config = ConfigDict(extra="allow")
        plugins: list[str] = Field(default_factory=list)

    class Hook(BaseModel):
        model_config = ConfigDict(extra="allow")
        __pydantic_extra__: dict[str, Any] = Field(init=False)  # type: ignore

        id: str
        if_: str | None = Field(default=None, alias="if")

    directory: Path = Field(alias="_directory")
    filename: Path = Field(alias="_filename")

    config: Config
    hooks: list[Hook] = Field(default_factory=list)
