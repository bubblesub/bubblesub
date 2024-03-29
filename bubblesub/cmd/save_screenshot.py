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


class SaveScreenshotCommand(BaseCommand):
    names = ["save-screenshot"]
    help_text = "Makes a screenshot of given video frame."
    help_text_extra = (
        "Prompts user to choose where to save the file to if the path wasn't "
        "specified in the command arguments."
    )

    @property
    def is_enabled(self) -> bool:
        return (
            self.api.video.has_current_stream
            and self.api.video.current_stream.is_ready
        )

    async def run(self) -> None:
        pts = await self.args.pts.get()
        path = await self.args.path.get_save_path(
            file_filter="Portable Network Graphics (*.png)",
            default_file_name="shot-{}-{}.png".format(
                self.api.video.current_stream.path.name, ms_to_str(pts)
            ),
        )

        self.api.video.current_stream.screenshot(
            pts,
            path,
            self.args.include_subs,
            self.args.width,
            self.args.height,
        )
        self.api.log.info(f"saved screenshot to {path}")

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--pts",
            help="which frame to make screenshot of",
            type=lambda value: Pts(api, value),
            default="cf",
        )
        parser.add_argument(
            "-p",
            "--path",
            help="path to save the screenshot to",
            type=lambda value: FancyPath(api, value),
            default="",
        )
        parser.add_argument(
            "-i",
            "--include-subs",
            help='whether to "burn" the subtitles into the screenshot',
            action="store_true",
        )
        parser.add_argument(
            "--width",
            help="width of the screenshot (by default, original video width)",
            type=int,
        )
        parser.add_argument(
            "--height",
            help=(
                "height of the screenshot (by default, original video height)"
            ),
            type=int,
        )
        parser.epilog = (
            "If only either of width or height is given, "
            "the command tries to maintain aspect ratio."
        )


COMMANDS = [SaveScreenshotCommand]
