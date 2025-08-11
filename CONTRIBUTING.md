## Cheat sheet

- To install development dependencies: `uv sync --dev`
- To run from a vemv: `uv run -m bubblesub`
- To run tests: `scripts/run_tests`
- To run type checks: `scripts/run_mypy`
- To generate themes and icons: `scripts/generate_assets`
- To generate documentation: `scripts/generate_documentation`

## Pre-commit

To enable pre-commit hooks, install [pre-commit](https://github.com/pre-commit/pre-commit):

```
pip install --user pre-commit
pre-commit install
```

Now every time you commit, the code should be automatically reformatted with
[isort](https://github.com/timothycrosley/isort) and
[black](https://github.com/python/black). Additionally you should get some
extra information from pylint about other problems such as unused imports.
