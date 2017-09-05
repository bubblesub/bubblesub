import re
import sys
import time
import pickle
import queue
import traceback
from numbers import Number
from collections import Set, Mapping, deque
from pathlib import Path
from PyQt5 import QtCore
import xdg
import pysubs2.time


class classproperty(property):
    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()


def escape_ass_tag(text):
    return (
        text
        .replace('\\', r'\\')
        .replace('{', r'\[')
        .replace('}', r'\]'))


def unescape_ass_tag(text):
    return (
        text
        .replace(r'\\', '\\')
        .replace(r'\[', '{')
        .replace(r'\]', '}'))


def ass_to_plaintext(text, mask=False):
    return (
        re.sub('{[^}]+}', '\N{FULLWIDTH ASTERISK}' if mask else '', text)
        .replace('\\h', ' ')
        .replace('\\N', ' '))


def character_count(text):
    return len(re.sub(r'\W+', '', ass_to_plaintext(text), flags=re.I | re.U))


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
        ret = (((hour * 60) + minute * 60) + second) * 1000 + millisecond
        if sign == '-':
            ret = -ret
        return ret
    raise ValueError('Invalid time')


def _get_cache_file_path(cache_name):
    return Path(xdg.XDG_CACHE_HOME) / 'bubblesub' / (cache_name + '.dat')


def load_cache(cache_name):
    cache_file = _get_cache_file_path(cache_name)
    if cache_file.exists():
        with cache_file.open(mode='rb') as handle:
            return pickle.load(handle)
    return None


def save_cache(cache_name, data):
    cache_file = _get_cache_file_path(cache_name)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with cache_file.open(mode='wb') as handle:
        pickle.dump(data, handle)


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


class ObservableProperty:
    def __init__(self, attr):
        self.attr = attr

    def __get__(self, instance, owner):
        return instance.__dict__.get(self.attr, None)

    def __set__(self, instance, value):
        if getattr(instance, self.attr) != value:
            instance.notify_before_property_change()
            instance.__dict__[self.attr] = value
            instance.notify_after_property_change()


class ObservableObject:
    prop = {}
    REQUIRED = object()

    def __init_subclass__(cls):
        if not hasattr(cls, 'prop'):
            raise RuntimeError(
                'Observable object needs to have a "prop" class property '
                'that tells what to observe')
        for key in cls.prop:
            setattr(cls, key, ObservableProperty(key))

    def __init__(self, **kwargs):
        self._dirty = False
        self._throttled = True
        empty = object()
        for key, value in self.prop.items():
            user_value = kwargs.get(key, empty)
            if user_value is empty:
                if value == self.REQUIRED:
                    raise RuntimeError('Missing argument: {}'.format(key))
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, user_value)
        for key in kwargs:
            if key not in self.prop:
                raise RuntimeError('Invalid argument: {}'.format(key))
        self._throttled = False

    def begin_update(self):
        self._throttled = True
        self._before_change()

    def end_update(self):
        self._throttled = False
        if self._dirty:
            self._after_change()
            self._dirty = False

    def notify_before_property_change(self):
        if not self._throttled:
            self._before_change()

    def notify_after_property_change(self):
        self._dirty = True
        if not self._throttled:
            self._after_change()

    def _before_change(self):
        pass

    def _after_change(self):
        pass


# alternative to QtCore.QAbstractListModel that simplifies indexing
class ListModel(QtCore.QObject):
    items_inserted = QtCore.pyqtSignal([int, int])
    items_removed = QtCore.pyqtSignal([int, int])
    item_changed = QtCore.pyqtSignal([int])
    items_about_to_be_inserted = QtCore.pyqtSignal([int, int])
    items_about_to_be_removed = QtCore.pyqtSignal([int, int])
    item_about_to_change = QtCore.pyqtSignal([int])

    def __init__(self):
        super().__init__()
        self._data = []

    def __len__(self):
        return len(self._data)

    def __getitem__(self, idx):
        return self._data[idx]

    def __setitem__(self, idx, value):
        self._data[idx] = value
        if isinstance(idx, slice):
            for i, _ in enumerate(self._data[idx]):
                self.item_changed.emit(i)
        else:
            self.item_changed.emit(idx)

    def get(self, idx, default=None):
        if idx < 0 or idx >= len(self):
            return default
        return self[idx]

    def index(self, data):
        for idx, item in enumerate(self):
            if item == data:
                return idx
        return None

    def insert(self, idx, data):
        if not data:
            return
        self.items_about_to_be_inserted.emit(idx, len(data))
        self._data = self._data[:idx] + data + self._data[idx:]
        self.items_inserted.emit(idx, len(data))

    def remove(self, idx, count):
        self.items_about_to_be_removed.emit(idx, count)
        self._data = self._data[:idx] + self._data[idx + count:]
        self.items_removed.emit(idx, count)


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
        self.worker.finished.connect(self._work_finished)
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

    def _work_finished(self, result):
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
