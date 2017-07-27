import re
import threading
import sys
import time
import json
import queue
from PyQt5 import QtCore
from pathlib import Path
import pysubs2.time


def ass_to_plaintext(text, mask=False):
    return (
        re.sub('{[^}]+}', '\N{FULLWIDTH ASTERISK}' if mask else '', text)
        .replace('\\h', ' ')
        .replace('\\N', ''))


def character_count(text):
    return len(re.sub('[^\\W]+', '', ass_to_plaintext(text), re.I))


def ms_to_str(ms):
    return pysubs2.time.ms_to_str(ms, fractions=True)


def str_to_ms(text):
    result = re.match('''
        ^(?:(?P<hour>\\d+):)?
        (?P<minute>\\d\\d):
        (?P<second>\\d\\d)\\.
        (?P<millisecond>\\d\\d\\d)$''', text.strip(), re.VERBOSE)

    if result:
        hour = int(result.group('hour'))
        minute = int(result.group('minute'))
        second = int(result.group('second'))
        millisecond = int(result.group('millisecond'))
        return pysubs2.time.make_time(
            h=hour, m=minute, s=second, ms=millisecond)
    raise ValueError('Invalid time')


def _get_cache_file_path(section_name):
    return Path('~/.cache/bubblesub/').expanduser() / (section_name + '.json')


def load_cache(section_name, key_name):
    cache_file = _get_cache_file_path(section_name)
    if cache_file.exists():
        return json.loads(cache_file.read_text()).get(key_name, None)
    return None


def save_cache(section_name, key_name, value):
    cache_file = _get_cache_file_path(section_name)
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
    else:
        data = {}
    data[key_name] = value
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data))


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


class ObservableObject:
    def __init__(self):
        self._dirty = False
        self._throttled = False

    def begin_update(self):
        self._throttled = True

    def end_update(self):
        self._throttled = False
        if self._dirty:
            self._changed()
            self._dirty = False

    def _changed(self):
        pass


class ObservableProperty:
    def __init__(self, attr):
        self.attr = attr

    def __get__(self, instance, type):
        return instance.__dict__.get(self.attr, None)

    def __set__(self, instance, value):
        if getattr(instance, self.attr) != value:
            instance.__dict__[self.attr] = value
            instance._dirty = True
            if not instance._throttled:
                instance._changed()


# alternative to QtCore.QAbstractListModel that simplifies indexing
class ListModel(QtCore.QObject):
    items_inserted = QtCore.pyqtSignal([int, int])
    items_removed = QtCore.pyqtSignal([int, int])
    item_changed = QtCore.pyqtSignal([int])

    def __init__(self):
        super().__init__()
        self._data = []

    def __len__(self):
        return len(self._data)

    def __getitem__(self, idx):
        return self._data[idx]

    def __setitem__(self, idx, value):
        self._data[idx] = value
        self.item_changed.emit(idx)

    def get(self, idx, default=None):
        if idx < 0 or idx >= len(self):
            return default
        return self[idx]

    def insert(self, idx, data):
        if not data:
            return
        self._data = self._data[:idx] + data + self._data[idx:]
        self.items_inserted.emit(idx, len(data))

    def remove(self, idx, count):
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

    # executed in child thread
    def run(self):
        self._context.start_work()
        work = self._context.work
        while True:
            arg = self._queue.get()
            if arg is None:
                break
            try:
                result = work(arg)
            except Exception as ex:
                print(type(ex), ex, file=sys.stderr)
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
        worker = ProviderThread(self._queue, context)
        worker.setParent(parent)
        worker.finished.connect(self._work_finished)
        worker.start()

    def schedule(self, task_data):
        self._queue.put(task_data)

    def _work_finished(self, result):
        self.finished.emit(result)
