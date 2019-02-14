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
import functools
import re
import typing as T
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

import bubblesub.api  # pylint: disable=unused-import
from bubblesub.ui.util import SUBS_FILE_FILTER, save_dialog


class GuiApi(QtCore.QObject):
    """The GUI API."""

    terminated = QtCore.pyqtSignal()
    request_quit = QtCore.pyqtSignal()
    request_begin_update = QtCore.pyqtSignal()
    request_end_update = QtCore.pyqtSignal()

    def __init__(self, api: "bubblesub.api.Api") -> None:
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
        self, func: T.Callable[..., T.Any], *args: T.Any, **kwargs: T.Any
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
        self.request_quit.emit()

    async def confirm_unsaved_changes(self) -> bool:
        """
        Ask user to continue if there are unsaved changes to the subtitles.

        :return: true it's okay to proceed, false if user has chosen to cancel
        """
        if not self._api.undo.needs_save:
            return True

        doc_path = self._api.subs.path
        doc_name = doc_path.name if doc_path else "Untitled"

        box = QtWidgets.QMessageBox()
        box.setWindowTitle("Question")
        box.setText(f'Do you wish to save changes to "{doc_name}"?')
        box.setIcon(QtWidgets.QMessageBox.Question)
        box.addButton(box.Save)
        box.addButton(box.Discard)
        box.addButton(box.Cancel)
        box.setDefaultButton(box.Discard)

        response = T.cast(int, box.exec_())
        if response == box.Save:
            if not doc_path:
                doc_path = await save_dialog(
                    self._main_window,
                    file_filter=SUBS_FILE_FILTER,
                    directory=self.get_dialog_dir(),
                )
                if not doc_path:
                    return False
            self._api.subs.save_ass(doc_path, remember_path=True)
            return True
        if response == box.Discard:
            return True
        assert response == box.Cancel
        return False

    @functools.lru_cache(maxsize=None)
    def get_color(self, color_name: str) -> QtGui.QColor:
        """
        Receive a color from the current color scheme.

        :param color_name: color name to retrieve
        :return: color
        """
        current_palette = self._api.cfg.opt["gui"]["current_palette"]
        try:
            palette_def = self._api.cfg.opt["gui"]["palettes"][current_palette]
            color_name = palette_def[color_name]
            color_value = tuple(
                int(match.group(1), 16)
                for match in re.finditer(
                    "([0-9a-fA-F]{2})", color_name.lstrip("#")
                )
            )
        except KeyError:
            return QtGui.QColor()
        return QtGui.QColor(*color_value)

    def get_dialog_dir(self) -> T.Optional[Path]:
        """
        Retrieve default dialog path.

        :return: default path
        """
        if self._api.subs.path:
            return self._api.subs.path.parent
        return None

    @contextlib.contextmanager
    def throttle_updates(self) -> T.Any:
        """Throttle updates to GUI."""
        self.request_begin_update.emit()
        try:
            yield
        finally:
            self.request_end_update.emit()
