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

from PyQt5 import QtWidgets

import bubblesub.api
from bubblesub.api.cmd import BaseCommand


class ViewSetPaletteCommand(BaseCommand):
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
        async def run(
                api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow
        ) -> None:
            api.opt.general.current_palette = self._palette_name
            main_window.apply_palette(self._palette_name)

        await self.api.gui.exec(run)


class ViewFocusTextEditorCommand(BaseCommand):
    """Focuses the subtitle text edit field."""

    name = 'view/focus-text-editor'
    menu_name = '&Focus text editor'

    async def run(self) -> None:
        """Carry out the command."""
        async def run(
                _api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow
        ) -> None:
            main_window.editor.center.text_edit.setFocus()
            main_window.editor.center.text_edit.selectAll()

        await self.api.gui.exec(run)


class ViewFocusNoteEditorCommand(BaseCommand):
    """Focuses the subtitle note edit field."""

    name = 'view/focus-note-editor'
    menu_name = '&Focus note editor'

    async def run(self) -> None:
        """Carry out the command."""
        async def run(
                _api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow
        ) -> None:
            main_window.editor.center.note_edit.setFocus()
            main_window.editor.center.note_edit.selectAll()

        await self.api.gui.exec(run)


class ViewFocusGridCommand(BaseCommand):
    """Focuses the subtitles grid."""

    name = 'view/focus-grid'
    menu_name = '&Focus subtitles grid'

    async def run(self) -> None:
        """Carry out the command."""
        async def run(
                _api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow
        ) -> None:
            main_window.subs_grid.setFocus()

        await self.api.gui.exec(run)


class ViewFocusSpectrogramCommand(BaseCommand):
    """Focuses the audio spectrogram."""

    name = 'view/focus-spectrogram'
    menu_name = '&Focus spectrogram'

    async def run(self) -> None:
        """Carry out the command."""
        async def run(
                _api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow
        ) -> None:
            main_window.audio.setFocus()

        await self.api.gui.exec(run)


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    """
    Register commands in this file into the command API.

    :param cmd_api: command API
    """
    for cls in [
            ViewSetPaletteCommand,
            ViewFocusTextEditorCommand,
            ViewFocusNoteEditorCommand,
            ViewFocusGridCommand,
            ViewFocusSpectrogramCommand,
    ]:
        cmd_api.register_core_command(cls)
