from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML
from stdlibx.compose import flow
from stdlibx.option import fn as option
from stdlibx.option import optional_of
from stdlibx.result import Ok, Result, as_result, result_of
from stdlibx.result import fn as result

from bex_hooks.exec.errors import BexExecError


def load_config(directory: Path | None, filename: Path | None):
    _directory = flow(
        optional_of(lambda: directory),
        option.map_or_else(lambda: result_of(Path.cwd), lambda val: Ok(val)),
    )

    _file = flow(
        optional_of(lambda: filename),
        option.map_or_else(
            lambda: flow(
                _directory,
                result.and_then(
                    as_result(
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
            lambda val: Ok(val),
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
        result_of(file.read_text),
        result.and_then(as_result(YAML(typ="safe").load)),
        result.map_(
            lambda data: {
                **data,
                "_directory": directory,
                "_filename": file,
            }
        ),
        result.and_then(
            as_result(partial(Environment.model_validate, from_attributes=False))
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
