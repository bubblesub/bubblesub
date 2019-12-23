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

from dataclasses import dataclass
from PyQt5 import QtCore, QtGui

from bubblesub.api import Api
from bubblesub.fmt.ass.event import AssEvent
from bubblesub.fmt.ass.util import character_count
from bubblesub.ui.model.proxy import ObservableListTableAdapter
from bubblesub.ui.themes import ThemeManager
from bubblesub.ui.util import blend_colors
from bubblesub.util import ms_to_str


class AssEventsModelColumn(enum.IntEnum):
    """Column indices in subtitles grid."""

    Start = 0
    End = 1
    AssStyle = 2
    Actor = 3
    Text = 4
    Note = 5
    ShortDuration = 6
    LongDuration = 7
    CharsPerSec = 8
    Layer = 9
    MarginVertical = 10
    MarginLeft = 11
    MarginRight = 12
    IsComment = 13


@dataclass
class AssEventsModelOptions:
    editable: bool = False


class _Column:
    editable = True

    def __init__(self, header: str) -> None:
        self.header = header

    def display(self, sub: AssEvent) -> T.Any:
        raise NotImplementedError("not implemented")

    def read(self, sub: AssEvent) -> T.Any:
        raise NotImplementedError("not implemented")

    def write(self, sub: AssEvent, value: T.Any) -> T.Any:
        raise NotImplementedError("not implemented")


class _PropertyColumn(_Column):
    def __init__(self, header: str, property_name: str) -> None:
        super().__init__(header)
        self._property_name = property_name

    def display(self, sub: AssEvent) -> T.Any:
        return getattr(sub, self._property_name)

    def read(self, sub: AssEvent) -> T.Any:
        return getattr(sub, self._property_name)

    def write(self, sub: AssEvent, value: T.Any) -> T.Any:
        setattr(sub, self._property_name, value)


class _BoolPropertyColumn(_PropertyColumn):
    def write(self, sub: AssEvent, value: T.Any) -> T.Any:
        setattr(sub, self._property_name, bool(value))


class _IntPropertyColumn(_PropertyColumn):
    def write(self, sub: AssEvent, value: T.Any) -> T.Any:
        setattr(sub, self._property_name, int(value))


class _TextPropertyColumn(_PropertyColumn):
    def display(self, sub: AssEvent) -> T.Any:
        ret = getattr(sub, self._property_name)
        ret = ret.replace("\n", "\\N")
        return ret

    def read(self, sub: AssEvent) -> T.Any:
        ret = getattr(sub, self._property_name)
        ret = ret.replace("\\N", "\n")
        return ret

    def write(self, sub: AssEvent, value: T.Any) -> T.Any:
        value = value.replace("\n", "\\N")
        setattr(sub, self._property_name, value)


class _TimePropertyColumn(_PropertyColumn):
    def display(self, sub: AssEvent) -> T.Any:
        return ms_to_str(getattr(sub, self._property_name))

    def read(self, sub: AssEvent) -> T.Any:
        return getattr(sub, self._property_name)

    def write(self, sub: AssEvent, value: T.Any) -> T.Any:
        setattr(sub, self._property_name, int(value))


class _CpsColumn(_Column):
    editable = False

    def __init__(self) -> None:
        super().__init__("CPS")

    def display(self, sub: AssEvent) -> T.Any:
        return (
            "{:.1f}".format(
                character_count(sub.text) / max(1, sub.duration / 1000.0)
            )
            if sub.duration > 0
            else "-"
        )

    def read(self, sub: AssEvent) -> T.Any:
        raise NotImplementedError("not implemented")

    def write(self, sub: AssEvent, value: T.Any) -> T.Any:
        raise NotImplementedError("not implemented")


class _ShortDurationColumn(_IntPropertyColumn):
    def __init__(self) -> None:
        super().__init__("Duration", "duration")

    def display(self, sub: AssEvent) -> T.Any:
        return f"{sub.duration / 1000.0:.1f}"


class _LongDurationColumn(_IntPropertyColumn):
    def __init__(self) -> None:
        super().__init__("Duration (long)", "duration")

    def display(self, sub: AssEvent) -> T.Any:
        return ms_to_str(sub.duration)


