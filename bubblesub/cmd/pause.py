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
from bubblesub.cmd.common import BooleanOperation


class PauseCommand(BaseCommand):
    names = ["pause"]
    help_text = "Pauses or unpauses the video playback."

    @property
    def is_enabled(self) -> bool:
        return self.api.playback.is_loaded

    async def run(self) -> None:
        self.api.playback.is_paused = self.args.operation.apply(
            self.api.playback.is_paused
        )

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "operation",
            help="whether to pause the video",
            type=BooleanOperation,
        )


COMMANDS = [PauseCommand]
