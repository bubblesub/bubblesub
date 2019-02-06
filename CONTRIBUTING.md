## Basic development guidelines

- To install development dependencies: `pip install --user -e '.[develop]'`
- To run tests: `python setup.py test`
- To run linters: `python setup.py lint`
- To run formatters: `python setup.py fmt`
  (`bubblesub` uses [`black`](https://github.com/ambv/black))
- To run type checks: `python setup.py mypy`
- To generate documentation: `python setup.py doc`
