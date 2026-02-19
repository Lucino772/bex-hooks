# bex-hooks-python

Python-related hooks for **bex**. This package provides hooks to create and manage Python virtual environments and their dependencies.

## `python/setup-python`

Sets up a Python virtual environment for a specified version and synchronizes its dependencies using `uv`. When both `requirements` and `requirements_file` are provided, their contents are merged into a single set of requirements.

### Arguments

| Name | Type | Default | Description |
|---|---|---:|---|
| `version` | `str` | *(required)* | Python version to provision (e.g. `">=3.11,<3.12"`) |
| `uv` | `str \| None` | `None` | Version of `uv` to use |
| `requirements` | `str` | `""` | Inline requirements (e.g. `"requests==2.32.0"`). |
| `requirements_file` | `list[str]` | `[]` | One or more requirements file paths. |
| `activate_env` | `bool` | `False` | If `True`, activates the environment for subsequent steps. |
| `set_python_path` | `bool` | `False` | If `True`, sets `PYTHONPATH` to the virtual environment. |
| `inexact` | `bool` | `False` | If `True`, tells `uv` not to remove dependencies that are present but not declared in the requirements. |

### Example

```yaml
hooks:
  - id: python/setup-python
    version: ">=3.11,<3.12"
    uv: "0.4.0"
    requirements_file:
      - requirements.txt
    requirements: |
      requests==2.32.0
      requirements_file:
    activate_env: true
    inexact: true
```
