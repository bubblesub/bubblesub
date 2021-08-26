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
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QWidget

import bubblesub.api  # pylint: disable=unused-import
from bubblesub.ui.util import SUBS_FILE_FILTER, async_dialog_exec, save_dialog


class GuiApi(QObject):
    """The GUI API."""

    terminated = pyqtSignal()
    request_quit = pyqtSignal()
    request_begin_update = pyqtSignal()
    request_end_update = pyqtSignal()

    def __init__(self, api: "bubblesub.api.Api") -> None:
        """Initialize self.

        :param api: core API
        """
        super().__init__()
        self.last_directory: Optional[Path] = None
        self._api = api
        self._main_window: Optional[QWidget] = None

    def set_main_window(self, main_window: QWidget) -> None:
        """Set main window instance, needed to interact with the GUI.

        :param main_window: main window instance
        """
        self._main_window = main_window

    def is_widget_visible(self, widget_name: str) -> bool:
        """Return whether a widget is visible.

        :param widget_name: name of the widget to look for
        :return: true if the widget is visible, false otherwise
        """
        assert self._main_window
        widget = self._main_window.findChild(QWidget, widget_name)
        if widget is None:
            raise RuntimeError(f"widget {widget_name} cannot be found")
        return widget.isVisible()

    async def exec(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute function in GUI thread.

        :param func: function to execute
        :param args: arguments passed to the function
        :param kwargs: keyword arguments passed to the function
        """
        return await func(self._main_window, *args, **kwargs)

    def quit(self) -> None:
        """Exit the application."""
        self.request_quit.emit()

    async def confirm_unsaved_changes(self) -> bool:
        """Ask user to continue if there are unsaved changes to the subtitles.

        :return: true it's okay to proceed, false if user has chosen to cancel
        """
        if not self._api.undo.needs_save:
            return True
        if not self._main_window:  # GUI was not created yet
            return True

        doc_path = self._api.subs.path
        doc_name = doc_path.name if doc_path else "Untitled"

        box = QMessageBox(self._main_window)
        box.setWindowTitle("Question")
        box.setText(f'Do you wish to save changes to "{doc_name}"?')
        box.setIcon(QMessageBox.Question)
        box.addButton(box.Save)
        box.addButton(box.Discard)
        box.addButton(box.Cancel)
        box.setDefaultButton(box.Save)

        response = await async_dialog_exec(box)
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
        assert response in {box.Cancel, box.NoButton}
        return False

    def get_dialog_dir(self) -> Optional[Path]:
        """Retrieve default dialog path.

        :return: default path
        """
        if self.last_directory:
            return self.last_directory
        if self._api.subs.path:
            return self._api.subs.path.parent
        return Path().absolute()

    @contextlib.contextmanager
    def throttle_updates(self) -> Any:
        """Throttle updates to GUI."""
        self.request_begin_update.emit()
        try:
            yield
        finally:
            self.request_end_update.emit()
