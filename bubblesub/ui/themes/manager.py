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

import functools
import re

from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.ui.themes.base import BaseTheme
from bubblesub.ui.themes.system import SystemTheme


class ThemeManager(QtCore.QObject):
    def __init__(self, api: Api, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._api = api
        self._theme: BaseTheme = SystemTheme()

        self.apply_theme(api.cfg.opt["gui"]["current_theme"])

    def apply_theme(self, theme_name: str) -> None:
        if theme_name == self._theme.name:
            return

        theme = next(
            (t for t in BaseTheme.__subclasses__() if t.name == theme_name),
            None,
        )
        if not theme:
            self._api.log.error(f'unknown theme: "{theme_name}"')
            return

        self._theme = theme()
        self._theme.apply()
        self._api.cfg.opt["gui"]["current_theme"] = theme_name
        self.get_color.cache_clear()
        self.parent().update()

    @property
    def current_theme(self) -> BaseTheme:
        return self._theme

    @functools.lru_cache(maxsize=None)
    def get_color(self, color_name: str) -> None:
        if color_name not in self._theme.palette:
            return QtGui.QColor()
        color_name = self._theme.palette[color_name]
        color_value = tuple(
            int(match.group(1), 16)
            for match in re.finditer(
                "([0-9a-fA-F]{2})", color_name.lstrip("#")
            )
        )
        return QtGui.QColor(*color_value)
