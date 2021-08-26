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

"""Miscellaneous functions and classes for general purpose usage."""

import ast
import itertools
import operator
import re
from collections.abc import Callable, Iterable
from fractions import Fraction
from pathlib import Path
from typing import Any, TypeVar, Union


def ms_to_times(milliseconds: int) -> tuple[int, int, int, int]:
    """Convert PTS to tuple symbolizing time.

    :param milliseconds: PTS
    :return: tuple with hours, minutes, seconds and milliseconds
    """
    milliseconds = int(round(max(milliseconds, 0)))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return hours, minutes, seconds, milliseconds


def ms_to_str(milliseconds: int) -> str:
    """Convert PTS to a human readable form.

    :param milliseconds: PTS
    :return: PTS representation in form of `[-]HH:MM:SS.mmm`
    """
    sgn = "-" if milliseconds < 0 else ""
    hours, minutes, seconds, milliseconds = ms_to_times(abs(milliseconds))
    return f"{sgn}{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def str_to_ms(text: str) -> int:
    """Convert a human readable text in form of `[[-]HH:]MM:SS.mmm` to PTS.

    :param text: input text
    :return: PTS
    """
    result = re.match(
        """
        ^(?P<sign>[+-])?
        (?:(?P<hour>\\d+):)?
        (?P<minute>\\d\\d):
        (?P<second>\\d\\d)\\.
        (?P<millisecond>\\d\\d\\d)\\d*$
        """.strip(),
        text.strip(),
        re.VERBOSE,
    )

    if result:
        sign = result.group("sign")
        hour = int(result.group("hour"))
        minute = int(result.group("minute"))
        second = int(result.group("second"))
        millisecond = int(result.group("millisecond"))
        ret = ((((hour * 60) + minute) * 60) + second) * 1000 + millisecond
        if sign == "-":
            ret = -ret
        return ret
    raise ValueError(f'invalid time format: "{text}"')


def eval_expr(expr: str) -> Union[int, float, Fraction]:
    """Evaluate simple expression.

    :param expr: expression to evaluate
    :return: scalar result
    """
    TNumber = TypeVar("TNumber", bound=Union[int, float, Fraction])

    bin_ops: dict[type, Callable[[TNumber, TNumber], TNumber]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.BitXor: operator.xor,
    }

    unary_ops: dict[type, Callable[[TNumber], TNumber]] = {
        ast.USub: operator.neg,
    }

    def _eval(node: ast.AST) -> Union[int, float, Fraction]:
        if isinstance(node, ast.Constant) and isinstance(
            node.value, (int, float, str)
        ):
            return Fraction(node.value)
        if isinstance(node, ast.BinOp):
            return bin_ops[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            return unary_ops[type(node.op)](_eval(node.operand))
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        raise TypeError(node)

    return _eval(ast.parse(str(expr), mode="eval"))


def make_ranges(
    indexes: Iterable[int], reverse: bool = False
) -> Iterable[tuple[int, int]]:
    """Group indexes together into a list of consecutive ranges.

    :param indexes: list of source indexes
    :param reverse: whether ranges should be made in reverse order
    :return: list of tuples symbolizing start and end of each range
    """
    items = list(enumerate(sorted(indexes)))
    if reverse:
        items.reverse()
    for _, group in itertools.groupby(items, lambda item: item[1] - item[0]):
        elems = list(group)
        if reverse:
            elems.reverse()
        start_idx = elems[0][1]
        end_idx = elems[-1][1]
        yield (start_idx, end_idx + 1 - start_idx)


def sanitize_file_name(file_name: Union[Path, str]) -> str:
    """Remove unusable characters from a file name.

    :param file_name: file name to sanitize
    :return: sanitized file name
    """
    if isinstance(file_name, Path):
        file_name = str(file_name.resolve())

    file_name = file_name.replace("/", "_")
    file_name = file_name.replace(":", ".")
    file_name = file_name.replace(" ", "_")
    file_name = re.sub(r"(?u)[^-\w.]", "", file_name)
    return file_name


def chunks(source: list[Any], size: int) -> Iterable[list[Any]]:
    """Yield successive chunks of given size from source.

    :param source: source list
    :param size: chunk size
    :return: chunks
    """
    for i in range(0, len(source), size):
        yield source[i : i + size]


def first(source: Iterable[Any], default: Any = None) -> Any:
    """Return first element from a list or default value if the list is empty.

    :param source: source list
    :param default: default value
    :return: first element or default value
    """
    try:
        return next(iter(source))
    except StopIteration:
        return default


def ucfirst(source: str) -> str:
    """Return source string with capitalized first letter.

    :param source: source string
    :return: transformed string
    """
    if not source:
        return source
    return source[0].upper() + source[1:]


def all_subclasses(cls: Any) -> set[Any]:
    """Return all subclasses of the given class.

    :param cls: class to inspect
    :return: subclasses of the given class
    """
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)]
    )
