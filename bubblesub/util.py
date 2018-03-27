import re
import time
import fractions
import hashlib

import pysubs2.time


def ms_to_str(milliseconds):
    return pysubs2.time.ms_to_str(milliseconds, fractions=True)


def str_to_ms(text):
    result = re.match('''
        ^(?P<sign>[+-])?
        (?:(?P<hour>\\d+):)?
        (?P<minute>\\d\\d):
        (?P<second>\\d\\d)\\.
        (?P<millisecond>\\d\\d\\d)$''', text.strip(), re.VERBOSE)

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


def hash_digest(subject):
    return hashlib.md5(str(subject).encode('utf-8')).hexdigest()


class Benchmark:
    def __init__(self, msg):
        self._msg = msg
        self._time = time.time()

    def __enter__(self):
        self._time = time.time()
        print('{}: started'.format(self._msg))
        return self

    def __exit__(self, *args, **kwargs):
        print('{}: ended {:.02f} s'.format(
            self._msg, time.time() - self._time))

    def mark(self, msg):
        print('{}: {:.02f} s'.format(msg, time.time() - self._time))
        self._time = time.time()


def eval_expr(expr):
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

    def eval_(node):
        if isinstance(node, ast.Num):
            return fractions.Fraction(node.n)
        elif isinstance(node, ast.BinOp):
            return op_map[type(node.op)](eval_(node.left), eval_(node.right))
        elif isinstance(node, ast.UnaryOp):
            return op_map[type(node.op)](eval_(node.operand))
        raise TypeError(node)

    return eval_(ast.parse(str(expr), mode='eval').body)
