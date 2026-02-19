from __future__ import annotations

import platform
import time
from typing import TYPE_CHECKING, Any, Callable

import cel
from pydantic import BaseModel
from stdlibx.cancel import is_token_cancelled, with_cancel
from stdlibx.compose import flow
from stdlibx.option import Nothing, Some, optional_of
from stdlibx.result import Error, Ok, Result, as_result, is_err, result_of
from stdlibx.result import fn as result

from bex_hooks.exec.plugin import plugin_from_entrypoint

if TYPE_CHECKING:
    from collections.abc import Mapping, MutableMapping

    from stdlibx.cancel import CancellationToken

    from bex_hooks.exec._interface import UI, HookFunc
    from bex_hooks.exec.config import Environment


def execute(
    token: CancellationToken,
    ui: UI,
    metadata: MutableMapping[str, Any],
    environ: MutableMapping[str, str],
    env: Environment,
) -> Result[ExecContext, Exception]:
    ctx = ExecContext(
        token, working_dir=str(env.directory), metadata=metadata, environ=environ
    )

    match result.collect_all(
        flow(
            plugin_from_entrypoint(_plugin),
            result.inspect(lambda _: ui.print(f"[+] Imported plugin '{_plugin}'")),
            result.inspect_err(
                lambda _: ui.print(f"[+] Failed to import plugin '{_plugin}'")
            ),
        )
        for _plugin in env.config.plugins
    ):
        case Ok(value):
            plugins = list(value)
        case Error(_) as err:
            return Error(err.error)

    hooks: MutableMapping[str, HookFunc] = {}
    for plugin in plugins:
        hooks.update(plugin.hooks)
        ui.print(f"[+] Loaded hooks from plugin '{plugin.name}'")

    ctx.metadata["platform"] = platform.system().lower()
    ctx.metadata["arch"] = platform.machine().lower()

    cel_ctx = cel.Context()
    for hook in env.hooks:
        if is_err(err := _execute_hook(ui, hooks, hook, ctx, cel_ctx)):
            return Error(err.error)

    return Ok(ctx)


def _execute_hook(
    ui: UI,
    hooks: Mapping[str, HookFunc],
    hook: Environment.Hook,
    ctx: ExecContext,
    cel_ctx: cel.Context,
) -> Result[None, Exception]:
    match flow(
        result_of(lambda: cel_ctx.update({**ctx.metadata, "env": ctx.environ})),
        result.and_then(
            as_result(
                lambda _: (
                    hook.if_ is not None
                    and bool(cel.evaluate(hook.if_, cel_ctx)) is False
                )
            )
        ),
    ):
        case Ok(skip_hook) if skip_hook is True:
            ui.print(f"[-] Hook skipped: '{hook.id}'")
            return Ok(None)
        case Error(_) as err:
            return Error(err.error)

    if is_token_cancelled(ctx):
        return Error(ctx.get_error())

    match optional_of(hooks.get, hook.id):
        case Some(func):
            hook_func = func
        case Nothing():
            return Error(Exception(f"Hook '{hook.id}' does not exists"))

    ui.print(f"[+] Running hook '{hook.id}'")
    start_time = time.perf_counter()
    try:
        hook_func(ctx, hook.__pydantic_extra__, ui=ui)
    except Exception as e:
        duration = time.perf_counter() - start_time
        ui.print(
            f"[!] Hook failed to run: '{hook.id}' ({duration:.2f}s)",  # style="red"
        )
        return Error(e)
    else:
        duration = time.perf_counter() - start_time
        ui.print(f"[+] Hook ran successfully: '{hook.id}' ({duration:.2f}s)")

    return Ok(None)


class ExecContext(BaseModel):
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
