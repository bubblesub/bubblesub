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

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.cmd.common import Pts
from bubblesub.ui.views import TargetWidget


class AudioSetSelectionCommand(BaseCommand):
    names = [
        "audio-set-sel",
        "audio-set-selection",
        "spectrogram-set-sel",
        "spectrogram-set-selection",
    ]
    help_text = "Sets the spectrogram selection."

    @property
    def is_enabled(self) -> bool:
        return self.api.gui.is_widget_visible(str(TargetWidget.Spectrogram))

    async def run(self) -> None:
        with self.api.undo.capture():
            start = self.api.audio.view.selection_start
            end = self.api.audio.view.selection_end

            if self.args.start is not None:
                start = await self.args.start.get(
                    origin=start, align_to_near_frame=not self.args.no_align
                )

            if self.args.end is not None:
                end = await self.args.end.get(
                    origin=end, align_to_near_frame=not self.args.no_align
                )

            self.api.audio.view.select(start, end)

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-s",
            "--start",
            help="new start of the selection",
            type=lambda value: Pts(api, value),
        )
        parser.add_argument(
            "-e",
            "--end",
            help="new end of the selection",
            type=lambda value: Pts(api, value),
        )
        parser.add_argument(
            "--no-align",
            help="don't realign selection to video frames",
            action="store_true",
        )


COMMANDS = [AudioSetSelectionCommand]
