# bubblesub - ASS subtitle editor
# Copyright (C) 2018 Marcin Kurczewski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import ast
import contextlib
import re
import typing as T
from pathlib import Path

import docstring_parser
import pytest

from .common import collect_source_files

IGNORED_ARGUMENTS = {
    "self",
    "args",
    "kwargs",
    "_exc_type",
    "_exc_val",
    "_exc_tb",
}


def _get_nodes() -> T.Iterable[T.Tuple[Path, ast.AST, str]]:
    for path in collect_source_files():
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, (ast.FunctionDef, ast.Module)):
                docstring = ast.get_docstring(node, clean=False)
                yield path, node, docstring


_NODES = list(_get_nodes())


@contextlib.contextmanager
def _decorated_log(path: Path, node: ast.AST) -> T.Any:
    try:
        yield
    except AssertionError:
        line_number = getattr(node, "lineno", "?")
        print(f"Error at {path}:{line_number}")
        raise


def is_sentence(text: str) -> bool:
    return text.endswith(".") and not text.endswith("etc.")


def verify_function_params(
    node: ast.FunctionDef, docstring: docstring_parser.parser.Docstring
) -> None:
    expected_arg_names = [
        arg.arg for arg in node.args.args if arg.arg not in IGNORED_ARGUMENTS
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

    assert actual_arg_names == expected_arg_names, (
        f'Documentation for function "{node.name}" mismatches '
        f"its signature"
    )

    for arg, desc in zip(actual_arg_names, actual_arg_descs):
        assert desc, f'Param "{arg}" has no description'
        assert not is_sentence(desc)


def verify_function_returns(
    node: ast.FunctionDef, docstring: docstring_parser.parser.Docstring
) -> None:
    has_returns = any(
        isinstance(child_node, ast.Return) and child_node.value
        for child_node in ast.walk(node)
    )

    if has_returns and node.name != "__exit__":
        assert docstring.returns is not None, (
            'Function "{node.name}" has return statements, '
            'but no ":return: …" docstring'
        )
        assert docstring.returns.description, "Return has no description"
        assert not is_sentence(docstring.returns.description)


@pytest.mark.parametrize(
    "path,node,docstring",
    ((path, node, docstring) for path, node, docstring in _NODES if docstring),
)
def test_docstrings_validity(
    path: Path, node: ast.AST, docstring: str
) -> None:
    with _decorated_log(path, node):
        assert not docstring.startswith(
            ("\n", " ")
        ), "don't start docstrings with whitespace"

        if "\n" in docstring:
            assert docstring.rstrip(" ").endswith(
                "\n"
            ), "end multiline docstrings with a newline"


@pytest.mark.parametrize(
    "path,node,docstring",
    (
        (path, node, docstring)
        for path, node, docstring in _NODES
        if isinstance(node, ast.FunctionDef) and docstring
    ),
)
def test_function_docstrings_validity(
    path: Path, node: ast.AST, docstring: str
) -> None:
    with _decorated_log(path, node):
        docstring = docstring_parser.parse(docstring)
        verify_function_params(node, docstring)
        verify_function_returns(node, docstring)
