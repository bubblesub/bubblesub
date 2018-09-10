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

import bubblesub.api
from bubblesub.api.cmd import BaseCommand
from bubblesub.api.cmd import CommandUnavailable
from bubblesub.cmd.common import EventSelection


class PlaySubtitleCommand(BaseCommand):
    names = ['play-sub', 'play-subtitle']
    help_text = (
        'Plays given subtitle. If multiple subtitles are selected, plays '
        'a region from the start of the earliest subtitle to the end '
        'of the latest one.'
    )

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded and self.args.target.makes_sense

    async def run(self) -> None:
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable('nothing to play')

        start = min(sub.start for sub in subs)
        end = max(sub.end for sub in subs)
        self.api.media.play(start, end)

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitle to play',
            type=lambda value: EventSelection(api, value),
            default='selected'
        )


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    cmd_api.register_core_command(PlaySubtitleCommand)
