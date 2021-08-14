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
from bubblesub.cmd.common import Pts, SubtitlesSelection


class SubtitlesSetCommand(BaseCommand):
    names = ["sub-set"]
    help_text = "Updates given subtitles parameters."

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable("nothing to update")

        with self.api.undo.capture():
            for sub in subs:
                params = {
                    "text": sub.text,
                    "note": sub.note,
                    "actor": sub.actor,
                    "style": sub.style_name,
                }

                sub.begin_update()

                if self.args.start:
                    sub.start = await self.args.start.get(
                        origin=sub.start,
                        align_to_near_frame=not self.args.no_align,
                    )

                if self.args.end:
                    sub.end = await self.args.end.get(
                        origin=sub.end,
                        align_to_near_frame=not self.args.no_align,
                    )

                if self.args.text is not None:
                    sub.text = self.args.text.format(**params)

                if self.args.note is not None:
                    sub.note = self.args.note.format(**params)

                if self.args.actor is not None:
                    sub.actor = self.args.actor.format(**params)

                if self.args.style is not None:
                    sub.style_name = self.args.style.format(**params)

                if self.args.comment:
                    sub.is_comment = True

                if self.args.no_comment:
                    sub.is_comment = False

                if self.args.layer is not None:
                    sub.layer = self.args.layer

                sub.end_update()

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-t",
            "--target",
            help="subtitles to change",
            type=lambda value: SubtitlesSelection(api, value),
            default="selected",
        )

        parser.add_argument("--text", help="new subtitles text")
        parser.add_argument("--note", help="new subtitles note")
        parser.add_argument("--actor", help="new subtitles actor")
        parser.add_argument("--style", help="new subtitles style")
        parser.add_argument(
            "--comment",
            action="store_true",
            help="mark subtitles as a comment",
        )
        parser.add_argument(
            "--no-comment",
            action="store_true",
            help="mark subtitles as a non-comment",
        )
        parser.add_argument("--layer", help="new subtitles layer", type=int)

        parser.add_argument(
            "-s",
            "--start",
            help="new subtitles start",
            type=lambda value: Pts(api, value),
        )
        parser.add_argument(
            "-e",
            "--end",
            help="new subtitles end",
            type=lambda value: Pts(api, value),
        )
        parser.add_argument(
            "--no-align",
            help="don't realign subtitles to video frames",
            action="store_true",
        )


COMMANDS = [SubtitlesSetCommand]
