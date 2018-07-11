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

import enum
import fractions
import hashlib
import itertools
import re
import time
import typing as T


class _BaseIntEnum(enum.IntEnum):
    @classmethod
    def from_string(cls, name: str) -> None:
        try:
            return cls[name.title()]
        except KeyError:
            raise ValueError

    def __str__(self) -> str:
        return self.name.lower()


class ShiftTarget(_BaseIntEnum):
    """What parts to shift in a target that has a start and an end point."""

    Start = 1
    End = 2
    Both = 3


class HorizontalDirection(_BaseIntEnum):
    """Generic direction on a horizontal 1D axis."""

    Left = 1
    Right = 2


class VerticalDirection(_BaseIntEnum):
    """Generic direction on a vertical 1D axis."""

    Above = 1
    Below = 2


class BooleanOperation(_BaseIntEnum):
    """Operation to perform on a boolean."""

    On = 1
    Off = 2
    Enable = 1
    Disable = 2
    Toggle = 3


def ms_to_times(milliseconds: int) -> T.Tuple[int, int, int, int]:
    """
    Convert PTS to tuple symbolizing time.

    :param milliseconds: PTS
    :return: tuple with hours, minutes, seconds and milliseconds
    """
    if milliseconds < 0:
        milliseconds = 0

    milliseconds = int(round(milliseconds))
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return hours, minutes, seconds, milliseconds


def ms_to_str(milliseconds: int) -> str:
    """
    Convert PTS to a human readable form.

    :param milliseconds: PTS
    :return: PTS representation in form of `[-]HH:MM:SS.mmm`
    """
    sgn = '-' if milliseconds < 0 else ''
    hours, minutes, seconds, milliseconds = ms_to_times(abs(milliseconds))
    return f'{sgn}{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}'


def str_to_ms(text: str) -> int:
    """
    Convert a human readable text in form of `[[-]HH:]MM:SS.mmm` to PTS.

    :param text: input text
    :return: PTS
    """
    result = re.match(
        '''
        ^(?P<sign>[+-])?
        (?:(?P<hour>\\d+):)?
        (?P<minute>\\d\\d):
        (?P<second>\\d\\d)\\.
        (?P<millisecond>\\d\\d\\d)$
        '''.strip(),
        text.strip(),
        re.VERBOSE
    )

    if result:
        sign = result.group('sign')
        hour = int(result.group('hour'))
        minute = int(result.group('minute'))
        second = int(result.group('second'))
        millisecond = int(result.group('millisecond'))
        ret = ((((hour * 60) + minute) * 60) + second) * 1000 + millisecond
        if sign == '-':
            ret = -ret
        return ret
    raise ValueError('Invalid time')


def hash_digest(subject: T.Any) -> str:
    """
    Return MD5 digest of given subject.

    :param subject: any
    :return: MD5 digest
    """
    return hashlib.md5(str(subject).encode('utf-8')).hexdigest()


class Benchmark:
    """Tracks execution time of Python code."""

    def __init__(self, msg: str) -> None:
        """
        Initialize self.

        :param msg: message to print for benchmark start and end
        """
        self._msg = msg
        self._time = time.time()

    def __enter__(self) -> 'Benchmark':
        """
        Start counting time.

        :return: self
        """
        self._time = time.time()
        print('{}: started'.format(self._msg))
        return self

    def __exit__(self, *args: T.Any, **kwargs: T.Any) -> None:
        """Stop counting time."""
        difference = time.time() - self._time
        print(f'{self._msg}: ended {difference:.04f} s')

    def mark(self, msg: str) -> None:
        """
        Print current elapsed time and restart time counting.

        :param msg: message to print
        """
        print('{}: {:.04f} s'.format(msg, time.time() - self._time))
        self._time = time.time()


def eval_expr(expr: str) -> T.Union[int, float, fractions.Fraction]:
    """
    Evaluate simple expression.

    :param expr: expression to evaluate
    :return: scalar result
    """
    import ast
    import operator

    op_map = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.BitXor: operator.xor,
        ast.USub: operator.neg,
    }

    def eval_(
            node: T.List[ast.stmt]
    ) -> T.Union[int, float, fractions.Fraction]:
        if isinstance(node, ast.Num):
            return fractions.Fraction(node.n)
        elif isinstance(node, ast.BinOp):
            return op_map[type(node.op)](eval_(node.left), eval_(node.right))
        elif isinstance(node, ast.UnaryOp):
            return op_map[type(node.op)](eval_(node.operand))
        raise TypeError(node)

    return eval_(ast.parse(str(expr), mode='eval').body)


def make_ranges(
        indexes: T.Iterable[int],
        reverse: bool = False
) -> T.Iterable[T.Tuple[int, int]]:
    """
    Group indexes together into a list of consecutive ranges.

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


def sanitize_file_name(file_name: str) -> str:
    """
    Remove unusable characters from a file name.

    :param file_name: file name to sanitize
    :return: sanitized file name
    """
    file_name = file_name.replace(':', '.')
    file_name = file_name.replace(' ', '_')
    file_name = re.sub(r'(?u)[^-\w.]', '', file_name)
    return file_name


def chunks(source: T.List, size: int) -> T.Iterable[T.List]:
    """
    Yield successive chunks of given size from source.

    :param source: source list
    :param size: chunk size
    """
    for i in range(0, len(source), size):
        yield source[i:i + size]
