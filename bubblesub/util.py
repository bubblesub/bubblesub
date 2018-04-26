"""Miscellaneous functions and classes for general purpose usage."""

import fractions
import hashlib
import itertools
import re
import time
import typing as T

MAX_REPRESENTABLE_TIME = 3599990


class RefDict:
    """A dictionary-like object that stores references to objects."""

    def __init__(self) -> None:
        """Initialize self."""
        self._map: T.Dict[int, T.Any] = {}

    def __getitem__(self, key: int) -> T.Any:
        """
        Return self[key].

        :param key: object id
        :return: associated object
        """
        return self._map[key]

    def __setitem__(self, key: int, value: T.Any) -> None:
        """
        Set self[key] to value.

        :param key: object id
        :param value: object instance
        """
        self._map[key] = value


ref_dict = RefDict()  # pylint: disable=invalid-name


def ms_to_times(milliseconds: int) -> T.Tuple[int, int, int, int]:
    """
    Convert PTS to tuple symbolizing time.

    :param milliseconds: PTS
    :return: tuple with hours, minutes, seconds and milliseconds
    """
    if milliseconds < 0:
        milliseconds = 0
    if milliseconds > MAX_REPRESENTABLE_TIME:
        milliseconds = MAX_REPRESENTABLE_TIME

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
    return f'{sgn}{hours:01d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}'


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

    def __enter__(self) -> None:
        """Start counting time."""
        self._time = time.time()
        print('{}: started'.format(self._msg))

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
    for _, group in itertools.groupby(
            enumerate(sorted(indexes, reverse=reverse)),
            lambda item: item[1] - item[0]
    ):
        elems = list(group)
        start_idx = elems[0][1]
        end_idx = elems[-1][1]
        yield (start_idx, end_idx + 1 - start_idx)


class ScopedCounter:
    """
    Tracks number of occurrences.

    x = ScopedCounter()
    with x:
        assert x.num == 1
        with x:
            assert x.num == 2
        assert x.num == 1
    """

    def __init__(self) -> None:
        """Initialize self."""
        self.num = 0

    def __enter__(self) -> None:
        """Increments the counter."""
        self.num += 1

    def __exit__(
            self,
            _exc_type: T.Optional[T.Type[BaseException]],
            _exc_val: T.Optional[Exception],
            _exc_tb: T.Any
    ) -> bool:
        """
        Decrements the counter.

        :param _exc_type: exception type
        :param _exc_val: exception value
        :param _exc_tb: exception traceback
        :return: whether to suppress the exception
        """
        self.num -= 1
        return False
