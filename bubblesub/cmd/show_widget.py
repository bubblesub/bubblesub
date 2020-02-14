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

from PyQt5 import QtWidgets

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.cmd.common import BooleanOperation
from bubblesub.ui.views import TargetWidget


class VisibilityMode(BooleanOperation):
    YES = ["show"]
    NO = ["hide"]
    TOGGLE = ["toggle"]


class ShowWidgetCommand(BaseCommand):
    names = ["show-widget"]
    help_text = "Shows or hides given widget."

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        widget = main_window.findChild(
            QtWidgets.QWidget, str(self.args.target)
        )
        widget.setVisible(self.args.mode.apply(widget.isVisible()))

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "target",
            help="target widget",
            type=TargetWidget,
            choices=list(TargetWidget),
        )

        parser.add_argument(
            "-m",
            "--mode",
            help="whether to show or hide the widget",
            type=VisibilityMode,
            choices=VisibilityMode.choices(),
            default=VisibilityMode.TOGGLE[0],
        )


COMMANDS = [ShowWidgetCommand]
