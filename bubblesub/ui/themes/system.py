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

import typing as T
from pathlib import Path

from PyQt5 import QtWidgets

from bubblesub.ui.themes.base import BaseTheme
from bubblesub.ui.themes.dark import DarkTheme
from bubblesub.ui.themes.light import LightTheme


class SystemLightTheme(BaseTheme):
    name = "system-light"
    title = "system (with light icons)"

    def apply(self) -> None:
        QtWidgets.QApplication.setStyle("")
        QtWidgets.QApplication.instance().setStyleSheet("")

    @property
    def palette(self) -> T.Dict[str, str]:
        return LightTheme().palette

    def get_icon_path(self, name: str) -> Path:
        return LightTheme().get_icon_path(name)


class SystemDarkTheme(BaseTheme):
    name = "system-dark"
    title = "system (with dark icons)"

    def apply(self) -> None:
        QtWidgets.QApplication.setStyle("")
        QtWidgets.QApplication.instance().setStyleSheet("")

    @property
    def palette(self) -> T.Dict[str, str]:
        return DarkTheme().palette

    def get_icon_path(self, name: str) -> Path:
        return DarkTheme().get_icon_path(name)
