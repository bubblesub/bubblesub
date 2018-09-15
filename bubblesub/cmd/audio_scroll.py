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


class AudioScrollCommand(BaseCommand):
    names = ['audio-scroll', 'spectrogram-scroll']
    help_text = (
        'Scrolls the spectrogram horizontally by its width\'s percentage.'
    )

    async def run(self) -> None:
        distance = int(self.args.delta * self.api.media.audio.view_size)
        self.api.media.audio.move_view(distance)

    @staticmethod
    def _decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-d', '--delta',
            help='factor to shift the view by',
            type=float,
            required=True
        )


COMMANDS = [AudioScrollCommand]
