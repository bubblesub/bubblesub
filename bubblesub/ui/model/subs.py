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
from dataclasses import dataclass

from PyQt5 import QtCore
from PyQt5 import QtGui

from bubblesub.api import Api
from bubblesub.ass.event import Event
from bubblesub.ass.util import character_count
from bubblesub.opt.general import SubtitlesModelColumn
from bubblesub.ui.model.proxy import ObservableListTableAdapter
from bubblesub.ui.util import get_color, blend_colors
from bubblesub.util import ms_to_str, str_to_ms


@dataclass
class SubtitlesModelOptions:
    convert_newlines: bool = False
    editable: bool = False


def _getattr_proxy(
        prop_name: str, wrapper: T.Callable[[T.Any], T.Any],
) -> T.Callable[[Event, SubtitlesModelOptions], T.Any]:
    def func(subtitle: Event, _options: SubtitlesModelOptions) -> T.Any:
        return wrapper(getattr(subtitle, prop_name))

    return func


def _setattr_proxy(
        prop_name: str, wrapper: T.Callable[[T.Any], T.Any],
) -> T.Callable[[Event, SubtitlesModelOptions, T.Any], None]:
    def func(
            subtitle: Event, _options: SubtitlesModelOptions, value: T.Any
    ) -> None:
        setattr(subtitle, prop_name, wrapper(value))

    return func


def _serialize_text(subtitle: Event, options: SubtitlesModelOptions) -> T.Any:
    if options.convert_newlines:
        return subtitle.text.replace('\\N', '\n')
    return subtitle.text


def _serialize_note(subtitle: Event, options: SubtitlesModelOptions) -> T.Any:
    if options.convert_newlines:
        return subtitle.note.replace('\\N', '\n')
    return subtitle.note


def _serialize_cps(subtitle: Event, _options: SubtitlesModelOptions) -> T.Any:
    return (
        '{:.1f}'.format(
            character_count(subtitle.text) /
            max(1, subtitle.duration / 1000.0)
        )
        if subtitle.duration > 0 else
        '-'
    )


def _serialize_short_duration(
        subtitle: Event, _options: SubtitlesModelOptions
) -> T.Any:
    return f'{subtitle.duration / 1000.0:.1f}'


def _deserialize_long_duration(
        subtitle: Event, _options: SubtitlesModelOptions, value: str
) -> T.Any:
    subtitle.end = subtitle.start + str_to_ms(value)


_HEADERS = {
    SubtitlesModelColumn.Start: 'Start',
    SubtitlesModelColumn.End: 'End',
    SubtitlesModelColumn.Style: 'Style',
    SubtitlesModelColumn.Actor: 'Actor',
    SubtitlesModelColumn.Text: 'Text',
    SubtitlesModelColumn.Note: 'Note',
    SubtitlesModelColumn.ShortDuration: 'Duration',
    SubtitlesModelColumn.LongDuration: 'Duration (long)',
    SubtitlesModelColumn.CharsPerSec: 'CPS',
    SubtitlesModelColumn.Layer: 'Layer',
    SubtitlesModelColumn.MarginVertical: 'Vertical margin',
    SubtitlesModelColumn.MarginLeft: 'Left margin',
    SubtitlesModelColumn.MarginRight: 'Right margin',
    SubtitlesModelColumn.IsComment: 'Is comment?',

}

_READER_MAP = {
    SubtitlesModelColumn.Start: _getattr_proxy('start', ms_to_str),
    SubtitlesModelColumn.End: _getattr_proxy('end', ms_to_str),
    SubtitlesModelColumn.Style: _getattr_proxy('style', str),
    SubtitlesModelColumn.Actor: _getattr_proxy('actor', str),
    SubtitlesModelColumn.Text: _serialize_text,
    SubtitlesModelColumn.Note: _serialize_note,
    SubtitlesModelColumn.ShortDuration: _serialize_short_duration,
    SubtitlesModelColumn.LongDuration: _getattr_proxy('duration', ms_to_str),
    SubtitlesModelColumn.CharsPerSec: _serialize_cps,
    SubtitlesModelColumn.Layer: _getattr_proxy('layer', int),
    SubtitlesModelColumn.MarginLeft: _getattr_proxy('margin_left', int),
    SubtitlesModelColumn.MarginRight: _getattr_proxy('margin_right', int),
    SubtitlesModelColumn.MarginVertical:
        _getattr_proxy('margin_vertical', int),
    SubtitlesModelColumn.IsComment: _getattr_proxy('is_comment', bool),
}

