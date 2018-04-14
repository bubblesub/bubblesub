import queue
import sys
import time
import traceback
import typing as T

from PyQt5 import QtCore

TTask = T.TypeVar('TTask')  # pylint: disable=invalid-name
TResult = T.TypeVar('TResult')  # pylint: disable=invalid-name
TProvider = T.TypeVar('TProvider')  # pylint: disable=invalid-name


class ProviderContext(T.Generic[TTask, TResult]):
    def start_work(self) -> None:
        pass

    def end_work(self) -> None:
        pass

    def work(self, task: TTask) -> TResult:
        raise NotImplementedError('Not implemented')


class ProviderThread(QtCore.QThread):
    finished = QtCore.pyqtSignal(object)

    # executed in main thread
    def __init__(
            self,
            queue_: queue.LifoQueue,
            context: ProviderContext
    ) -> None:
        super().__init__()
        self._queue: queue.LifoQueue = queue_
        self._context = context
        self._running = False

    def start(
            self,
            priority: QtCore.QThread.Priority = QtCore.QThread.NormalPriority
    ) -> None:
        self._running = True
        super().start(priority)

    def stop(self) -> None:
        self._running = False

    # executed in child thread
    def run(self) -> None:
        self._context.start_work()
        work = self._context.work
        while self._running:
            arg = self._queue.get()
            if arg is None:
                break
            try:
                result = work(arg)
            except Exception as ex:  # pylint: disable=broad-except
                print(type(ex), ex, file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
                time.sleep(1)
            else:
                self.finished.emit(result)
            self._queue.task_done()
        self._context.end_work()


class ProviderSignals(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)


class Provider(T.Generic[TProvider]):
    def __init__(
            self,
            parent: QtCore.QObject,
            context: ProviderContext
    ) -> None:
        super().__init__()
        self._signals = ProviderSignals()
        self._queue: queue.LifoQueue = queue.LifoQueue()
        self.worker = ProviderThread(self._queue, context)
        self.worker.setParent(parent)
        self.worker.finished.connect(self._on_work_finish)
        self.worker.start()

    @property
    def finished(self) -> QtCore.pyqtSignal:
        return self._signals.finished

    def __del__(self) -> None:
        self.worker.stop()

    def clear_tasks(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get(False)
            except queue.Empty:
                continue
            self._queue.task_done()

    def schedule_task(self, task_data: TTask) -> None:
        self._queue.put(task_data)

    def _on_work_finish(self, result: TResult) -> None:
        self.finished.emit(result)
