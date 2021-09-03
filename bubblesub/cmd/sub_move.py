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
from collections.abc import Iterable
from copy import copy
from typing import cast

from ass_parser import AssEvent
from PyQt5.QtWidgets import QInputDialog, QMainWindow

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand, CommandCanceled, CommandUnavailable
from bubblesub.cmd.common import SubtitlesSelection
from bubblesub.ui.util import async_dialog_exec
from bubblesub.util import make_ranges


class SubtitlesMoveCommand(BaseCommand):
    names = ["sub-move"]
    help_text = "Moves given subtitles around."

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        with self.api.undo.capture():
            indexes = await self.args.target.get_indexes()
            if not indexes:
                raise CommandUnavailable("nothing to move")

            if self.args.method == "above":
                sub_copies = list(self._move_above(indexes))
            elif self.args.method == "below":
                sub_copies = list(self._move_below(indexes))
            elif self.args.method == "gui":
                base_idx = await self.api.gui.exec(self._show_dialog, indexes)
                sub_copies = list(self._move_to(indexes, base_idx))
            else:
                raise AssertionError

            self.api.subs.selected_indexes = [sub.index for sub in sub_copies]

    def _move_above(self, indexes: list[int]) -> Iterable[AssEvent]:
        if indexes[0] == 0:
            raise CommandUnavailable("cannot move further up")
        for idx, count in make_ranges(indexes):
            chunk = [copy(s) for s in self.api.subs.events[idx : idx + count]]
            self.api.subs.events[idx - 1 : idx - 1] = chunk
            del self.api.subs.events[idx + count : idx + count + count]
            yield from chunk

    def _move_below(self, indexes: list[int]) -> Iterable[AssEvent]:
        if indexes[-1] + 1 == len(self.api.subs.events):
            raise CommandUnavailable("cannot move further down")
        for idx, count in make_ranges(indexes, reverse=True):
            chunk = [copy(s) for s in self.api.subs.events[idx : idx + count]]
            self.api.subs.events[idx + count + 1 : idx + count + 1] = chunk
            del self.api.subs.events[idx : idx + count]
            yield from chunk

    def _move_to(
        self, indexes: list[int], base_idx: int
    ) -> Iterable[AssEvent]:
        sub_copies: list[AssEvent] = []

        for idx, count in make_ranges(indexes, reverse=True):
            chunk = [copy(s) for s in self.api.subs.events[idx : idx + count]]
            chunk.reverse()
            sub_copies += chunk
            del self.api.subs.events[idx : idx + count]

        sub_copies.reverse()
        self.api.subs.events[base_idx:base_idx] = sub_copies
        return sub_copies

    async def _show_dialog(
        self, main_window: QMainWindow, indexes: list[int]
    ) -> int:
        dialog = QInputDialog(main_window)
        dialog.setLabelText("Line number to move subtitles to:")
        dialog.setIntMinimum(1)
        dialog.setIntMaximum(len(self.api.subs.events))
        if indexes:
            dialog.setIntValue(indexes[0] + 1)
        dialog.setInputMode(QInputDialog.IntInput)
        if not await async_dialog_exec(dialog):
            raise CommandCanceled
        return cast(int, dialog.intValue()) - 1

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-t",
            "--target",
            help="subtitles to move",
            type=lambda value: SubtitlesSelection(api, value),
            default="selected",
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--above",
            dest="method",
            action="store_const",
            const="above",
            help="move subtitles up",
        )
        group.add_argument(
            "--below",
            dest="method",
            action="store_const",
            const="below",
            help="move subtitles down",
        )
        group.add_argument(
            "--gui",
            dest="method",
            action="store_const",
            const="gui",
            help="prompt user for placement position with a GUI dialog",
        )


COMMANDS = [SubtitlesMoveCommand]
