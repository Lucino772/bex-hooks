from __future__ import annotations

import functools
import logging
import platform
import time
from typing import TYPE_CHECKING, Any

import cel
from stdlibx.cancel import is_token_cancelled
from stdlibx.compose import flow
from stdlibx.option import Nothing, Some, optional_of
from stdlibx.result import Error, Ok, Result, as_result, result_of
from stdlibx.result import fn as result

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
            return Error(err.error)

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
        Ok["ContextLike", Exception](
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
            ui.print(f"Hook skipped: '{hook.id}'")
            return Ok(ctx)
        case Error(_) as err:
            return Error(err.error)

    if is_token_cancelled(token):
        return Error(token.get_error())

    match optional_of(hooks.get, hook.id):
        case Some(func):
            hook_func = func
        case Nothing():
            return Error(Exception(f"Hook '{hook.id}' does not exists"))

    ui.print(f"Running hook '{hook.id}'")
    start_time = time.perf_counter()
    try:
        hook_result = hook_func(token, hook.__pydantic_extra__, ctx, ui=ui)
    except Exception as e:
        duration = time.perf_counter() - start_time
        ui.print(
            f"Hook failed to run: '{hook.id}' ({duration:.2f}s)",  # style="red"
        )
        return Error(e)
    else:
        duration = time.perf_counter() - start_time
        ui.print(f"Hook ran successfully: '{hook.id}' ({duration:.2f}s)")
        return Ok(hook_result)
