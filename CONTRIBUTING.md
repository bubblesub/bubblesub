## Cheat sheet

- To install development dependencies:
    ```
    uv sync --dev
    ```
- To run from a venv:
    ```
    uv run bubblesub
    ```

- To run via Docker:
    ```
    just build
    just run
    ```
    The container will run at your current UID:GID, with your home directory
    mounted in `/home/user/data`, and config directory (`~/.config/bubblesub`)
    mounted in `/home/user/.config/bubblesub/`.

## Dev stuff

- To run tests:
    ```
    just build
    just test
    ```

- To run type checks:
    ```
    just mypy
    ````

- To generate themes and icons:
    ```
    just assets
    ```

- To generate documentation:
    ```
    just docs
    ```

## Pre-commit

To enable pre-commit hooks which will run linters and formatters before each
commit, install [pre-commit](https://github.com/pre-commit/pre-commit):

```
pip install --user pre-commit
pre-commit install
```
