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
import typing as T
from copy import copy

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand, CommandUnavailable
from bubblesub.ass.event import Event
from bubblesub.cmd.common import SubtitlesSelection


class SubtitlesCloneCommand(BaseCommand):
    names = ["sub-clone", "sub-duplicate"]
    help_text = (
        "Duplicates given subtitles. Duplicated subtitles "
        "are interleaved with the source subtitles."
    )

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        with self.api.undo.capture(), self.api.gui.throttle_updates():
            indexes = await self.args.target.get_indexes()
            if not indexes:
                raise CommandUnavailable("nothing to clone")

            sub_copies: T.List[Event] = []
            for idx in reversed(indexes):
                sub_copy = copy(self.api.subs.events[idx])
                self.api.subs.events.insert(idx + 1, [sub_copy])
                sub_copies.append(sub_copy)
            self.api.subs.selected_indexes = [sub.index for sub in sub_copies]

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-t",
            "--target",
            help="subtitles to clone",
            type=lambda value: SubtitlesSelection(api, value),
            default="selected",
        )


COMMANDS = [SubtitlesCloneCommand]
