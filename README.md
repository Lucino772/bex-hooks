# bex-hooks

**bex-hooks** is a configuration-driven executor implementation for [**bex**](https://github.com/Lucino772/bex) that loads a workflow definition from a YAML file, resolves configured plugins, and executes hooks in order within an isolated environment bootstrapped by `bex`.

## Content

- [Usage](#usage)
- [CLI](#cli)
  - [Global Options](#global-options)
  - [Commands](#commands)
- [Configuration](#configuration)
  - [`config`](#config)
  - [`hooks`](#hooks)

## Usage

A workflow is defined in a single YAML file containing:

1. A bootstrap header
2. The executor configuration


```yaml
# /// bootstrap
# uv: "0.10.2"
# requires-python: ">=3.11,<3.12"
# requirements: |
#   bex-hooks
#   bex-hooks-files
#   bex-hooks-python
# entrypoint: bex_hooks.exec:main
# ///

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

The bootstrap header is processed by **`bex`**, not by this executor.

For this executor, the bootstrap section must:

* Include `bex-hooks` in `requirements`
* Set `entrypoint` to `bex_hooks.exec:main`

After the environment is bootstrapped, the executor reads the YAML body (`config` and `hooks`) and executes the defined hooks in declaration order.

## CLI

This executor exposes a CLI.

### Global Options

The following options are defined by the executor. They are set internally by the bootstrapper (via environment variables) and are not intended for manual use.

| Flags               | Environment Variable | Description                                                   |
| ------------------- | -------------------- | ------------------------------------------------------------- |
| `-f`, `--file`      | `BEX_FILE`           | Path to the workflow file.                                    |
| `-C`, `--directory` | `BEX_DIRECTORY`      | Working directory used to resolve the workflow configuration. |

### Commands

| Command  | Usage                            | Description                                                                                                                                 |
| -------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `run`    | `bex run -- <command> [args...]` | Executes the workflow, then runs the specified command within the resulting environment.                                                    |
| `shell`  | `bex shell`                      | Executes the workflow, then opens an interactive shell using the resulting environment.                                                     |
| `export` | `bex export`                     | Executes the workflow and prints the resulting context as JSON (`working_dir`, `metadata`, `environ`).                                      |

Command arguments for `run` support templating using metadata produced by the executor:

```bash
bex run -- echo "{working_dir}"
```

## Configuration

The executor expects the following YAML structure:

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

General executor configuration.

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
