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
from enum import Enum

from PyQt5 import QtCore, QtWidgets

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand, CommandCanceled, CommandUnavailable
from bubblesub.cmd.common import SubtitlesSelection
from bubblesub.ui.model.events import AssEventsModelColumn


class InlineEditMode(Enum):
    def __str__(self) -> str:
        return self.value

    Start = "start"
    End = "end"
    AssStyle = "style"
    Actor = "actor"
    Text = "text"
    Note = "note"
    ShortDuration = "short-duration"
    LongDuration = "long-duration"
    Layer = "layer"
    MarginVertical = "margin-vertical"
    MarginLeft = "margin-left"
    MarginRight = "margin-right"
    IsComment = "is-comment"


COLUMN_MAP = {
    InlineEditMode.Start: AssEventsModelColumn.Start,
    InlineEditMode.End: AssEventsModelColumn.End,
    InlineEditMode.AssStyle: AssEventsModelColumn.AssStyle,
    InlineEditMode.Actor: AssEventsModelColumn.Actor,
    InlineEditMode.Text: AssEventsModelColumn.Text,
    InlineEditMode.Note: AssEventsModelColumn.Note,
    InlineEditMode.ShortDuration: AssEventsModelColumn.ShortDuration,
    InlineEditMode.LongDuration: AssEventsModelColumn.LongDuration,
    InlineEditMode.Layer: AssEventsModelColumn.Layer,
    InlineEditMode.MarginVertical: AssEventsModelColumn.MarginVertical,
    InlineEditMode.MarginLeft: AssEventsModelColumn.MarginLeft,
    InlineEditMode.MarginRight: AssEventsModelColumn.MarginRight,
    InlineEditMode.IsComment: AssEventsModelColumn.IsComment,
}


class InlineEditCommand(BaseCommand):
    names = ["inline-edit"]
    help_text = "Triggers an inline edit of a given subtitle."

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-t",
            "--target",
            help="subtitles to process",
            type=lambda value: SubtitlesSelection(api, value),
            default="selected",
        )
        parser.add_argument(
            "-m",
            "--mode",
            type=InlineEditMode,
            choices=list(InlineEditMode),
            default=InlineEditMode.Text,
            help="which cell to edit",
        )

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        subtitles = await self.args.target.get_subtitles()
        if not subtitles:
            raise CommandCanceled

        subtitles_grid = main_window.findChild(
            QtWidgets.QWidget, "subtitles-grid"
        )

        index = subtitles_grid.model().index(
            subtitles[0].index, COLUMN_MAP[self.args.mode].value,
        )

        self.api.subs.selected_indexes = [subtitles[0].index]
        subtitles_grid.setFocus()

        # even though the normal selection will update the grid,
        # it will focus column 0
        subtitles_grid.setCurrentIndex(index)
        selection = QtCore.QItemSelection()
        selection.select(index, index)
        subtitles_grid.selectionModel().select(
            selection,
            QtCore.QItemSelectionModel.Rows
            | QtCore.QItemSelectionModel.Current
            | QtCore.QItemSelectionModel.Select,
        )

        if not subtitles_grid.edit(index):
            raise CommandUnavailable


COMMANDS = [InlineEditCommand]
