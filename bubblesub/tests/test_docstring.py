import ast
import typing as T
from pathlib import Path

import pytest
import docstring_parser

ROOT_DIR = Path(__file__).parent.parent
IGNORED_ARGUMENTS = {
    'self', 'args', 'kwargs', '_exc_type', '_exc_val', '_exc_tb'
}


def is_sentence(text):
    return text.endswith('.') and not text.endswith('etc.')


def collect_files(root: Path) -> T.Iterable[Path]:
    for path in root.iterdir():
        if path.is_dir():
            yield from collect_files(path)
        elif path.is_file() and path.suffix == '.py':
            yield path


def verify_function_params(
        node: ast.FunctionDef,
        docstring: docstring_parser.parser.Docstring
) -> None:
    expected_arg_names = [
        arg.arg
        for arg in node.args.args
        if arg.arg not in IGNORED_ARGUMENTS
    ]
    if node.args.vararg and node.args.vararg.arg not in IGNORED_ARGUMENTS:
        expected_arg_names.append(node.args.vararg.arg)

    actual_arg_names = [
        param.arg_name
        for param in docstring.params
        if param.arg_name not in IGNORED_ARGUMENTS
    ]
    actual_arg_descs = [
        param.description
        for param in docstring.params
        if param.arg_name not in IGNORED_ARGUMENTS
    ]

    assert \
        actual_arg_names == expected_arg_names, \
        f'Documentation for function "{node.name}" mismatches ' \
        f'its signature'

    for arg, desc in zip(actual_arg_names, actual_arg_descs):
        assert desc, f'Param "{arg}" has no description'
        assert not is_sentence(desc)


def verify_function_returns(
        node: ast.FunctionDef,
        docstring: docstring_parser.parser.Docstring
) -> None:
    has_returns = any(
        isinstance(child_node, ast.Return)
        and child_node.value
        for child_node in ast.walk(node)
    )

    if has_returns and node.name != '__exit__':
        assert \
            docstring.returns is not None, \
            'Function "{node.name}" has return statements, ' \
            'but no ":return: …" docstring'
        assert docstring.returns.description, 'Return has no description'
        assert not is_sentence(docstring.returns.description)


def verify_function_docstring(node: ast.FunctionDef) -> None:
    docstring = ast.get_docstring(node)
    if not docstring:
        return

    docstring = docstring_parser.parse(docstring)
    verify_function_params(node, docstring)
    verify_function_returns(node, docstring)


def test_collect_files():
    files = list(collect_files(ROOT_DIR))
    assert any(p.name == '__main__.py' for p in files)


@pytest.mark.parametrize('path', collect_files(ROOT_DIR))
def test_docstrings(path) -> None:
    for node in ast.walk(ast.parse(path.read_text())):
        try:
            if isinstance(node, ast.FunctionDef):
                verify_function_docstring(node)
        except AssertionError:
            print(f'Error at {path}:{node.lineno}')
            raise
