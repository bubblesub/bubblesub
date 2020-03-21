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
from bubblesub.cmd.common import FancyPath, Pts
from bubblesub.util import ms_to_str


class SaveAudioSampleCommand(BaseCommand):
    names = ["save-audio-sample"]
    help_text = "Saves given subtitles to a WAV file."
    help_text_extra = (
        "Prompts user to choose where to save the file to if the path wasn't "
        "specified in the command arguments."
    )

    @property
    def is_enabled(self) -> bool:
        return (
            self.api.audio.current_stream
            and self.api.audio.current_stream.is_ready
        )

    async def run(self) -> None:
        start = await self.args.start.get(align_to_near_frame=False)
        end = await self.args.end.get(align_to_near_frame=False)

        assert self.api.audio.current_stream.path
        path = await self.args.path.get_save_path(
            file_filter="Waveform Audio File (*.wav)",
            default_file_name="audio-{}-{}..{}.wav".format(
                self.api.audio.current_stream.path.name,
                ms_to_str(start),
                ms_to_str(end),
            ),
        )

        self.api.audio.current_stream.save_wav(path, start, end)
        self.api.log.info(f"saved audio sample to {path}")

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-s",
            "--start",
            help="start of the audio sample",
            type=lambda value: Pts(api, value),
            default="a.s",
        )
        parser.add_argument(
            "-e",
            "--end",
            help="end of the audio sample",
            type=lambda value: Pts(api, value),
            default="a.e",
        )
        parser.add_argument(
            "-p",
            "--path",
            help="path to save the sample to",
            type=lambda value: FancyPath(api, value),
            default="",
        )


COMMANDS = [SaveAudioSampleCommand]
