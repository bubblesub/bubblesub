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

import enum
from collections.abc import Callable
from typing import Any, cast

from ass_parser import AssColor, AssStyle
from PyQt5 import QtCore, QtGui

from bubblesub.ui.model.proxy import ObservableListTableAdapter


def _serialize_color(color: AssColor) -> QtGui.QColor:
    return QtGui.QColor(color.red, color.green, color.blue, 255 - color.alpha)


def _deserialize_color(color: QtGui.QColor) -> AssColor:
    return AssColor(
        color.red(), color.green(), color.blue(), 255 - color.alpha()
    )


class AssStylesModelColumn(enum.IntEnum):
    NAME = 0
    FONT_NAME = 1
    FONT_SIZE = 2
    BOLD = 3
    ITALIC = 4
    UNDERLINE = 5
    STRIKE_OUT = 6
    PRIMARY_COLOR = 7
    SECONDARY_COLOR = 8
    BACK_COLOR = 9
    OUTLINE_COLOR = 10
    SHADOW_WIDTH = 11
    OUTLINE_WIDTH = 12
    SCALE_X = 13
    SCALE_Y = 14
    ANGLE = 15
    SPACING = 16
    MARGIN_LEFT = 17
    MARGIN_RIGHT = 18
    MARGIN_VERTICAL = 19
    ALIGNMENT = 20


def _getattr_proxy(
    prop_name: str, wrapper: Callable[[Any], Any]
) -> Callable[[AssStyle], Any]:
    def func(style: AssStyle) -> Any:
        return wrapper(getattr(style, prop_name))

    return func


def _setattr_proxy(
    prop_name: str, wrapper: Callable[[Any], Any]
) -> Callable[[AssStyle, Any], None]:
    def func(style: AssStyle, value: Any) -> None:
        setattr(style, prop_name, wrapper(value))

    return func


_READER_MAP = {
    AssStylesModelColumn.NAME: _getattr_proxy("name", str),
    AssStylesModelColumn.FONT_NAME: _getattr_proxy("font_name", str),
    AssStylesModelColumn.FONT_SIZE: _getattr_proxy("font_size", int),
    AssStylesModelColumn.BOLD: _getattr_proxy("bold", bool),
    AssStylesModelColumn.ITALIC: _getattr_proxy("italic", bool),
    AssStylesModelColumn.UNDERLINE: _getattr_proxy("underline", bool),
    AssStylesModelColumn.STRIKE_OUT: _getattr_proxy("strike_out", bool),
    AssStylesModelColumn.SHADOW_WIDTH: _getattr_proxy("shadow", float),
    AssStylesModelColumn.OUTLINE_WIDTH: _getattr_proxy("outline", float),
    AssStylesModelColumn.SCALE_X: _getattr_proxy("scale_x", float),
    AssStylesModelColumn.SCALE_Y: _getattr_proxy("scale_y", float),
    AssStylesModelColumn.ANGLE: _getattr_proxy("angle", float),
    AssStylesModelColumn.SPACING: _getattr_proxy("spacing", float),
    AssStylesModelColumn.ALIGNMENT: _getattr_proxy("alignment", int),
    AssStylesModelColumn.MARGIN_LEFT: _getattr_proxy("margin_left", int),
    AssStylesModelColumn.MARGIN_RIGHT: _getattr_proxy("margin_right", int),
    AssStylesModelColumn.MARGIN_VERTICAL: _getattr_proxy(
        "margin_vertical", int
    ),
    AssStylesModelColumn.PRIMARY_COLOR: _getattr_proxy(
        "primary_color", _serialize_color
    ),
    AssStylesModelColumn.SECONDARY_COLOR: _getattr_proxy(
        "secondary_color", _serialize_color
    ),
    AssStylesModelColumn.BACK_COLOR: _getattr_proxy(
        "back_color", _serialize_color
    ),
    AssStylesModelColumn.OUTLINE_COLOR: _getattr_proxy(
        "outline_color", _serialize_color
    ),
}

_WRITER_MAP = {
    AssStylesModelColumn.NAME: _setattr_proxy("name", str),
    AssStylesModelColumn.FONT_NAME: _setattr_proxy("font_name", str),
    AssStylesModelColumn.FONT_SIZE: _setattr_proxy("font_size", int),
    AssStylesModelColumn.BOLD: _setattr_proxy("bold", bool),
    AssStylesModelColumn.ITALIC: _setattr_proxy("italic", bool),
    AssStylesModelColumn.UNDERLINE: _setattr_proxy("underline", bool),
    AssStylesModelColumn.STRIKE_OUT: _setattr_proxy("strike_out", bool),
    AssStylesModelColumn.SHADOW_WIDTH: _setattr_proxy("shadow", float),
    AssStylesModelColumn.OUTLINE_WIDTH: _setattr_proxy("outline", float),
    AssStylesModelColumn.SCALE_X: _setattr_proxy("scale_x", float),
    AssStylesModelColumn.SCALE_Y: _setattr_proxy("scale_y", float),
    AssStylesModelColumn.ANGLE: _setattr_proxy("angle", float),
    AssStylesModelColumn.SPACING: _setattr_proxy("spacing", float),
    AssStylesModelColumn.ALIGNMENT: _setattr_proxy("alignment", int),
    AssStylesModelColumn.MARGIN_LEFT: _setattr_proxy("margin_left", int),
    AssStylesModelColumn.MARGIN_RIGHT: _setattr_proxy("margin_right", int),
    AssStylesModelColumn.MARGIN_VERTICAL: _setattr_proxy(
        "margin_vertical", int
    ),
    AssStylesModelColumn.PRIMARY_COLOR: _setattr_proxy(
        "primary_color", _deserialize_color
    ),
    AssStylesModelColumn.SECONDARY_COLOR: _setattr_proxy(
        "secondary_color", _deserialize_color
    ),
    AssStylesModelColumn.BACK_COLOR: _setattr_proxy(
        "back_color", _deserialize_color
    ),
    AssStylesModelColumn.OUTLINE_COLOR: _setattr_proxy(
        "outline_color", _deserialize_color
    ),
}


class AssStylesModel(ObservableListTableAdapter):
    def flags(self, index: QtCore.QModelIndex) -> int:
        if index.column() == AssStylesModelColumn.NAME:
            return cast(
                int, QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            )
        return cast(
            int,
            QtCore.Qt.ItemIsEnabled
            | QtCore.Qt.ItemIsSelectable
            | QtCore.Qt.ItemIsEditable,
        )

    @property
    def _column_count(self) -> int:
        return len(AssStylesModelColumn)

    def _get_data(self, row_idx: int, col_idx: int, role: int) -> Any:
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            style = self._list[row_idx]
            return _READER_MAP[AssStylesModelColumn(col_idx)](style)
        return QtCore.QVariant()

    def _set_data(
        self, row_idx: int, col_idx: int, role: int, new_value: Any
    ) -> bool:
        style = self._list[row_idx]
        try:
            writer = _WRITER_MAP[AssStylesModelColumn(col_idx)]
        except KeyError:
            return False
        writer(style, new_value)
        return True
