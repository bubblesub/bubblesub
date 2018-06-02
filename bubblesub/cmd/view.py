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

"""General GUI commands."""

import enum

from PyQt5 import QtWidgets

import bubblesub.api
from bubblesub.api.cmd import BaseCommand


class TargetWidget(enum.Enum):
    """Known widgets in GUI."""

    TextEditor = 'text-editor'
    NoteEditor = 'note-editor'
    SubtitlesGrid = 'subtitles-grid'
    Spectrogram = 'spectrogram'


class SetPaletteCommand(BaseCommand):
    """Changes the GUI color theme."""

    name = 'view/set-palette'

    def __init__(self, api: bubblesub.api.Api, palette_name: str) -> None:
        """
        Initialize self.

        :param api: core API
        :param palette_name: name of the palette to change to
        """
        super().__init__(api)
        self._palette_name = palette_name

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return '&Switch to {} color scheme'.format(self._palette_name)

    async def run(self) -> None:
        """Carry out the command."""
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        self.api.opt.general.gui.current_palette = self._palette_name
        main_window.apply_palette(self._palette_name)


class FocusWidgetCommand(BaseCommand):
    """Focuses the target widget."""

    name = 'view/focus-widget'

    def __init__(
            self,
            api: bubblesub.api.Api,
            target_widget: str
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param target_widget: which widget to focus
        """
        super().__init__(api)
        self._target_widget = TargetWidget(target_widget)

    async def run(self) -> None:
        """Carry out the command."""
        await self.api.gui.exec(self._run_with_gui)

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        widget_name = {
            TargetWidget.TextEditor: 'text editor',
            TargetWidget.NoteEditor: 'note editor',
            TargetWidget.SubtitlesGrid: 'subtitles grid',
            TargetWidget.Spectrogram: 'spectrogram'
        }[self._target_widget]
        return '&Focus ' + widget_name

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        widget = {
            TargetWidget.TextEditor: main_window.editor.center.text_edit,
            TargetWidget.NoteEditor: main_window.editor.center.note_edit,
            TargetWidget.SubtitlesGrid: main_window.subs_grid,
            TargetWidget.Spectrogram: main_window.audio,
        }[self._target_widget]
        widget.setFocus()
        if isinstance(widget, (QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            widget.selectAll()


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    """
    Register commands in this file into the command API.

    :param cmd_api: command API
    """
    cmd_api.register_core_command(SetPaletteCommand)
    cmd_api.register_core_command(FocusWidgetCommand)
