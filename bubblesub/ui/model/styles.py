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
import typing as T

from PyQt5 import QtCore, QtGui

from bubblesub.ass.style import AssColor, AssStyle
from bubblesub.ui.model.proxy import ObservableListTableAdapter


def _serialize_color(color: AssColor) -> QtGui.QColor:
    return QtGui.QColor(color.red, color.green, color.blue, 255 - color.alpha)


def _deserialize_color(color: QtGui.QColor) -> AssColor:
    return AssColor(
        color.red(), color.green(), color.blue(), 255 - color.alpha()
    )


class AssStylesModelColumn(enum.IntEnum):
    Name = 0
    FontName = 1
    FontSize = 2
    Bold = 3
    Italic = 4
    Underline = 5
    StrikeOut = 6
    PrimaryColor = 7
    SecondaryColor = 8
    BackColor = 9
    OutlineColor = 10
    ShadowWidth = 11
    OutlineWidth = 12
    ScaleX = 13
    ScaleY = 14
    Angle = 15
    Spacing = 16
    MarginLeft = 17
    MarginRight = 18
    MarginVertical = 19
    Alignment = 20


def _getattr_proxy(
    prop_name: str, wrapper: T.Callable[[T.Any], T.Any]
) -> T.Callable[[AssStyle], T.Any]:
    def func(style: AssStyle) -> T.Any:
        return wrapper(getattr(style, prop_name))

    return func


def _setattr_proxy(
    prop_name: str, wrapper: T.Callable[[T.Any], T.Any]
) -> T.Callable[[AssStyle, T.Any], None]:
    def func(style: AssStyle, value: T.Any) -> None:
        setattr(style, prop_name, wrapper(value))

    return func


_READER_MAP = {
    AssStylesModelColumn.Name: _getattr_proxy("name", str),
    AssStylesModelColumn.FontName: _getattr_proxy("font_name", str),
    AssStylesModelColumn.FontSize: _getattr_proxy("font_size", int),
    AssStylesModelColumn.Bold: _getattr_proxy("bold", bool),
    AssStylesModelColumn.Italic: _getattr_proxy("italic", bool),
    AssStylesModelColumn.Underline: _getattr_proxy("underline", bool),
    AssStylesModelColumn.StrikeOut: _getattr_proxy("strike_out", bool),
    AssStylesModelColumn.ShadowWidth: _getattr_proxy("shadow", float),
    AssStylesModelColumn.OutlineWidth: _getattr_proxy("outline", float),
    AssStylesModelColumn.ScaleX: _getattr_proxy("scale_x", float),
    AssStylesModelColumn.ScaleY: _getattr_proxy("scale_y", float),
    AssStylesModelColumn.Angle: _getattr_proxy("angle", float),
    AssStylesModelColumn.Spacing: _getattr_proxy("spacing", float),
    AssStylesModelColumn.Alignment: _getattr_proxy("alignment", int),
    AssStylesModelColumn.MarginLeft: _getattr_proxy("margin_left", int),
    AssStylesModelColumn.MarginRight: _getattr_proxy("margin_right", int),
    AssStylesModelColumn.MarginVertical: _getattr_proxy(
        "margin_vertical", int
    ),
    AssStylesModelColumn.PrimaryColor: _getattr_proxy(
        "primary_color", _serialize_color
    ),
    AssStylesModelColumn.SecondaryColor: _getattr_proxy(
        "secondary_color", _serialize_color
    ),
    AssStylesModelColumn.BackColor: _getattr_proxy(
        "back_color", _serialize_color
    ),
    AssStylesModelColumn.OutlineColor: _getattr_proxy(
        "outline_color", _serialize_color
    ),
}

_WRITER_MAP = {
    AssStylesModelColumn.Name: _setattr_proxy("name", str),
    AssStylesModelColumn.FontName: _setattr_proxy("font_name", str),
    AssStylesModelColumn.FontSize: _setattr_proxy("font_size", int),
    AssStylesModelColumn.Bold: _setattr_proxy("bold", bool),
    AssStylesModelColumn.Italic: _setattr_proxy("italic", bool),
    AssStylesModelColumn.Underline: _setattr_proxy("underline", bool),
    AssStylesModelColumn.StrikeOut: _setattr_proxy("strike_out", bool),
    AssStylesModelColumn.ShadowWidth: _setattr_proxy("shadow", float),
    AssStylesModelColumn.OutlineWidth: _setattr_proxy("outline", float),
    AssStylesModelColumn.ScaleX: _setattr_proxy("scale_x", float),
    AssStylesModelColumn.ScaleY: _setattr_proxy("scale_y", float),
    AssStylesModelColumn.Angle: _setattr_proxy("angle", float),
    AssStylesModelColumn.Spacing: _setattr_proxy("spacing", float),
    AssStylesModelColumn.Alignment: _setattr_proxy("alignment", int),
    AssStylesModelColumn.MarginLeft: _setattr_proxy("margin_left", int),
    AssStylesModelColumn.MarginRight: _setattr_proxy("margin_right", int),
    AssStylesModelColumn.MarginVertical: _setattr_proxy(
        "margin_vertical", int
    ),
    AssStylesModelColumn.PrimaryColor: _setattr_proxy(
        "primary_color", _deserialize_color
    ),
    AssStylesModelColumn.SecondaryColor: _setattr_proxy(
        "secondary_color", _deserialize_color
    ),
    AssStylesModelColumn.BackColor: _setattr_proxy(
        "back_color", _deserialize_color
    ),
    AssStylesModelColumn.OutlineColor: _setattr_proxy(
        "outline_color", _deserialize_color
    ),
}


class AssStylesModel(ObservableListTableAdapter):
    def flags(self, index: QtCore.QModelIndex) -> int:
        if index.column() == AssStylesModelColumn.Name:
            return T.cast(
                int, QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            )
        return T.cast(
            int,
            QtCore.Qt.ItemIsEnabled
            | QtCore.Qt.ItemIsSelectable
            | QtCore.Qt.ItemIsEditable,
        )

    @property
    def _column_count(self) -> int:
        return len(AssStylesModelColumn)

    def _get_data(self, row_idx: int, col_idx: int, role: int) -> T.Any:
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            style = self._list[row_idx]
            return _READER_MAP[AssStylesModelColumn(col_idx)](style)
        return QtCore.QVariant()

    def _set_data(
        self, row_idx: int, col_idx: int, role: int, new_value: T.Any
    ) -> bool:
        style = self._list[row_idx]
        try:
            writer = _WRITER_MAP[AssStylesModelColumn(col_idx)]
        except KeyError:
            return False
        writer(style, new_value)
        return True
