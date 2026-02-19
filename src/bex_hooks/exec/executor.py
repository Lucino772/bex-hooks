from __future__ import annotations

import platform
import time
from typing import TYPE_CHECKING

import cel
from stdlibx.cancel import is_token_cancelled
from stdlibx.compose import flow
from stdlibx.option import Nothing, Some, optional_of
from stdlibx.result import Error, Ok, Result, as_result, result_of
from stdlibx.result import fn as result

from bex_hooks.exec.plugin import load_plugins
from bex_hooks.exec.ui import RichUI

if TYPE_CHECKING:
    from collections.abc import Mapping, MutableMapping

    from rich.console import Console

    from bex_hooks.exec.spec import UI, Context, Environment, HookFunc


def execute(
    console: Console, ctx: Context, env: Environment
) -> Result[Context, Exception]:
    ui = RichUI(console)

    match load_plugins(console, env.config.plugins):
        case Ok(value):
            plugins = list(value)
        case Error(_) as err:
            return Error(err.error)

    hooks: MutableMapping[str, HookFunc] = {}
    for plugin in plugins:
        hooks.update(plugin.hooks)
        console.print(f"[+] Loaded hooks from plugin '{plugin.name}'")

    ctx.metadata["platform"] = platform.system().lower()
    ctx.metadata["arch"] = platform.machine().lower()

    cel_ctx = cel.Context()

    return flow(
        result.collect_all(
            _execute_hook(console, hooks, hook, ctx, cel_ctx, ui) for hook in env.hooks
        ),
        result.map_(lambda _: ctx),
    )


def _execute_hook(
    console: Console,
    hooks: Mapping[str, HookFunc],
    hook: Environment.Hook,
    ctx: Context,
    cel_ctx: cel.Context,
    ui: UI,
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
            console.print(f"[-] Hook skipped: '{hook.id}'")
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

    console.print(f"[+] Running hook '{hook.id}'")
    start_time = time.perf_counter()
    try:
        hook_func(ctx, hook.__pydantic_extra__, ui=ui)
    except Exception as e:
        duration = time.perf_counter() - start_time
        console.print(
            f"[!] Hook failed to run: '{hook.id}' ({duration:.2f}s)", style="red"
        )
        return Error(e)
    else:
        duration = time.perf_counter() - start_time
        console.print(f"[+] Hook ran successfully: '{hook.id}' ({duration:.2f}s)")

    return Ok(None)
