import re
import sys
import time
import fractions
import queue
import traceback
import hashlib

from numbers import Number
from collections import Set, Mapping, deque

import pysubs2.time

from PyQt5 import QtCore


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


class ProviderContext:
    def start_work(self):
        pass

    def end_work(self):
        pass

    def work(self, task):
        raise NotImplementedError('Not implemented')


class ProviderThread(QtCore.QThread):
    finished = QtCore.pyqtSignal(object)

    # executed in main thread
    def __init__(self, queue_, context):
        super().__init__()
        self._queue = queue_
        self._context = context
        self._running = False

    def start(self):
        self._running = True
        super().start()

    def stop(self):
        self._running = False

    # executed in child thread
    def run(self):
        self._context.start_work()
        work = self._context.work
        while self._running:
            arg = self._queue.get()
            if arg is None:
                break
            try:
                result = work(arg)
            except Exception as ex:
                print(type(ex), ex, file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
                time.sleep(1)
            else:
                self.finished.emit(result)
            self._queue.task_done()
        self._context.end_work()


class Provider(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)

    def __init__(self, parent, context):
        super().__init__()
        self._queue = queue.LifoQueue()
        self.worker = ProviderThread(self._queue, context)
        self.worker.setParent(parent)
        self.worker.finished.connect(self._on_work_finish)
        self.worker.start()

    def __del__(self):
        self.worker.stop()

    def clear_tasks(self):
        while not self._queue.empty():
            try:
                self._queue.get(False)
            except queue.Empty:
                continue
            self._queue.task_done()

    def schedule_task(self, task_data):
        self._queue.put(task_data)

    def _on_work_finish(self, result):
        self.finished.emit(result)


# snippet by Aaron Hall, taken from https://stackoverflow.com/a/30316760
# CC-BY-SA 3.0
def getsize(top_obj):
    visited = set()

    def inner(obj):
        obj_id = id(obj)
        if obj_id in visited:
            return 0
        visited.add(obj_id)
        size = sys.getsizeof(obj)
        if isinstance(obj, (str, bytes, Number, range, bytearray)):
            pass
        elif isinstance(obj, (tuple, list, Set, deque)):
            size += sum(inner(i) for i in obj)
        elif isinstance(obj, Mapping) or hasattr(obj, 'items'):
            size += sum(inner(k) + inner(v) for k, v in obj.items())
        if hasattr(obj, '__dict__'):
            size += inner(vars(obj))
        if hasattr(obj, '__slots__'):
            size += sum(
                inner(getattr(obj, s))
                for s in obj.__slots__ if hasattr(obj, s))
        return size

    return inner(top_obj)


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
