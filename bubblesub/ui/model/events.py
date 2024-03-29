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
from dataclasses import dataclass
from typing import Any, cast

from ass_parser import AssEvent
from PyQt5.QtCore import QModelIndex, QObject, Qt, QVariant
from PyQt5.QtGui import QColor

from bubblesub.api import Api
from bubblesub.ass_util import character_count
from bubblesub.ui.model.proxy import ObservableListTableAdapter
from bubblesub.ui.themes import ThemeManager
from bubblesub.ui.util import blend_colors
from bubblesub.util import ms_to_str


class AssEventsModelColumn(enum.IntEnum):
    """Column indices in subtitles grid."""

    START = 0
    END = 1
    ASS_STYLE = 2
    ACTOR = 3
    TEXT = 4
    NOTE = 5
    SHORT_DURATION = 6
    LONG_DURATION = 7
    CHARS_PER_SEC = 8
    LAYER = 9
    MARGIN_VERTICAL = 10
    MARGIN_LEFT = 11
    MARGIN_RIGHT = 12
    IS_COMMENT = 13


@dataclass
class AssEventsModelOptions:
    editable: bool = False


class _Column:
    editable = True

    def __init__(self, header: str) -> None:
        self.header = header

    def display(self, sub: AssEvent) -> Any:
        raise NotImplementedError("not implemented")

    def read(self, sub: AssEvent) -> Any:
        raise NotImplementedError("not implemented")

    def write(self, sub: AssEvent, value: Any) -> Any:
        raise NotImplementedError("not implemented")


class _PropertyColumn(_Column):
    def __init__(self, header: str, property_name: str) -> None:
        super().__init__(header)
        self._property_name = property_name

    def display(self, sub: AssEvent) -> Any:
        return getattr(sub, self._property_name)

    def read(self, sub: AssEvent) -> Any:
        return getattr(sub, self._property_name)

    def write(self, sub: AssEvent, value: Any) -> Any:
        setattr(sub, self._property_name, value)


class _BoolPropertyColumn(_PropertyColumn):
    def write(self, sub: AssEvent, value: Any) -> Any:
        setattr(sub, self._property_name, bool(value))


class _IntPropertyColumn(_PropertyColumn):
    def write(self, sub: AssEvent, value: Any) -> Any:
        setattr(sub, self._property_name, int(value))


class _TextPropertyColumn(_PropertyColumn):
    def display(self, sub: AssEvent) -> Any:
        ret = getattr(sub, self._property_name)
        ret = ret.replace("\n", "\\N")
        return ret

    def read(self, sub: AssEvent) -> Any:
        ret = getattr(sub, self._property_name)
        ret = ret.replace("\\N", "\n")
        return ret

    def write(self, sub: AssEvent, value: Any) -> Any:
        value = value.replace("\n", "\\N")
        setattr(sub, self._property_name, value)


class _TimePropertyColumn(_PropertyColumn):
    def display(self, sub: AssEvent) -> Any:
        return ms_to_str(getattr(sub, self._property_name))

    def read(self, sub: AssEvent) -> Any:
        return getattr(sub, self._property_name)

    def write(self, sub: AssEvent, value: Any) -> Any:
        setattr(sub, self._property_name, int(value))


class _CpsColumn(_Column):
    editable = False

    def __init__(self) -> None:
        super().__init__("CPS")

    def display(self, sub: AssEvent) -> Any:
        return (
            "{:.1f}".format(
                character_count(sub.text) / max(1, sub.duration / 1000.0)
            )
            if sub.duration > 0
            else "-"
        )

    def read(self, sub: AssEvent) -> Any:
        raise NotImplementedError("not implemented")

    def write(self, sub: AssEvent, value: Any) -> Any:
        raise NotImplementedError("not implemented")


class _ShortDurationColumn(_IntPropertyColumn):
    def __init__(self) -> None:
        super().__init__("Duration", "duration")

    def display(self, sub: AssEvent) -> Any:
        return f"{sub.duration / 1000.0:.1f}"


class _LongDurationColumn(_IntPropertyColumn):
    def __init__(self) -> None:
        super().__init__("Duration (long)", "duration")

    def display(self, sub: AssEvent) -> Any:
        return ms_to_str(sub.duration)


