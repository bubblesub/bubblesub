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
from bubblesub.ui.views import TargetWidget
from bubblesub.util import eval_expr


class VideoPanCommand(BaseCommand):
    names = ["video-pan"]
    help_text = "Pans the video to specific position."

    @property
    def is_enabled(self) -> bool:
        return self.api.gui.is_widget_visible(str(TargetWidget.Video))

    async def run(self) -> None:
        self.api.video.view.pan = (
            eval_expr(self.args.expr_x.format(self.api.video.view.pan_x)),
            eval_expr(self.args.expr_y.format(self.api.video.view.pan_y)),
        )

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "expr_x", help="expr to calculate new pan x position", type=str
        )
        parser.add_argument(
            "expr_y", help="expr to calculate new pan y position", type=str
        )


COMMANDS = [VideoPanCommand]
