## Cheat sheet

- To install development dependencies: `pip install --user -e '.[develop]'`
- To run tests: `python setup.py test`
- To run type checks: `python setup.py mypy`
- To generate documentation: `python setup.py doc`

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
