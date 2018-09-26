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
from bubblesub.cmd.common import FancyPath
from bubblesub.cmd.common import SubtitlesSelection
from bubblesub.util import ms_to_str


class SaveAudioSampleCommand(BaseCommand):
    names = ['save-audio-sample']
    help_text = (
        'Saves given subtitles to a WAV file. '
        'Prompts user to choose where to save the file to if the path wasn\'t '
        'specified in the command arguments.'
    )

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense \
            and self.api.media.audio.has_audio_source

    async def run(self) -> None:
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable('nothing to sample')

        assert self.api.media.path
        path = await self.args.path.get_save_path(
            file_filter='Waveform Audio File (*.wav)',
            default_file_name='audio-{}-{}..{}.wav'.format(
                self.api.media.path.name,
                ms_to_str(subs[0].start),
                ms_to_str(subs[-1].end)
            )
        )

        pts_ranges = [(sub.start, sub.end) for sub in subs]
        self.api.media.audio.save_wav(path, pts_ranges)
        self.api.log.info(f'saved audio sample to {path}')

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to save audio from',
            type=lambda value: SubtitlesSelection(api, value),
            default='selected'
        )
        parser.add_argument(
            '-p', '--path',
            help='path to save the sample to',
            type=lambda value: FancyPath(api, value),
            default=''
        )


COMMANDS = [SaveAudioSampleCommand]
