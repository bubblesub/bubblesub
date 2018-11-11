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
from copy import copy

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand, CommandUnavailable
from bubblesub.cmd.common import Pts, SubtitlesSelection


class SubtitlesSplitCommand(BaseCommand):
    names = ['sub-split']
    help_text = 'Splits given subtitles at specified time.'

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable('nothing to split')

        split_pos = await self.args.position.get(
            align_to_near_frame=not self.args.no_align
        )

        with self.api.undo.capture(), self.api.gui.throttle_updates():
            for sub in reversed(subs):
                if split_pos < sub.start or split_pos > sub.end:
                    continue
                idx = sub.index
                self.api.subs.events.insert(idx + 1, [copy(sub)])
                self.api.subs.events[idx].end = split_pos
                self.api.subs.events[idx + 1].start = split_pos
                self.api.subs.selected_indexes = [idx, idx + 1]

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-t',
            '--target',
            help='subtitles to split',
            type=lambda value: SubtitlesSelection(api, value),
            default='selected',
        )

        parser.add_argument(
            '--no-align',
            help='don\'t align split position to video frames',
            action='store_true',
        )

        parser.add_argument(
            '-p',
            '--position',
            help='position to split the subtitles at',
            type=lambda value: Pts(api, value),
        )


COMMANDS = [SubtitlesSplitCommand]
