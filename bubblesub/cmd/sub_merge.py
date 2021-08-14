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
import enum
import typing as T

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand, CommandUnavailable
from bubblesub.cmd.common import SubtitlesSelection


class SubtitlesMergeSeparator(enum.Enum):
    def __str__(self) -> str:
        return self.value

    NONE = "none"
    SPACE = "space"
    NEWLINE = "newline"


def strip_whitespace(text: str) -> str:
    return text.replace("\\N", "\n").strip()


def merge_text(
    chunks: T.Iterable[str], separator: SubtitlesMergeSeparator
) -> str:
    if separator == SubtitlesMergeSeparator.NONE:
        return "".join(chunks)
    if separator == SubtitlesMergeSeparator.SPACE:
        return " ".join(map(strip_whitespace, chunks))
    if separator == SubtitlesMergeSeparator.NEWLINE:
        return "\n".join(map(strip_whitespace, chunks))
    raise RuntimeError(f'unknown separator separator: "{separator}"')


class SubtitlesMergeCommand(BaseCommand):
    names = ["sub-merge", "sub-join"]
    help_text = "Merges given subtitles together."

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable("nothing to merge")

        if len(subs) == 1:
            if not subs[0].next:
                raise CommandUnavailable("nothing to merge")
            subs.append(subs[0].next)

        with self.api.undo.capture():
            subs[0].begin_update()
            subs[0].end = subs[-1].end
            if self.args.concat:
                subs[0].text = merge_text(
                    (sub.text for sub in subs), separator=self.args.separator
                )
                subs[0].note = merge_text(
                    (sub.note for sub in subs), separator=self.args.separator
                )
            subs[0].end_update()

            idx = subs[0].index
            del self.api.subs.events[idx + 1 : idx + len(subs)]
            self.api.subs.selected_indexes = [idx]

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-t",
            "--target",
            help="subtitles to merge",
            type=lambda value: SubtitlesSelection(api, value),
            default="selected",
        )
        parser.add_argument(
            "--concat",
            "--concatenate",
            help=(
                "merge the subtitles text and notes "
                "(otherwise keep only the first subtitle)"
            ),
            action="store_true",
        )
        parser.add_argument(
            "--separator",
            help=("separator to merge the text with"),
            type=SubtitlesMergeSeparator,
            choices=list(SubtitlesMergeSeparator),
            default=SubtitlesMergeSeparator.NEWLINE,
        )


COMMANDS = [SubtitlesMergeCommand]
