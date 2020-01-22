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

from PyQt5 import QtWidgets

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.ui.views import TargetWidget, ViewLayout


class _WidgetMode(enum.Enum):
    """Visibility mode for a GUI widget."""

    Show = "show"
    Hide = "hide"
    Toggle = "toggle"


class ShowWidgetCommand(BaseCommand):
    names = ["show-widget"]
    help_text = "Shows given widget."

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        widget = main_window.findChild(
            QtWidgets.QWidget, str(self.args.target),
        )

        run_operation = {
            _WidgetMode.Show: lambda: widget.setVisible(True),
            _WidgetMode.Hide: lambda: widget.setVisible(False),
            _WidgetMode.Toggle: lambda: widget.setVisible(
                not widget.isVisible()
            ),
        }.get(self.args.mode)

        run_operation()

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "target",
            help="which widget to show/hide",
            type=TargetWidget,
            choices=list(TargetWidget),
        )

        parser.add_argument(
            "-m",
            "--mode",
            help="visibility mode for a widget",
            type=_WidgetMode,
            default=_WidgetMode.Toggle,
            choices=list(_WidgetMode),
        )


class ShowViewCommand(BaseCommand):
    names = ["show-view"]
    help_text = "Shows a view."

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        main_window.view_manager.view_layout = self.args.view

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "view",
            help="which view to show",
            type=ViewLayout,
            choices=list(ViewLayout),
        )


COMMANDS = [ShowWidgetCommand, ShowViewCommand]
