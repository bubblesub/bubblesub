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

import re
import weakref
from functools import lru_cache
from typing import Any

from PyQt5.QtCore import QObject
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import QWidget

from bubblesub.api import Api
from bubblesub.ui.themes.base import BaseTheme
from bubblesub.ui.themes.system import SystemLightTheme


class ThemeManager(QObject):
    def __init__(self, api: Api, parent: QWidget) -> None:
        super().__init__(parent)
        self._api = api
        self._theme: BaseTheme = SystemLightTheme()
        self._icons_to_update: dict[Any, str] = {}

        self.apply_theme(api.cfg.opt["gui"]["current_theme"], force=True)

    def apply_theme(self, theme_name: str, force: bool = False) -> None:
        if theme_name == self._theme.name and not force:
            return

        theme = next(
            (t for t in BaseTheme.__subclasses__() if t.name == theme_name),
            None,
        )
        if not theme:
            self._api.log.error(f'unknown theme: "{theme_name}"')
            return

        self.get_color.cache_clear()
        self._theme = theme()
        self._theme.apply()
        self._api.cfg.opt["gui"]["current_theme"] = theme_name
        self.parent().update()

        new_icons_to_update: dict[Any, str] = {}
        for widget_ref, name in self._icons_to_update.items():
            widget = widget_ref()
            if widget is not None:
                widget.setIcon(self.get_icon(name))
                new_icons_to_update[widget_ref] = name
        self._icons_to_update = new_icons_to_update

    @property
    def current_theme(self) -> BaseTheme:
        return self._theme

    @lru_cache(maxsize=None)
    def get_color(self, color_name: str) -> QColor:
        if color_name not in self._theme.palette:
            return QColor()
        color_name = self._theme.palette[color_name]
        color_value = tuple(
            int(match.group(1), 16)
            for match in re.finditer(
                "([0-9a-fA-F]{2})", color_name.lstrip("#")
            )
        )
        return QColor(*color_value)

    def get_icon(self, name: str) -> QIcon:
        return self.current_theme.get_icon(name)

    def set_icon(self, widget: QWidget, name: str) -> None:
        widget.setIcon(self.get_icon(name))
        self._icons_to_update[weakref.ref(widget)] = name
