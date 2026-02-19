from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import shellingham
import typer
from rich.console import Console
from rich.traceback import Traceback
from stdlibx.cancel import CancellationTokenCancelledError, default_token, with_cancel
from stdlibx.compose import flow
from stdlibx.result import Error, Ok, as_result
from stdlibx.result import fn as result

from bex_hooks.exec.config import load_config
from bex_hooks.exec.executor import execute
from bex_hooks.exec.ui import CliUI

if TYPE_CHECKING:
    from bex_hooks.exec._interface import Context


class _FormatCommandError(Exception):
    def __init__(self, key: str, value: Context):
        super().__init__()
        self.key = key
        self.value = value


app = typer.Typer(add_completion=False, name="bex")


def main():
    app(prog_name="bex")


@app.callback()
def callback(
    ctx: typer.Context,
    file: Annotated[
        Path | None,
        typer.Option(
            "-f",
            "--file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            envvar="BEX_FILE",
        ),
    ] = None,
    directory: Annotated[
        Path | None,
        typer.Option(
            "-C",
            "--directory",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
            envvar="BEX_DIRECTORY",
        ),
    ] = None,
):
    ctx.ensure_object(dict)
    console = Console()

    match load_config(Path(os.getcwd()) if directory is None else directory, file):
        case Ok(env):
            ctx.obj["console"] = console
            ctx.obj["env"] = env
        case Error(err):
            console.print("Failed to execute environment", style="red")
            console.print(
                Traceback(Traceback.extract(type(err), err, err.__traceback__)),
                style="dim",
            )
            ctx.exit(1)


@app.command(context_settings={"allow_interspersed_args": False})
def run(ctx: typer.Context, command: list[str]):
    console: Console = ctx.obj["console"]

    token, cancel = with_cancel(default_token())
    signal.signal(signal.SIGTERM, lambda _, __: cancel())
    signal.signal(signal.SIGINT, lambda _, __: cancel())

    with console.status("Executing environment"):
        exec_result = execute(
            token,
            CliUI(console),
            {},
            dict(os.environ),
            ctx.obj["env"],
        )

    def _format_command(value: Context, cmd: list[str]):
        try:
            return [item.format_map(value.metadata) for item in cmd]
        except KeyError as err:
            raise _FormatCommandError(err.args[0], value) from None

    match flow(
        exec_result,
        result.map_(lambda val: (val,)),
        result.zipped(as_result(lambda value: _format_command(value, command))),
    ):
        case Ok((value, cmd)):
            console.print("Executed environment successfully", style="green")
            console.print(f"  Running command: {cmd}")
            ctx.exit(
                subprocess.call(
                    cmd,
                    shell=False,
                    env=value.environ,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
            )
        case Error(CancellationTokenCancelledError()):
            console.print("Process was cancelled", style="red")
            ctx.exit(3)
        case Error(_FormatCommandError() as err):
            console.print(
                f"Failed to prepare command, '{err.key}' is not in metadata",
                style="red",
            )
            console.print(json.dumps(err.value.metadata, indent=4), style="red")
            ctx.exit(4)
        case Error(err):
            console.print("Failed to execute environment", style="red")
            console.print(
                Traceback(Traceback.extract(type(err), err, err.__traceback__)),
                style="dim",
            )
            ctx.exit(2)


@app.command()
def shell(ctx: typer.Context):
    console: Console = ctx.obj["console"]

    token, cancel = with_cancel(default_token())
    signal.signal(signal.SIGTERM, lambda _, __: cancel())
    signal.signal(signal.SIGINT, lambda _, __: cancel())

    with console.status("Executing environment"):
        exec_result = execute(
            token,
            CliUI(console),
            {},
            dict(os.environ),
            ctx.obj["env"],
        )

    match exec_result:
        case Ok(value):
            console.print("Executed environment successfully", style="green")
            shell, path = shellingham.detect_shell()
            args = []
            if shell in ("powershell", "pwsh"):
                args += ["-NoLogo"]

            ctx.exit(
                subprocess.call(
                    [path, *args],
                    shell=False,
                    env=value.environ,
                )
            )
        case Error(CancellationTokenCancelledError()):
            console.print("Process was cancelled", style="red")
            ctx.exit(3)
        case Error(err):
            console.print("Failed to execute environment", style="red")
            console.print(
                Traceback(Traceback.extract(type(err), err, err.__traceback__)),
                style="dim",
            )
            ctx.exit(2)


@app.command()
def export(ctx: typer.Context):
    console: Console = ctx.obj["console"]

    token, cancel = with_cancel(default_token())
    signal.signal(signal.SIGTERM, lambda _, __: cancel())
    signal.signal(signal.SIGINT, lambda _, __: cancel())

    with console.status("Executing environment"):
        exec_result = execute(
            token,
            CliUI(console),
            {},
            dict(os.environ),
            ctx.obj["env"],
        )

    match exec_result:
        case Ok(value):
            console.print("Executed environment successfully", style="green")
            console.print(
                json.dumps(
                    {
                        "working_dir": value.working_dir,
                        "metadata": value.metadata,
                        "environ": value.environ,
                    },
                    indent=4,
                )
            )
        case Error(CancellationTokenCancelledError()):
            console.print("Process was cancelled", style="red")
            ctx.exit(3)
        case Error(err):
            console.print("Failed to execute environment", style="red")
            console.print(
                Traceback(Traceback.extract(type(err), err, err.__traceback__)),
                style="dim",
            )
            ctx.exit(2)
