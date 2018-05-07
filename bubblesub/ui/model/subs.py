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

from PyQt5 import QtCore
from PyQt5 import QtGui

import bubblesub.api
import bubblesub.ass.event
import bubblesub.ass.util
import bubblesub.cache
import bubblesub.ui.util
import bubblesub.util
from bubblesub.opt.general import SubsModelColumn
from bubblesub.ui.model.proxy import ObservableListTableAdapter


_HEADERS = {
    SubsModelColumn.Start: 'Start',
    SubsModelColumn.End: 'End',
    SubsModelColumn.Style: 'Style',
    SubsModelColumn.Actor: 'Actor',
    SubsModelColumn.Text: 'Text',
    SubsModelColumn.Note: 'Note',
    SubsModelColumn.Duration: 'Duration',
    SubsModelColumn.CharsPerSec: 'CPS',
}


def _get_cps(subtitle: bubblesub.ass.event.Event) -> str:
    return (
        '{:.1f}'.format(
            bubblesub.ass.util.character_count(subtitle.text) /
            max(1, subtitle.duration / 1000.0))
        if subtitle.duration > 0 else
        '-'
    )


_READER_MAP = {
    SubsModelColumn.Start:
        lambda subtitle: bubblesub.util.ms_to_str(subtitle.start),
    SubsModelColumn.End:
        lambda subtitle: bubblesub.util.ms_to_str(subtitle.end),
    SubsModelColumn.Style:
        lambda subtitle: subtitle.style,
    SubsModelColumn.Actor:
        lambda subtitle: subtitle.actor,
    SubsModelColumn.Text:
        lambda subtitle: bubblesub.ass.util.ass_to_plaintext(
            subtitle.text, True),
    SubsModelColumn.Note:
        lambda subtitle: bubblesub.ass.util.ass_to_plaintext(
            subtitle.note, True),
    SubsModelColumn.Duration:
        lambda subtitle: f'{subtitle.duration / 1000.0:.1f}',
    SubsModelColumn.CharsPerSec: _get_cps,
}


class SubsModel(ObservableListTableAdapter):
    def __init__(
            self,
            parent: QtCore.QObject,
            api: bubblesub.api.Api
    ) -> None:
        super().__init__(parent, api.subs.events)
        self._api = api

    def headerData(
            self,
            idx: int,
            orientation: int,
            role: int = QtCore.Qt.DisplayRole
    ) -> T.Any:
        if orientation == QtCore.Qt.Vertical:
            if role == QtCore.Qt.DisplayRole:
                return idx + 1
            elif role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignRight

        elif orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return _HEADERS[SubsModelColumn(idx)]
            elif role == QtCore.Qt.TextAlignmentRole:
                if idx in (SubsModelColumn.Text, SubsModelColumn.Note):
                    return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
                return QtCore.Qt.AlignCenter

        return QtCore.QVariant()

    def flags(self, _index: QtCore.QModelIndex) -> int:
        return T.cast(
            int,
            QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        )

    @property
    def _column_count(self) -> int:
        return len(SubsModelColumn)

    @bubblesub.cache.Memoize
    def _get_data(self, row_idx: int, col_idx: int, role: int) -> T.Any:
        subtitle = self._list[row_idx]

        if role == QtCore.Qt.BackgroundRole:
            if subtitle.is_comment:
                return bubblesub.ui.util.get_color(self._api, 'grid/comment')
            if col_idx == SubsModelColumn.CharsPerSec:
                return self._get_background_cps(subtitle)
            return QtCore.QVariant()

        elif role == QtCore.Qt.TextAlignmentRole:
            if col_idx in {SubsModelColumn.Text, SubsModelColumn.Note}:
                return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
            return QtCore.Qt.AlignCenter

        elif role == QtCore.Qt.DisplayRole:
            return _READER_MAP[SubsModelColumn(col_idx)](subtitle)

        return QtCore.QVariant()

    def _set_data(
            self, row_idx: int, col_idx: int, role: int, new_value: T.Any
    ) -> bool:
        return False

    def _get_background_cps(
            self, subtitle: bubblesub.ass.event.Event
    ) -> T.Any:
        ratio = (
            bubblesub.ass.util.character_count(subtitle.text) /
            max(1, subtitle.duration / 1000.0)
        )
        character_limit = self._api.opt.general.subs.max_characters_per_second

        ratio -= character_limit
        ratio = max(0, ratio)
        ratio /= character_limit
        ratio = min(1, ratio)
        return QtGui.QColor(
            bubblesub.ui.util.blend_colors(
                self.parent().palette().base().color(),
                self.parent().palette().highlight().color(),
                ratio
            )
        )
