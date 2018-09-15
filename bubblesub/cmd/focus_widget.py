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

import argparse
import enum

from PyQt5 import QtWidgets

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand


class _TargetWidget(enum.Enum):
    """Known widgets in GUI."""

    def __str__(self) -> str:
        return self.value

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
    Console = 'console'
    ConsoleInput = 'console-input'


class FocusWidgetCommand(BaseCommand):
    names = ['focus-widget']
    help_text = 'Focuses given widget.'

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        widget = main_window.findChild(
            QtWidgets.QWidget, str(self.args.target)
        )
        widget.setFocus()
        if self.args.select:
            widget.selectAll()

    @staticmethod
    def _decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            'target',
            help='which widget to focus',
            type=_TargetWidget,
            choices=list(_TargetWidget)
        )
        parser.add_argument(
            '-s', '--select',
            help='whether to select the text',
            action='store_true'
        )


COMMANDS = [FocusWidgetCommand]
