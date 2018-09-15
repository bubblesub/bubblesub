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
from bubblesub.cmd.common import RelativePts


class SeekCommand(BaseCommand):
    names = ['seek']
    help_text = 'Changes the video playback position to desired place.'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded

    async def run(self) -> None:
        pts = self.api.media.current_pts
        pts = await self.args.delta.apply(pts, align_to_near_frame=True)
        self.api.media.seek(pts, self.args.precise)
        self.api.media.is_paused = True

    @staticmethod
    def _decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-d', '--delta',
            help='amount to seek by',
            type=lambda value: RelativePts(api, value),
            required=True,
        )
        parser.add_argument(
            '-p', '--precise',
            help=(
                'whether to use precise seeking at the expense of performance'
            ),
            action='store_true'
        )


COMMANDS = [SeekCommand]
