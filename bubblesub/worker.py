"""Utilities for running things in parallel."""
import queue
import sys
import time
import traceback
import typing as T

from PyQt5 import QtCore


class Worker(QtCore.QThread):
    """Base background worker class."""

    task_finished = QtCore.pyqtSignal(object)

    def __init__(self) -> None:
        """Initialize self."""
        super().__init__(parent=None)
        self._running = False
        self._queue: queue.LifoQueue = queue.LifoQueue()

    def run(self) -> None:
        """
        Run the thread.

        Gets tasks from the internal queue and passes them to internal
        callbacks. Once the task has been completed, signals the result via
        "task_finished" signal.
        Erroneous tasks (processing of which throws an exception) are
        discarded, and the exception is logged to stdout.
        """
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
        """Stop processing any remaining tasks and quit the thread ASAP."""
        self._running = False

    def schedule_task(self, task_data: T.Any) -> None:
        """
        Put a new task onto internal task queue.

        :param task_data: task to process
        """
        self._queue.put(task_data)

    def clear_tasks(self) -> None:
        """
        Remove all remaining tasks.

        Doesn't fire task_finished signal.
        """
        while not self._queue.empty():
            try:
                self._queue.get(False)
            except queue.Empty:
                continue
            self._queue.task_done()

    def _start_work(self) -> None:
        """
        Meant to be overriden by the user.

        Executed in the worker thread before the task processing loop is about
        to start.
        """
        pass

    def _end_work(self) -> None:
        """
        Meant to be overriden by the user.

        Executed in the worker thread after the task processing loop was
        aborted by the .stop() method call.
        """
        pass

    def _do_work(self, task: T.Any) -> T.Any:
        """
        Meant to be overriden by the user.

        Process the task. The result will be signaled via the .task_finished
        signal.

        :param task: task to process
        :return: task result
        """
        raise NotImplementedError('Not implemented')
