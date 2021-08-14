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
from copy import copy

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.cmd.common import SubtitlesSelection
from bubblesub.util import make_ranges


class SortStyle(enum.Enum):
    def __str__(self) -> str:
        return self.value

    START = "start"
    END = "end"
    ACTOR = "actor"
    STYLE = "style"
    LAYER = "layer"


class SubtitlesSortCommand(BaseCommand):
    names = ["sub-sort"]
    help_text = "Sorts all subtitles by their start time."

    @property
    def is_enabled(self) -> bool:
        return bool(self.api.subs.events)

    async def run(self) -> None:
        attr_name = {
            SortStyle.START: "start",
            SortStyle.END: "end",
            SortStyle.ACTOR: "actor",
            SortStyle.STYLE: "style_name",
            SortStyle.LAYER: "layer",
        }[self.args.style]
        with self.api.undo.capture(), self.api.gui.throttle_updates():
            indexes = await self.args.target.get_indexes()
            for idx, count in make_ranges(indexes):
                events = self.api.subs.events[idx : idx + count]
                events = sorted(
                    events, key=lambda event: getattr(event, attr_name)
                )
                self.api.subs.events[idx : idx + count] = list(
                    map(copy, events)
                )

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
            "-s",
            "--style",
            help="how to sort the subtitles",
            type=SortStyle,
            choices=list(SortStyle),
            default=SortStyle.START,
        )


COMMANDS = [SubtitlesSortCommand]
