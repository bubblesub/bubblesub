import queue
import sys
import time
import traceback
import typing as T

from PyQt5 import QtCore


class Worker(QtCore.QThread):
    task_finished = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtCore.QObject) -> None:
        super().__init__(parent)
        self._running = False
        self._queue: queue.LifoQueue = queue.LifoQueue()

    def run(self) -> None:
        self._running = True
        self._start_work()
        while self._running:
            arg = self._queue.get()
            if arg is None:
                break
            try:
                result = self._do_work(arg)
            except Exception as ex:  # pylint: disable=broad-except
                print(type(ex), ex, file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
                time.sleep(1)
            else:
                self.task_finished.emit(result)
            self._queue.task_done()
        self._end_work()

    def stop(self):
        self._running = False

    def schedule_task(self, task_data: T.Any) -> None:
        self._queue.put(task_data)

    def clear_tasks(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get(False)
            except queue.Empty:
                continue
            self._queue.task_done()

    def _start_work(self) -> None:
        pass

    def _end_work(self) -> None:
        pass

    def _do_work(self, task: T.Any) -> T.Any:
        raise NotImplementedError('Not implemented')
