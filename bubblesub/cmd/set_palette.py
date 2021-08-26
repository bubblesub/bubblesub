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

from PyQt5.QtWidgets import QMainWindow

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.ui.themes import BaseTheme


class SetThemeCommand(BaseCommand):
    names = ["set-theme"]
    help_text = "Changes the GUI color theme."

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QMainWindow) -> None:
        main_window.theme_mgr.apply_theme(self.args.theme_name)

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "theme_name",
            help="name of the theme to change to",
            type=str,
            choices=list(
                sorted(cls.name for cls in BaseTheme.__subclasses__())
            ),
        )


COMMANDS = [SetThemeCommand]
