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
from bubblesub.api.cmd import CommandUnavailable
from bubblesub.cmd.common import SubtitlesSelection


class AudioCommitSelectionCommand(BaseCommand):
    names = [
        'audio-commit-sel',
        'audio-commit-selection',
        'spectrogram-commit-sel',
        'spectrogram-commit-selection'
    ]
    help_text = (
        'Commits the spectrogram selection into given subtitles. '
        'The subtitles start and end times are synced to the '
        'current spectrogram selection boundaries.'
    )

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        with self.api.undo.capture():
            subs = await self.args.target.get_subtitles()
            if not subs:
                raise CommandUnavailable('nothing to update')

            for sub in subs:
                sub.begin_update()
                sub.start = self.api.media.audio.selection_start
                sub.end = self.api.media.audio.selection_end
                sub.end_update()

    @staticmethod
    def _decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to commit selection into',
            type=lambda value: SubtitlesSelection(api, value),
            default='selected'
        )


COMMANDS = [AudioCommitSelectionCommand]
