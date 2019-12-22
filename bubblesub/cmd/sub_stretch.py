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
import typing as T

from PyQt5 import QtWidgets

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand, CommandCanceled, CommandUnavailable
from bubblesub.cmd.common import Pts, SubtitlesSelection
from bubblesub.fmt.ass.event import AssEvent
from bubblesub.ui.util import time_jump_dialog


class SubtitlesStretchCommand(BaseCommand):
    names = ["sub-stretch"]
    help_text = "Stretches given subtitles to fit between new timestamp range."

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable("nothing to update")

        start = await self.args.start.get(
            align_to_near_frame=not self.args.no_align
        )
        end = await self.args.end.get(
            align_to_near_frame=not self.args.no_align
        )

        # use beginning of dialogues as reference points for both sides of the
        # range, since it makes more sense to align by dialogue start rather
        # than by dialogue end
        old_start = subs[0].start
        old_end = subs[-1].start

        self.api.log.info(str(old_start))
        self.api.log.info(str(old_end))

        def adjust(pts: int) -> int:
            pts = int(
                start
                + (pts - old_start) * (end - start) / (old_end - old_start)
            )
            if not self.args.no_align:
                pts = self.api.video.align_pts_to_near_frame(pts)
            return pts

        with self.api.undo.capture():
            for sub in subs:
                sub.begin_update()
                sub.start = adjust(sub.start)
                sub.end = adjust(sub.end)
                sub.end_update()

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-t",
            "--target",
            help="subtitles to stretch",
            type=lambda value: SubtitlesSelection(api, value),
            default="selected",
        )
        parser.add_argument(
            "--no-align",
            help="don't realign subtitles to video frames",
            action="store_true",
        )
        parser.add_argument(
            "-s",
            "--start",
            help="starting subtitle new start timestamp",
            type=lambda value: Pts(api, value),
            required=True,
        )
        parser.add_argument(
            "-e",
            "--end",
            help="ending subtitle new start timestamp",
            type=lambda value: Pts(api, value),
            required=True,
        )


COMMANDS = [SubtitlesStretchCommand]
