from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from bex_hooks.hooks.files.utils import download_file

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bex_hooks.hooks.files._interface import UI, CancellationToken, ContextLike


def archive(
    token: CancellationToken, args: Mapping[str, Any], ctx: ContextLike, *, ui: UI
) -> ContextLike:
    class _Args(BaseModel):
        source: str
        source_hash: str
        target: str
        format_: str = Field(validation_alias="format")
        keep_source: bool = Field(default=True)

    data = _Args.model_validate(args, from_attributes=False)
    target = Path(
        Template(data.target).substitute(
            {
                "working_dir": ctx.working_dir,
                "metadata": ctx.metadata,
                "environ": ctx.environ,
            }
        )
    )
    enforce_toplevel = args.get("enforce_toplevel", False)

    hash_algo, hash_hex = data.source_hash.split(":")
    cached_file = (
        Path(ctx.working_dir) / ".bex" / "cache" / "files" / hash_algo / hash_hex
    )
    if cached_file.exists() and cached_file.is_file():
        ui.print("Using {}".format(cached_file))
        filename = cached_file
    else:
        with ui.progress() as pb:
            task_id = pb.add_task(
                "Downloading {}".format(target.relative_to(ctx.working_dir))
            )
            filename = download_file(
                token,
                data.source,
                report_hook=lambda completed, total: pb.update(
                    task_id, completed=completed, total=total if total > 0 else None
                ),
            )

    _path = Path(filename)
    if hash_hex != hashlib.new(hash_algo, _path.read_bytes()).hexdigest():
        msg = f"Hash mismatched when downloading {data.source}"
        raise ValueError(msg)

    # TODO: Don't extract if file has not changed
    try:
        with ui.progress() as pb:
            if data.format_ == "zip":
                with zipfile.ZipFile(filename) as archive:
                    has_single_toplevel = True
                    if not enforce_toplevel or (
                        len(
                            {
                                Path(name).parts[0]
                                for name in archive.namelist()
                                if not name.startswith("__MACOSX")
                            }
                        )
                        > 1
                    ):
                        has_single_toplevel = False

                    _members = archive.infolist()
                    task_id = pb.add_task("Extracting {}".format(target.relative_to(ctx.working_dir)), total=len(_members))
                    for member in _members:
                        token.raise_if_cancelled()

                        member_path = Path(member.filename)
                        relative_path = (
                            Path(*member_path.parts[1:])
                            if has_single_toplevel
                            else member_path
                        )
                        target_path = (Path(target) / relative_path).resolve()
                        target_path.parent.mkdir(parents=True, exist_ok=True)

                        if member.is_dir():
                            target_path.mkdir(parents=True, exist_ok=True)
                        else:
                            with (
                                archive.open(member) as source,
                                open(target_path, "wb") as target_file,
                            ):
                                target_file.write(source.read())

                        pb.advance(task_id, 1)
    finally:
        if _path.exists() and data.keep_source is True:
            cached_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(_path, cached_file)
        elif _path.exists():
            _path.unlink()

    return ctx


def download(
    token: CancellationToken, args: Mapping[str, Any], ctx: ContextLike, *, ui: UI
) -> ContextLike:
    class _Args(BaseModel):
        source: str
        source_hash: str
        target: str
        keep_source: bool = Field(default=True)

    data = _Args.model_validate(args, from_attributes=False)
    target = Path(
        Template(data.target).substitute(
            {
                "working_dir": ctx.working_dir,
                "metadata": ctx.metadata,
                "environ": ctx.environ,
            }
        )
    )

    hash_algo, hash_hex = data.source_hash.split(":")
    if (
        target.exists()
        and hashlib.new(hash_algo, target.read_bytes()).hexdigest() == hash_hex
    ):
        ui.print("Skipping, file already exists {}".format(target))
        return ctx

    cached_file = (
        Path(ctx.working_dir) / ".bex" / "cache" / "files" / hash_algo / hash_hex
    )
    if cached_file.exists() and cached_file.is_file():
        ui.log("Using {}".format(cached_file))
        filename = cached_file
    else:
        with ui.progress() as pb:
            task_id = pb.add_task(
                "Downloading {}".format(target.relative_to(ctx.working_dir))
            )
            filename = download_file(
                token,
                data.source,
                report_hook=lambda completed, total: pb.update(
                    task_id, completed=completed, total=total if total > 0 else None
                ),
            )

    _path = Path(filename)
    if hash_hex != hashlib.new(hash_algo, _path.read_bytes()).hexdigest():
        msg = f"Hash mismatched when downloading {data.source}"
        raise ValueError(msg)

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(_path, target)
    finally:
        if _path.exists() and data.keep_source is True:
            cached_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(_path, cached_file)
        elif _path.exists():
            _path.unlink()

    return ctx


def inline(
    token: CancellationToken, args: Mapping[str, Any], ctx: ContextLike, *, ui: UI
) -> ContextLike:
    class _Args(BaseModel):
        content: str
        target: str

    data = _Args.model_validate(args, from_attributes=False)
    content = Template(data.content).substitute(
        {
            "working_dir": ctx.working_dir,
            "metadata": ctx.metadata,
            "environ": ctx.environ,
        }
    )
    target = Path(
        Template(data.target).substitute(
            {
                "working_dir": ctx.working_dir,
                "metadata": ctx.metadata,
                "environ": ctx.environ,
            }
        )
    )

    target.write_text(content)
    return ctx