_COLUMNS: T.Dict[AssEventsModelColumn, _Column] = {
    AssEventsModelColumn.Start: _TimePropertyColumn("Start", "start"),
    AssEventsModelColumn.End: _TimePropertyColumn("End", "end"),
    AssEventsModelColumn.AssStyle: _TextPropertyColumn("Style", "style"),
    AssEventsModelColumn.Actor: _TextPropertyColumn("Actor", "actor"),
    AssEventsModelColumn.Text: _TextPropertyColumn("Text", "text"),
    AssEventsModelColumn.Note: _TextPropertyColumn("Note", "note"),
    AssEventsModelColumn.ShortDuration: _ShortDurationColumn(),
    AssEventsModelColumn.LongDuration: _LongDurationColumn(),
    AssEventsModelColumn.CharsPerSec: _CpsColumn(),
    AssEventsModelColumn.Layer: _IntPropertyColumn("Layer", "layer"),
    AssEventsModelColumn.MarginVertical: _IntPropertyColumn(
        "Vertical margin", "margin_left"
    ),
    AssEventsModelColumn.MarginLeft: _IntPropertyColumn(
        "Left margin", "margin_vertical"
    ),
    AssEventsModelColumn.MarginRight: _IntPropertyColumn(
        "Right margin", "margin_right"
    ),
    AssEventsModelColumn.IsComment: _BoolPropertyColumn(
        "Is comment?", "is_comment"
    ),
}


class AssEventsModel(ObservableListTableAdapter):
    def __init__(
        self,
        api: Api,
        theme_mgr: ThemeManager,
        parent: QtCore.QObject,
        **kwargs: T.Any,
    ) -> None:
        super().__init__(parent, api.subs.events)
        self._api = api
        self._theme_mgr = theme_mgr
        self._options = AssEventsModelOptions(**kwargs)

    def headerData(
        self, idx: int, orientation: int, role: int = QtCore.Qt.DisplayRole
    ) -> T.Any:
        if orientation == QtCore.Qt.Vertical:
            if role == QtCore.Qt.DisplayRole:
                return idx + 1
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignRight

        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return _COLUMNS[AssEventsModelColumn(idx)].header
            if role == QtCore.Qt.TextAlignmentRole:
                if idx in {
                    AssEventsModelColumn.Text,
                    AssEventsModelColumn.Note,
                }:
                    return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
                return QtCore.Qt.AlignCenter

        return QtCore.QVariant()

    def flags(self, index: QtCore.QModelIndex) -> int:
        ret = QtCore.Qt.ItemIsEnabled
        ret |= QtCore.Qt.ItemIsSelectable
        if (
            self._options.editable
            and _COLUMNS[AssEventsModelColumn(index.column())].editable
        ):
            ret |= QtCore.Qt.ItemIsEditable
        return T.cast(int, ret)

    @property
    def _column_count(self) -> int:
        return len(AssEventsModelColumn)

    def _get_data(self, row_idx: int, col_idx: int, role: int) -> T.Any:
        subtitle = self._list[row_idx]

        if role == QtCore.Qt.BackgroundRole:
            if subtitle.is_comment:
                return self._theme_mgr.get_color("grid/comment")
            if col_idx == AssEventsModelColumn.CharsPerSec:
                return self._get_background_cps(subtitle)

        if role == QtCore.Qt.TextAlignmentRole:
            if col_idx in {
                AssEventsModelColumn.Text,
                AssEventsModelColumn.Note,
            }:
                return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
            return QtCore.Qt.AlignCenter

        if role == QtCore.Qt.DisplayRole:
            column = _COLUMNS[AssEventsModelColumn(col_idx)]
            return column.display(subtitle)

        if role == QtCore.Qt.EditRole:
            column = _COLUMNS[AssEventsModelColumn(col_idx)]
            return column.read(subtitle)

        return QtCore.QVariant()

    def _set_data(
        self, row_idx: int, col_idx: int, role: int, new_value: T.Any
    ) -> bool:
        subtitle = self._list[row_idx]
        column = _COLUMNS[AssEventsModelColumn(col_idx)]
        try:
            column.write(subtitle, new_value)
        except NotImplementedError:
            return False
        return True

    def _get_background_cps(self, subtitle: AssEvent) -> T.Any:
        if subtitle.duration == 0:
            return QtCore.QVariant()

        ratio = character_count(subtitle.text) / (
            abs(subtitle.duration) / 1000.0
        )
        character_limit = self._api.cfg.opt["subs"][
            "max_characters_per_second"
        ]

        ratio -= character_limit
        ratio = max(0, ratio)
        ratio /= character_limit
        ratio = min(1, ratio)
        return QtGui.QColor(
            blend_colors(
                self.parent().palette().base().color(),
                self.parent().palette().highlight().color(),
                ratio,
            )
        )
