import sys
import time
import queue
import traceback

from PyQt5 import QtCore


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
