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

import typing as T

from PyQt5 import QtWidgets

import bubblesub.api.api  # pylint: disable=unused-import
import bubblesub.event


class GuiApi:
    """The GUI API."""

    quit_requested = bubblesub.event.EventHandler()
    begin_update_requested = bubblesub.event.EventHandler()
    end_update_requested = bubblesub.event.EventHandler()

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
            self,
            func: T.Callable[[QtWidgets.QMainWindow], T.Awaitable[None]],
    ) -> None:
        """
        Execute function in GUI thread.

        :param func: function to execute
        :param args: arguments passed to the function
        :param kwargs: keyword arguments passed to the function
        """
        await func(self._main_window)

    def quit(self) -> None:
        """Exit the application."""
        self.quit_requested.emit()

    def begin_update(self) -> None:
        """Throttle updates to GUI, reducing effects such as flickering."""
        self.begin_update_requested.emit()

    def end_update(self) -> None:
        """Stop throttling GUI updates."""
        self.end_update_requested.emit()
