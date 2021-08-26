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
from bubblesub.api.cmd import BaseCommand, CommandUnavailable
from bubblesub.cmd.common import SubtitlesSelection
from bubblesub.util import make_ranges


class SubtitlesDeleteCommand(BaseCommand):
    names = ["sub-delete"]
    help_text = "Deletes given subtitles."

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        with self.api.undo.capture():
            indexes = await self.args.target.get_indexes()
            if not indexes:
                raise CommandUnavailable("nothing to delete")

            for start_idx, count in make_ranges(indexes, reverse=True):
                del self.api.subs.events[start_idx : start_idx + count]

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-t",
            "--target",
            help="subtitles to delete",
            type=lambda value: SubtitlesSelection(api, value),
            default="selected",
        )


COMMANDS = [SubtitlesDeleteCommand]
