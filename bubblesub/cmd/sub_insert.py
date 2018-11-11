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

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.cmd.common import SubtitlesSelection


class SubtitleInsertCommand(BaseCommand):
    names = ['sub-insert']
    help_text = 'Inserts one empty subtitle.'

    async def run(self) -> None:
        indexes = await self.args.origin.get_indexes()
        if self.args.dir == 'before':
            idx, start, end = self._insert_before(indexes)
        elif self.args.dir == 'after':
            idx, start, end = self._insert_after(indexes)
        else:
            raise AssertionError

        if not self.args.no_align:
            start = self.api.media.video.align_pts_to_near_frame(start)
            end = self.api.media.video.align_pts_to_near_frame(end)

        with self.api.undo.capture():
            self.api.subs.events.insert_one(
                idx, start=start, end=end, style='Default'
            )
            self.api.subs.selected_indexes = [idx]

    def _insert_before(self, indexes: T.List[int]) -> T.Tuple[int, int, int]:
        if indexes:
            idx = indexes[0]
            cur_sub = self.api.subs.events[idx]
            prev_sub = cur_sub.prev
        else:
            idx = 0
            cur_sub = self.api.subs.events.get(0)
            prev_sub = None

        end = cur_sub.start if cur_sub else self._duration
        start = end - self._duration
        if prev_sub and start < prev_sub.end:
            start = min(prev_sub.end, end)
        return idx, start, end

    def _insert_after(self, indexes: T.List[int]) -> T.Tuple[int, int, int]:
        if indexes:
            idx = indexes[-1]
            cur_sub = self.api.subs.events[idx]
            next_sub = cur_sub.next
            idx += 1
        else:
            idx = 0
            cur_sub = None
            next_sub = self.api.subs.events.get(0)

        start = cur_sub.end if cur_sub else 0
        end = start + self._duration
        if next_sub and end > next_sub.start:
            end = max(next_sub.start, start)
        return idx, start, end

    @property
    def _duration(self) -> int:
        return self.api.opt.general.subs.default_duration

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-o',
            '--origin',
            help='where to insert the subtitle',
            type=lambda value: SubtitlesSelection(api, value),
            default='selected',
        )

        parser.add_argument(
            '--no-align',
            help='don\'t realign the subtitle to video frames',
            action='store_true',
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--before',
            dest='dir',
            action='store_const',
            const='before',
            help='insert before origin',
        )
        group.add_argument(
            '--after',
            dest='dir',
            action='store_const',
            const='after',
            help='insert after origin',
        )


COMMANDS = [SubtitleInsertCommand]
