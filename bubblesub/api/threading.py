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

import typing as T

from PyQt5 import QtCore

from bubblesub.api.log import LogApi


class WorkerSignals(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)


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
