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
import typing as T
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

import bubblesub.api  # pylint: disable=unused-import
from bubblesub.ui.util import SUBS_FILE_FILTER, save_dialog


class GuiApi(QtCore.QObject):
    """The GUI API."""

    quit_requested = QtCore.pyqtSignal()
    quit_confirmed = QtCore.pyqtSignal()
    begin_update_requested = QtCore.pyqtSignal()
    end_update_requested = QtCore.pyqtSignal()

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

    def confirm_unsaved_changes(self) -> bool:
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

        response = T.cast(int, box.exec_())
        if response == box.Save:
            if not doc_path:
                doc_path = save_dialog(
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
        current_palette = self._api.opt.general.gui.current_palette
        try:
            palette_def = self._api.opt.general.gui.palettes[current_palette]
            color_value = palette_def[color_name]
        except KeyError:
            return QtGui.QVariant()
        return QtGui.QColor(*color_value)

    def get_dialog_dir(self) -> T.Optional[Path]:
        if self._api.subs.path:
            return self._api.subs.path.parent
        return None

    @contextlib.contextmanager
    def throttle_updates(self) -> T.Any:
        """Throttle updates to GUI."""
        self.begin_update_requested.emit()
        yield
        self.end_update_requested.emit()
