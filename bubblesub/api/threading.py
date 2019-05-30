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

"""Threading API."""

import queue
import sys
import time
import traceback
import typing as T

from PyQt5 import QtCore

from bubblesub.api.log import LogApi


class WorkerSignals(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)


class QueueWorker(QtCore.QRunnable):
    """Worker thread for continuous task queues."""

    def __init__(
        self, log_api: LogApi, func: T.Callable[[T.Any], T.Any]
    ) -> None:
        """
        Initialize self.

        :param log_api: logging API
        :param func: the function to run on this worker thread
        """
        super().__init__()
        self.signals = WorkerSignals()

        self._log_api = log_api
        self._func = func

        self._running = False
        self._clearing = False
        self._queue: queue.LifoQueue[T.Any] = queue.LifoQueue()

    def run(self) -> None:
        """
        Run the thread.

        Gets tasks from the internal queue and passes them to internal
        callbacks. Once the task has been completed, signals the result via
        "finished" signal.
        Erroneous tasks (processing of which throws an exception) are
        discarded, and the exception is logged to stdout.
        """
        self._running = True
        while self._running:
            if self._clearing:
                time.sleep(0.1)
                continue

            arg = self._queue.get()
            if arg is None:
                break
            with self._log_api.exception_guard():
                result = self._func(arg)
                self.signals.finished.emit(result)
            self._queue.task_done()

    def stop(self) -> None:
        """Stop processing any remaining tasks and quit the thread ASAP."""
        self.clear_tasks()
        self._running = False
        self._queue.put(None)  # make sure run() exits

    def schedule_task(self, task_data: T.Any) -> None:
        """
        Put a new task onto internal task queue.

        :param task_data: task to process
        """
        self._queue.put(task_data)

    def clear_tasks(self) -> None:
        """
        Remove all remaining tasks.

        Doesn't fire the finished signal.
        """
        self._clearing = True
        while not self._queue.empty():
            try:
                self._queue.get(False)
            except queue.Empty:
                continue
            self._queue.task_done()
        self._clearing = False


class OneShotWorker(QtCore.QRunnable):
    """Worker thread for one shot tasks."""

    def __init__(self, log_api: LogApi, func: T.Callable[[], T.Any]) -> None:
        """
        Initialize self.

        :param log_api: logging API
        :param func: the function to run on this worker thread
        """
        super().__init__()
        self.signals = WorkerSignals()

        self._log_api = log_api
        self._func = func

    def run(self) -> None:
        """Run the function."""
        with self._log_api.exception_guard():
            result = self._func()
            self.signals.finished.emit(result)


class ThreadingApi:
    def __init__(self, log_api: LogApi) -> None:
        self._log_api = log_api
        self._thread_pool = QtCore.QThreadPool()

    def schedule_task(self, function, complete_callback) -> None:
        worker = OneShotWorker(self._log_api, function)
        worker.signals.finished.connect(complete_callback)
        self._thread_pool.start(worker)

    def create_task_queue(self, function, complete_callback) -> QueueWorker:
        worker = QueueWorker(self._log_api, function)
        worker.signals.finished.connect(complete_callback)
        self._thread_pool.start(worker)
        return worker