_WRITER_MAP = {
    SubtitlesModelColumn.Start: _setattr_proxy('start', str_to_ms),
    SubtitlesModelColumn.End: _setattr_proxy('end', str_to_ms),
    SubtitlesModelColumn.Style: _setattr_proxy('style', str),
    SubtitlesModelColumn.Actor: _setattr_proxy('actor', str),
    SubtitlesModelColumn.Text: _setattr_proxy('text', str),
    SubtitlesModelColumn.Note: _setattr_proxy('note', str),
    SubtitlesModelColumn.LongDuration: _deserialize_long_duration,
    SubtitlesModelColumn.Layer: _setattr_proxy('layer', int),
    SubtitlesModelColumn.MarginLeft: _setattr_proxy('margin_left', int),
    SubtitlesModelColumn.MarginRight: _setattr_proxy('margin_right', int),
    SubtitlesModelColumn.MarginVertical:
        _setattr_proxy('margin_vertical', int),
    SubtitlesModelColumn.IsComment: _setattr_proxy('is_comment', bool),
}


class SubtitlesModel(ObservableListTableAdapter):
    def __init__(
            self, parent: QtCore.QObject, api: Api, **kwargs: T.Any,
    ) -> None:
        super().__init__(parent, api.subs.events)
        self._options = SubtitlesModelOptions(**kwargs)
        self._api = api

    def headerData(
            self,
            idx: int,
            orientation: int,
            role: int = QtCore.Qt.DisplayRole,
    ) -> T.Any:
        if orientation == QtCore.Qt.Vertical:
            if role == QtCore.Qt.DisplayRole:
                return idx + 1
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignRight

        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return _HEADERS[SubtitlesModelColumn(idx)]
            if role == QtCore.Qt.TextAlignmentRole:
                if idx in {
                        SubtitlesModelColumn.Text,
                        SubtitlesModelColumn.Note,
                }:
                    return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
                return QtCore.Qt.AlignCenter

        return QtCore.QVariant()

    def flags(self, _index: QtCore.QModelIndex) -> int:
        ret = QtCore.Qt.ItemIsEnabled
        ret |= QtCore.Qt.ItemIsSelectable
        if self._options.editable:
            ret |= QtCore.Qt.ItemIsEditable
        return T.cast(int, ret)

    @property
    def _column_count(self) -> int:
        return len(SubtitlesModelColumn)

    def _get_data(self, row_idx: int, col_idx: int, role: int) -> T.Any:
        subtitle = self._list[row_idx]

        if role == QtCore.Qt.BackgroundRole:
            if subtitle.is_comment:
                return get_color(self._api, 'grid/comment')
            if col_idx == SubtitlesModelColumn.CharsPerSec:
                return self._get_background_cps(subtitle)

        if role == QtCore.Qt.TextAlignmentRole:
            if col_idx in {
                    SubtitlesModelColumn.Text,
                    SubtitlesModelColumn.Note,
            }:
                return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
            return QtCore.Qt.AlignCenter

        if role in {QtCore.Qt.DisplayRole, QtCore.Qt.EditRole}:
            reader = _READER_MAP[SubtitlesModelColumn(col_idx)]
            return reader(subtitle, self._options)

        return QtCore.QVariant()

    def _set_data(
            self, row_idx: int, col_idx: int, role: int, new_value: T.Any
    ) -> bool:
        subtitle = self._list[row_idx]
        try:
            writer = _WRITER_MAP[SubtitlesModelColumn(col_idx)]
        except KeyError:
            return False
        writer(subtitle, self._options, new_value)
        return True

    def _get_background_cps(self, subtitle: Event) -> T.Any:
        if subtitle.duration == 0:
            return QtCore.QVariant()

        ratio = (
            character_count(subtitle.text) /
            (abs(subtitle.duration) / 1000.0)
        )
        character_limit = self._api.opt.general.subs.max_characters_per_second

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
