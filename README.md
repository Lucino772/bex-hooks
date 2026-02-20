# bex-hooks

**bex-hooks** is a configuration-driven entrypoint for [**bex**](https://github.com/Lucino772/bex) that loads a workflow definition from a YAML file, resolves configured plugins, and executes hooks in order within an isolated environment bootstrapped by `bex`.

## Content

- [Usage](#usage)
- [CLI](#cli)
  - [Global Options](#global-options)
  - [Commands](#commands)
- [Configuration](#configuration)
  - [`config`](#config)
  - [`hooks`](#hooks)

## Usage

`bex-hooks` is available on PyPI and is used as a `bex` entrypoint.

### 1. Add `bex-hooks` to the bootstrap header

In your workflow file, include `bex-hooks` in `requirements` and set the `entrypoint`:

```yaml
# /// bootstrap
# requires-python: ">=3.11,<3.12"
# requirements: |
#   bex-hooks
#   bex-hooks-files
#   bex-hooks-python
# entrypoint: bex_hooks.exec:main
# ///
```

### 2. Configure plugins and hooks

Below the header, configure which plugins to load and which hooks to run:

```yaml
config:
  plugins:
    - bex_hooks.hooks.python
    - bex_hooks.hooks.files

hooks:
  - id: files/download
    source: https://example.com/file.bin
    source_hash: md5:abc123...
    target: ./bin/file.bin

  - id: python/setup-python
    version: "3.12.8"
    requirements: |
      requests>=2,<3
```

## CLI

This entrypoint exposes a CLI.

### Global Options

The following options are defined by the entrypoint. They are set internally by the bootstrapper (via environment variables) and are not intended for manual use.

| Flags               | Environment Variable | Description                                                   |
| ------------------- | -------------------- | ------------------------------------------------------------- |
| `-f`, `--file`      | `BEX_FILE`           | Path to the workflow file.                                    |
| `-C`, `--directory` | `BEX_DIRECTORY`      | Working directory used to resolve the workflow configuration. |

### Commands

| Command  | Usage                            | Description                                                                                            |
| -------- | -------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `run`    | `bex exec run -- <command> [args...]` | Executes the workflow, then runs the specified command within the resulting environment.               |
| `shell`  | `bex exec shell`                      | Executes the workflow, then opens an interactive shell using the resulting environment.                |
| `export` | `bex exec export`                     | Executes the workflow and prints the resulting context as JSON (`working_dir`, `metadata`, `environ`). |

Command arguments for `run` support templating using metadata produced by the entrypoint:

```bash
bex exec run -- echo "{working_dir}"
```

## Configuration

The entrypoint expects the following YAML structure:

```yaml
config:
  plugins:
    - some.plugin.module

hooks:
  - id: some/hook
    if: some_condition
    # hook-specific fields...
```

### `config`

General entrypoint configuration.

| Field     | Type        | Default | Description                                                       |
| --------- | ----------- | :-----: | ----------------------------------------------------------------- |
| `plugins` | `list[str]` |   `[]`  | List of plugin modules to load. Plugins register available hooks. |

### `hooks`

Ordered list of hook definitions. Each hook entry has the following structure:

| Field            | Type   |    Default   | Description                                                                                   |
| ---------------- | ------ | :----------: | --------------------------------------------------------------------------------------------- |
| `id`             | `str`  | *(required)* | Identifier of the hook to execute.                                                            |
| `if`             | `str`  |    `None`    | Optional conditional expression. The hook executes only if the condition evaluates to `true`. |
| *(extra fields)* | varies |              | Additional fields are passed directly to the hook implementation.                             |
