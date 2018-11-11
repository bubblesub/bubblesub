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

"""GUI API."""

import contextlib
import typing as T

from PyQt5 import QtCore, QtWidgets

import bubblesub.api.api  # pylint: disable=unused-import


class GuiApi(QtCore.QObject):
    """The GUI API."""

    quit_requested = QtCore.pyqtSignal()
    quit_confirmed = QtCore.pyqtSignal()
    begin_update_requested = QtCore.pyqtSignal()
    end_update_requested = QtCore.pyqtSignal()

    def __init__(self, api: 'bubblesub.api.api.Api') -> None:
        """
        Initialize self.

        :param api: core API
        """
        super().__init__()
        self._api = api
        self._main_window: T.Optional[QtWidgets.QWidget] = None

    def set_main_window(self, main_window: QtWidgets.QWidget) -> None:
        """
        Set main window instance, needed to interact with the GUI.

        :param main_window: main window instance
        """
        self._main_window = main_window

    async def exec(
        self, func: T.Callable, *args: T.Any, **kwargs: T.Any
    ) -> T.Any:
        """
        Execute function in GUI thread.

        :param func: function to execute
        :param args: arguments passed to the function
        :param kwargs: keyword arguments passed to the function
        """
        return await func(self._main_window, *args, **kwargs)

    def quit(self) -> None:
        """Exit the application."""
        self.quit_requested.emit()

    @contextlib.contextmanager
    def throttle_updates(self) -> T.Any:
        """Throttle updates to GUI."""
        self.begin_update_requested.emit()
        yield
        self.end_update_requested.emit()
