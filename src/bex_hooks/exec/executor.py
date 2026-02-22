from __future__ import annotations

import functools
import logging
import platform
import time
from typing import TYPE_CHECKING, Any

import cel
from stdlibx import option, result
from stdlibx.cancel import is_token_cancelled
from stdlibx.compose import flow
from stdlibx.option.types import Nothing, Some
from stdlibx.result.types import Error, Ok, Result

from bex_hooks.exec._interface import Context
from bex_hooks.exec.plugin import plugin_from_entrypoint

if TYPE_CHECKING:
    from collections.abc import Mapping, MutableMapping

    from stdlibx.cancel import CancellationToken

    from bex_hooks.exec._interface import UI, ContextLike, HookFunc
    from bex_hooks.exec.config import Environment


def execute(
    token: CancellationToken,
    ui: UI,
    metadata: MutableMapping[str, Any],
    environ: MutableMapping[str, str],
    env: Environment,
) -> Result[ContextLike, Exception]:
    logger = logging.getLogger("bex_hooks.executor")

    match result.collect_all(
        flow(
            plugin_from_entrypoint(_plugin),
            result.inspect(lambda _: logger.info("Imported plugin '%s'", _plugin)),
            result.inspect_err(
                lambda _: logger.error("Failed to import plugin '%s'", _plugin)
            ),
        )
        for _plugin in env.config.plugins
    ):
        case Ok(value):
            plugins = list(value)
        case Error(_) as err:
            return result.error(err.error)

    hooks: MutableMapping[str, HookFunc] = {}
    for plugin in plugins:
        hooks.update(plugin.hooks)
        logger.info("Loaded hooks from plugin '%s'", plugin.name)

    cel_ctx = cel.Context()
    return functools.reduce(
        lambda prev, hook: flow(
            prev,
            result.and_then(
                lambda ctx_: _execute_hook(token, ui, hooks, hook, ctx_, cel_ctx)
            ),
        ),
        env.hooks,
        result.ok(
            Context(
                working_dir=str(env.directory),
                metadata={
                    **metadata,
                    "platform": platform.system().lower(),
                    "arch": platform.machine().lower(),
                },
                environ=environ,
            )
        ),
    )


def _execute_hook(
    token: CancellationToken,
    ui: UI,
    hooks: Mapping[str, HookFunc],
    hook: Environment.Hook,
    ctx: ContextLike,
    cel_ctx: cel.Context,
) -> Result[ContextLike, Exception]:
    match flow(
        result.try_(lambda: cel_ctx.update({**ctx.metadata, "env": ctx.environ})),
        result.and_then(
            result.safe(
                lambda _: (
                    hook.if_ is not None
                    and bool(cel.evaluate(hook.if_, cel_ctx)) is False
                )
            )
        ),
    ):
        case Ok(skip_hook) if skip_hook is True:
            ui.print(f"Hook skipped: '{hook.id}'")
            return result.ok(ctx)
        case Error(_) as err:
            return result.error(err.error)

    if is_token_cancelled(token):
        return result.error(token.get_error())

    match option.maybe(hooks.get, hook.id):
        case Some(func):
            hook_func = func
        case Nothing():
            return result.error(Exception(f"Hook '{hook.id}' does not exists"))

    ui.print(f"Running hook '{hook.id}'")
    start_time = time.perf_counter()
    try:
        hook_result = hook_func(token, hook.__pydantic_extra__, ctx, ui=ui)
    except Exception as e:
        duration = time.perf_counter() - start_time
        ui.print(
            f"Hook failed to run: '{hook.id}' ({duration:.2f}s)",  # style="red"
        )
        return result.error(e)
    else:
        duration = time.perf_counter() - start_time
        ui.print(f"Hook ran successfully: '{hook.id}' ({duration:.2f}s)")
        return result.ok(hook_result)