_COLUMNS: dict[AssEventsModelColumn, _Column] = {
    AssEventsModelColumn.START: _TimePropertyColumn("Start", "start"),
    AssEventsModelColumn.END: _TimePropertyColumn("End", "end"),
    AssEventsModelColumn.ASS_STYLE: _TextPropertyColumn("Style", "style_name"),
    AssEventsModelColumn.ACTOR: _TextPropertyColumn("Actor", "actor"),
    AssEventsModelColumn.TEXT: _TextPropertyColumn("Text", "text"),
    AssEventsModelColumn.NOTE: _TextPropertyColumn("Note", "note"),
    AssEventsModelColumn.SHORT_DURATION: _ShortDurationColumn(),
    AssEventsModelColumn.LONG_DURATION: _LongDurationColumn(),
    AssEventsModelColumn.CHARS_PER_SEC: _CpsColumn(),
    AssEventsModelColumn.LAYER: _IntPropertyColumn("Layer", "layer"),
    AssEventsModelColumn.MARGIN_VERTICAL: _IntPropertyColumn(
        "Vertical margin", "margin_left"
    ),
    AssEventsModelColumn.MARGIN_LEFT: _IntPropertyColumn(
        "Left margin", "margin_vertical"
    ),
    AssEventsModelColumn.MARGIN_RIGHT: _IntPropertyColumn(
        "Right margin", "margin_right"
    ),
    AssEventsModelColumn.IS_COMMENT: _BoolPropertyColumn(
        "Is comment?", "is_comment"
    ),
}


class AssEventsModel(ObservableListTableAdapter[AssEvent]):
    def __init__(
        self,
        api: Api,
        theme_mgr: ThemeManager,
        parent: QObject,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, api.subs.events)
        self._api = api
        self._theme_mgr = theme_mgr
        self._options = AssEventsModelOptions(**kwargs)

    def headerData(
        self,
        idx: int,
        orientation: int,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if orientation == Qt.Orientation.Vertical:
            if role == Qt.ItemDataRole.DisplayRole:
                return idx + 1
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return Qt.AlignmentFlag.AlignRight

        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return _COLUMNS[AssEventsModelColumn(idx)].header
            if role == Qt.ItemDataRole.TextAlignmentRole:
                if idx in {
                    AssEventsModelColumn.TEXT,
                    AssEventsModelColumn.NOTE,
                }:
                    return (
                        Qt.AlignmentFlag.AlignLeft
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                return Qt.AlignmentFlag.AlignCenter

        return QVariant()

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        ret = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if (
            self._options.editable
            and _COLUMNS[AssEventsModelColumn(index.column())].editable
        ):
            ret |= Qt.ItemFlag.ItemIsEditable
        return Qt.ItemFlags(cast(Qt.ItemFlag, ret))

    @property
    def _column_count(self) -> int:
        return len(AssEventsModelColumn)

    def _get_data(self, row_idx: int, col_idx: int, role: int) -> Any:
        subtitle = self._list[row_idx]

        if role == Qt.ItemDataRole.BackgroundRole:
            if subtitle.is_comment:
                return self._theme_mgr.get_color("grid/comment")
            if col_idx == AssEventsModelColumn.CHARS_PER_SEC:
                return self._get_background_cps(subtitle)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col_idx in {
                AssEventsModelColumn.TEXT,
                AssEventsModelColumn.NOTE,
            }:
                return (
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
            return Qt.AlignmentFlag.AlignCenter

        if role == Qt.ItemDataRole.DisplayRole:
            column = _COLUMNS[AssEventsModelColumn(col_idx)]
            return column.display(subtitle)

        if role == Qt.ItemDataRole.EditRole:
            column = _COLUMNS[AssEventsModelColumn(col_idx)]
            return column.read(subtitle)

        return QVariant()

    def _set_data(
        self, row_idx: int, col_idx: int, role: int, new_value: Any
    ) -> bool:
        subtitle = self._list[row_idx]
        column = _COLUMNS[AssEventsModelColumn(col_idx)]
        try:
            column.write(subtitle, new_value)
        except NotImplementedError:
            return False
        return True

    def _get_background_cps(self, subtitle: AssEvent) -> Any:
        if subtitle.duration == 0:
            return QVariant()

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
        return QColor(
            blend_colors(
                self.parent().palette().base().color(),
                self.parent().palette().highlight().color(),
                ratio,
            )
        )
