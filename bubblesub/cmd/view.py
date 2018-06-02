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
    StyleEditor = 'style-editor'
    ActorEditor = 'actor-editor'
    LayerEditor = 'layer-editor'
    MarginLeftEditor = 'margin-left-editor'
    MarginRightEditor = 'margin-right-editor'
    MarginVerticalEditor = 'margin-vertical-editor'
    StartTimeEditor = 'start-time-editor'
    EndTimeEditor = 'end-time-editor'
    DurationEditor = 'duration-editor'
    CommentCheckbox = 'comment-checkbox'
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
            TargetWidget.StyleEditor: 'style editor',
            TargetWidget.ActorEditor: 'actor editor',
            TargetWidget.LayerEditor: 'layer editor',
            TargetWidget.MarginLeftEditor: 'left margin editor',
            TargetWidget.MarginRightEditor: 'right margin editor',
            TargetWidget.MarginVerticalEditor: 'vertical margin editor',
            TargetWidget.StartTimeEditor: 'start time editor',
            TargetWidget.EndTimeEditor: 'end time editor',
            TargetWidget.DurationEditor: 'duration editor',
            TargetWidget.CommentCheckbox: 'comment checkbox',
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
            TargetWidget.StyleEditor: main_window.editor.bar1.style_edit,
            TargetWidget.ActorEditor: main_window.editor.bar1.actor_edit,
            TargetWidget.LayerEditor: main_window.editor.bar1.layer_edit,
            TargetWidget.MarginLeftEditor:
                main_window.editor.bar1.margin_l_edit,
            TargetWidget.MarginRightEditor:
                main_window.editor.bar1.margin_r_edit,
            TargetWidget.MarginVerticalEditor:
                main_window.editor.bar1.margin_v_edit,
            TargetWidget.StartTimeEditor:
                main_window.editor.bar2.start_time_edit,
            TargetWidget.EndTimeEditor: main_window.editor.bar2.end_time_edit,
            TargetWidget.DurationEditor: main_window.editor.bar2.duration_edit,
            TargetWidget.CommentCheckbox:
                main_window.editor.bar2.comment_checkbox,
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
