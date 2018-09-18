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


class PlayAudioSelectionCommand(BaseCommand):
    names = [
        'play-audio-sel',
        'play-audio-selection',
        'play-spectrogram-sel',
        'play-spectrogram-selection'
    ]
    help_text = 'Plays a region near the current spectrogram selection.'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded \
            and self.api.media.audio.has_selection

    async def run(self) -> None:
        start = self.api.media.audio.selection_start
        end = self.api.media.audio.selection_end

        if self.args.method == 'start':
            end = start
        elif self.args.method == 'end':
            start = end
        elif self.args.method != 'both':
            raise AssertionError

        if self.args.delta_start:
            start = await self.args.delta_start.get(origin=start)
        if self.args.delta_end:
            end = await self.args.delta_end.get(origin=end)

        self.api.media.play(start, end)

    @staticmethod
    def _decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-ds', '--delta-start',
            help='delta relative to the selection start',
            type=lambda value: Pts(api, value)
        )
        parser.add_argument(
            '-de', '--delta-end',
            help='delta relative to the selection end',
            type=lambda value: Pts(api, value)
        )

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '--start',
            action='store_const',
            dest='method',
            const='start',
            help='play around selection start',
            default='both'
        )
        group.add_argument(
            '--end',
            action='store_const',
            dest='method',
            const='end',
            help='play around selection end'
        )
        group.add_argument(
            '--both',
            action='store_const',
            dest='method',
            const='both',
            help='play around whole selection'
        )


COMMANDS = [PlayAudioSelectionCommand]
