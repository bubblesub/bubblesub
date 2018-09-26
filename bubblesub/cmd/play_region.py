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


class PlayRegionCommand(BaseCommand):
    names = ['play-region']
    help_text = 'Seeks to region start and plays audio/video until region end.'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded

    async def run(self) -> None:
        start = await self.args.start.get()
        if self.args.end:
            end = await self.args.end.get()
        else:
            end = None

        self.api.media.play(start, end)

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-s', '--start',
            help='start of region to play',
            type=lambda value: Pts(api, value),
            default='cf',
        )
        parser.add_argument(
            '-e', '--end',
            help='end of region to play',
            type=lambda value: Pts(api, value),
        )


COMMANDS = [PlayRegionCommand]
