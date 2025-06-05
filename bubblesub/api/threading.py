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
import time
from collections.abc import Callable
from typing import Any, ContextManager, TypeVar, cast

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

from bubblesub.api.log import LogApi

T = TypeVar("T", bound=Callable[..., Any])


def synchronized(lock: ContextManager) -> Callable[[T], T]:
    """A decorator that lets the passed function run only when given lock is
    active.

    :param lock: lock to use
    :return: decorated function
    """

    def _outer(func: T) -> T:
        def _inner(*args: Any, **kwargs: Any) -> Any:
            with lock:
                return func(*args, **kwargs)

        return cast(T, _inner)

    return _outer


class _WorkerSignals(QObject):
    finished = pyqtSignal(object)


class QueueWorker(QRunnable):
    """Worker thread for continuous task queues."""

    def __init__(self, log_api: LogApi) -> None:
        """Initialize self.

        :param log_api: logging API
        """
        super().__init__()
        self._log_api = log_api
        self._running = False
        self._clearing = False
        self._queue: queue.Queue[  # pylint: disable=unsubscriptable-object
            Any
        ] = queue.Queue()

    def run(self) -> None:
        """Run the thread.

        Gets tasks from the internal queue and passes them to the _process_task
        function.
        Erroneous tasks (processing of which throws an exception) are
        discarded, and the exception is logged to stdout.
        """
        self._running = True
        with self._log_api.exception_guard():
            self._started()
        while self._running:
            if self._clearing:
                time.sleep(0.1)
                continue

            task = self._queue.get()
            if task is None:
                break
            with self._log_api.exception_guard():
                self._process_task(task)
            self._queue.task_done()
        with self._log_api.exception_guard():
            self._finished()

    def _process_task(self, task: Any) -> None:
        """Process a task and return a result.

        :param task: task to process
        """

    def stop(self) -> None:
        """Stop processing any remaining tasks and quit the thread ASAP."""
        self.clear_tasks()
        self._running = False
        self._queue.put(None)  # make sure run() exits

    def schedule_task(self, task_data: Any) -> None:
        """Put a new task onto internal task queue.

        :param task_data: task to process
        """
        self._queue.put(task_data)

    def clear_tasks(self) -> None:
        """Remove all remaining tasks.

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

    def _started(self) -> None:
        """Called when the thread starts."""

    def _finished(self) -> None:
        """Called when the thread finishes."""


class OneShotWorker(QRunnable):
    """Worker thread for one shot tasks."""

    def __init__(self, log_api: LogApi, func: Callable[[], Any]) -> None:
        """Initialize self.

        :param log_api: logging API
        :param func: the function to run on this worker thread
        """
        super().__init__()
        self.signals = _WorkerSignals()

        self._log_api = log_api
        self._func = func

    def run(self) -> None:
        """Run the function."""
        with self._log_api.exception_guard():
            result = self._func()
            self.signals.finished.emit(result)


class ThreadingApi:
    """API for scheduling background tasks."""

    def __init__(self, log_api: LogApi) -> None:
        """Initialize self.

        :param log_api: logging API
        """
        self._log_api = log_api
        self._thread_pool = QThreadPool()

    def schedule_task(
        self,
        function: Callable[..., Any],
        complete_callback: Callable[..., Any],
    ) -> None:
        """Schedule a task to run in the background thread pool.

        :param function: function to run
        :param complete_callback:
            callback to execute when the function finishes
            (executed in the qt thread)
        """
        worker = OneShotWorker(self._log_api, function)
        worker.signals.finished.connect(complete_callback)
        self._thread_pool.start(worker)

    def schedule_runnable(self, runnable: QRunnable) -> None:
        """Schedule a QRunnable to run in the background thread pool.

        :param runnable: QRunnable to schedule
        """
        self._thread_pool.start(runnable)
