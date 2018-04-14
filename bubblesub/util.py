import fractions
import hashlib
import itertools
import re
import time
import typing as T

MAX_REPRESENTABLE_TIME = 3599990


class RefDict:
    def __init__(self) -> None:
        self._map: T.Dict[int, T.Any] = {}

    def __getitem__(self, key: int) -> T.Any:
        return self._map[key]

    def __setitem__(self, key: int, data: T.Any) -> None:
        self._map[key] = data


ref_dict = RefDict()


def ms_to_times(milliseconds: int) -> T.Tuple[int, int, int, int]:
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
    sgn = '-' if milliseconds < 0 else ''
    hours, minutes, seconds, milliseconds = ms_to_times(abs(milliseconds))
    return f'{sgn}{hours:01d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}'


def str_to_ms(text: str) -> int:
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
    return hashlib.md5(str(subject).encode('utf-8')).hexdigest()


class Benchmark:
    def __init__(self, msg: str) -> None:
        self._msg = msg
        self._time = time.time()

    def __enter__(self) -> 'Benchmark':
        self._time = time.time()
        print('{}: started'.format(self._msg))
        return self

    def __exit__(self, *args: T.Any, **kwargs: T.Any) -> None:
        difference = time.time() - self._time
        print(f'{self._msg}: ended {difference:.02f} s')

    def mark(self, msg: str) -> None:
        print('{}: {:.02f} s'.format(msg, time.time() - self._time))
        self._time = time.time()


def eval_expr(expr: str) -> T.Union[int, float, fractions.Fraction]:
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
    for _, group in itertools.groupby(
            enumerate(sorted(indexes, reverse=reverse)),
            lambda item: item[1] - item[0]
    ):
        elems = list(group)
        start_idx = elems[0][1]
        end_idx = elems[-1][1]
        yield (start_idx, end_idx + 1 - start_idx)
