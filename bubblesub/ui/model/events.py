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
from bubblesub.ass.event import AssEvent
from bubblesub.ass.util import character_count
from bubblesub.ui.model.proxy import ObservableListTableAdapter
from bubblesub.ui.util import blend_colors
from bubblesub.util import ms_to_str, str_to_ms


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
    convert_newlines: bool = False
    editable: bool = False


def _getattr_proxy(
    prop_name: str, wrapper: T.Callable[[T.Any], T.Any]
) -> T.Callable[[AssEvent, AssEventsModelOptions], T.Any]:
    def func(subtitle: AssEvent, options: AssEventsModelOptions) -> T.Any:
        return wrapper(getattr(subtitle, prop_name))

    return func


def _setattr_proxy(
    prop_name: str, wrapper: T.Callable[[T.Any], T.Any]
) -> T.Callable[[AssEvent, AssEventsModelOptions, T.Any], None]:
    def func(
        subtitle: AssEvent, options: AssEventsModelOptions, value: T.Any
    ) -> None:
        setattr(subtitle, prop_name, wrapper(value))

    return func


def _serialize_text(
    subtitle: AssEvent, options: AssEventsModelOptions
) -> T.Any:
    if options.convert_newlines:
        return subtitle.text.replace("\\N", "\n")
    return subtitle.text


def _serialize_note(
    subtitle: AssEvent, options: AssEventsModelOptions
) -> T.Any:
    if options.convert_newlines:
        return subtitle.note.replace("\\N", "\n")
    return subtitle.note


def _serialize_cps(
    subtitle: AssEvent, options: AssEventsModelOptions
) -> T.Any:
    return (
        "{:.1f}".format(
            character_count(subtitle.text) / max(1, subtitle.duration / 1000.0)
        )
        if subtitle.duration > 0
        else "-"
    )


def _serialize_short_duration(
    subtitle: AssEvent, options: AssEventsModelOptions
) -> T.Any:
    return f"{subtitle.duration / 1000.0:.1f}"


def _deserialize_long_duration(
    subtitle: AssEvent, options: AssEventsModelOptions, value: str
) -> T.Any:
    subtitle.end = subtitle.start + str_to_ms(value)


_HEADERS = {
    AssEventsModelColumn.Start: "Start",
    AssEventsModelColumn.End: "End",
    AssEventsModelColumn.AssStyle: "Style",
    AssEventsModelColumn.Actor: "Actor",
    AssEventsModelColumn.Text: "Text",
    AssEventsModelColumn.Note: "Note",
    AssEventsModelColumn.ShortDuration: "Duration",
    AssEventsModelColumn.LongDuration: "Duration (long)",
    AssEventsModelColumn.CharsPerSec: "CPS",
    AssEventsModelColumn.Layer: "Layer",
    AssEventsModelColumn.MarginVertical: "Vertical margin",
    AssEventsModelColumn.MarginLeft: "Left margin",
    AssEventsModelColumn.MarginRight: "Right margin",
    AssEventsModelColumn.IsComment: "Is comment?",
}

_READER_MAP = {
    AssEventsModelColumn.Start: _getattr_proxy("start", ms_to_str),
    AssEventsModelColumn.End: _getattr_proxy("end", ms_to_str),
    AssEventsModelColumn.AssStyle: _getattr_proxy("style", str),
    AssEventsModelColumn.Actor: _getattr_proxy("actor", str),
    AssEventsModelColumn.Text: _serialize_text,
    AssEventsModelColumn.Note: _serialize_note,
    AssEventsModelColumn.ShortDuration: _serialize_short_duration,
    AssEventsModelColumn.LongDuration: _getattr_proxy("duration", ms_to_str),
    AssEventsModelColumn.CharsPerSec: _serialize_cps,
    AssEventsModelColumn.Layer: _getattr_proxy("layer", int),
    AssEventsModelColumn.MarginLeft: _getattr_proxy("margin_left", int),
    AssEventsModelColumn.MarginRight: _getattr_proxy("margin_right", int),
    AssEventsModelColumn.MarginVertical: _getattr_proxy(
        "margin_vertical", int
    ),
    AssEventsModelColumn.IsComment: _getattr_proxy("is_comment", bool),
}

_WRITER_MAP = {
    AssEventsModelColumn.Start: _setattr_proxy("start", str_to_ms),
    AssEventsModelColumn.End: _setattr_proxy("end", str_to_ms),
    AssEventsModelColumn.AssStyle: _setattr_proxy("style", str),
    AssEventsModelColumn.Actor: _setattr_proxy("actor", str),
    AssEventsModelColumn.Text: _setattr_proxy("text", str),
    AssEventsModelColumn.Note: _setattr_proxy("note", str),
    AssEventsModelColumn.LongDuration: _deserialize_long_duration,
    AssEventsModelColumn.Layer: _setattr_proxy("layer", int),
    AssEventsModelColumn.MarginLeft: _setattr_proxy("margin_left", int),
    AssEventsModelColumn.MarginRight: _setattr_proxy("margin_right", int),
    AssEventsModelColumn.MarginVertical: _setattr_proxy(
        "margin_vertical", int
    ),
    AssEventsModelColumn.IsComment: _setattr_proxy("is_comment", bool),
}


class AssEventsModel(ObservableListTableAdapter):
    def __init__(
        self, parent: QtCore.QObject, api: Api, **kwargs: T.Any
    ) -> None:
        super().__init__(parent, api.subs.events)
        self._options = AssEventsModelOptions(**kwargs)
        self._api = api

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
                return _HEADERS[AssEventsModelColumn(idx)]
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
        if self._options.editable:
            ret |= QtCore.Qt.ItemIsEditable
        return T.cast(int, ret)

    @property
    def _column_count(self) -> int:
        return len(AssEventsModelColumn)

    def _get_data(self, row_idx: int, col_idx: int, role: int) -> T.Any:
        subtitle = self._list[row_idx]

        if role == QtCore.Qt.BackgroundRole:
            if subtitle.is_comment:
                return self._api.gui.get_color("grid/comment")
            if col_idx == AssEventsModelColumn.CharsPerSec:
                return self._get_background_cps(subtitle)

        if role == QtCore.Qt.TextAlignmentRole:
            if col_idx in {
                AssEventsModelColumn.Text,
                AssEventsModelColumn.Note,
            }:
                return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
            return QtCore.Qt.AlignCenter

        if role in {QtCore.Qt.DisplayRole, QtCore.Qt.EditRole}:
            reader = _READER_MAP[AssEventsModelColumn(col_idx)]
            return reader(subtitle, self._options)

        return QtCore.QVariant()

    def _set_data(
        self, row_idx: int, col_idx: int, role: int, new_value: T.Any
    ) -> bool:
        subtitle = self._list[row_idx]
        try:
            writer = _WRITER_MAP[AssEventsModelColumn(col_idx)]
        except KeyError:
            return False
        writer(subtitle, self._options, new_value)
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
