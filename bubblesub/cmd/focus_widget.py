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

from PyQt5.QtWidgets import QMainWindow, QWidget

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.ui.views import TargetWidget


class FocusWidgetCommand(BaseCommand):
    names = ["focus-widget"]
    help_text = "Focuses given widget."

    @property
    def is_enabled(self) -> bool:
        return self.api.gui.is_widget_visible(self.args.target.value)

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QMainWindow) -> None:
        widget = main_window.findChild(QWidget, str(self.args.target))
        widget.setFocus()
        if self.args.select:
            widget.selectAll()

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "target",
            help="which widget to focus",
            type=TargetWidget,
            choices=list(TargetWidget),
        )
        parser.add_argument(
            "-s",
            "--select",
            help="whether to select the text",
            action="store_true",
        )


COMMANDS = [FocusWidgetCommand]
