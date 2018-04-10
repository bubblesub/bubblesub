import enum
import typing as T

from PyQt5 import QtCore
from PyQt5 import QtGui

import bubblesub.ass.util
import bubblesub.util
import bubblesub.ui.util


class SubsModelColumn(enum.Enum):
    Start = 'start'
    End = 'end'
    Style = 'style'
    Actor = 'actor'
    Text = 'text'
    Note = 'note'
    Duration = 'duration'
    CharactersPerSecond = 'cps'


_CACHE_TEXT = 0
_CACHE_CPS_BK = 1

_HEADERS = {
    SubsModelColumn.Start: 'Start',
    SubsModelColumn.End: 'End',
    SubsModelColumn.Style: 'Style',
    SubsModelColumn.Actor: 'Actor',
    SubsModelColumn.Text: 'Text',
    SubsModelColumn.Note: 'Note',
    SubsModelColumn.Duration: 'Duration',
    SubsModelColumn.CharactersPerSecond: 'CPS',
}


class SubsModel(QtCore.QAbstractTableModel):
    def __init__(
            self,
            api: bubblesub.api.Api,
            *args: T.Any,
            **kwargs: T.Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._api = api

        self.column_order = [
            SubsModelColumn(name)
            for name in api.opt.general['grid']['columns']
        ]

        self._subtitles = api.subs.lines
        self._subtitles.item_changed.connect(self._proxy_data_changed)
        self._subtitles.items_inserted.connect(self._proxy_items_inserted)
        self._subtitles.items_removed.connect(self._proxy_items_removed)
        self._cache: T.List[T.List[T.Any]] = []
        self.reset_cache()

        self._character_limit = (
            api.opt.general['subs']['max_characters_per_second'])

    def rowCount(
            self,
            _parent: QtCore.QModelIndex = QtCore.QModelIndex(),
    ) -> int:
        return len(self._subtitles)

    def columnCount(
            self,
            _parent: QtCore.QModelIndex = QtCore.QModelIndex(),
    ) -> int:
        return len(self.column_order)

    def headerData(
            self,
            idx: int,
            orientation: int,
            role: int = QtCore.Qt.DisplayRole,
    ) -> T.Any:
        if orientation == QtCore.Qt.Vertical:
            if role == QtCore.Qt.DisplayRole:
                return idx + 1
            elif role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignRight

        elif orientation == QtCore.Qt.Horizontal:
            column_type = self.column_order[idx]
            if role == QtCore.Qt.DisplayRole:
                return _HEADERS[column_type]
            elif role == QtCore.Qt.TextAlignmentRole:
                if column_type in (SubsModelColumn.Text, SubsModelColumn.Note):
                    return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
                return QtCore.Qt.AlignCenter

        return QtCore.QVariant()

    def data(
            self,
            index: QtCore.QModelIndex,
            role: int = QtCore.Qt.DisplayRole,
    ) -> T.Any:
        if role == QtCore.Qt.DisplayRole:
            row_number = index.row()
            column_number = index.column()
            column_type = self.column_order[column_number]

            data = self._cache[row_number][_CACHE_TEXT]
            if not data:
                subtitle = self._subtitles[row_number]
                data = {
                    SubsModelColumn.Start:
                        bubblesub.util.ms_to_str(subtitle.start),
                    SubsModelColumn.End:
                        bubblesub.util.ms_to_str(subtitle.end),
                    SubsModelColumn.Style:
                        subtitle.style,
                    SubsModelColumn.Actor:
                        subtitle.actor,
                    SubsModelColumn.Text:
                        bubblesub.ass.util.ass_to_plaintext(
                            subtitle.text, True),
                    SubsModelColumn.Note:
                        bubblesub.ass.util.ass_to_plaintext(
                            subtitle.note, True),
                    SubsModelColumn.Duration:
                        '{:.1f}'.format(subtitle.duration / 1000.0),
                    SubsModelColumn.CharactersPerSecond: (
                        '{:.1f}'.format(
                            bubblesub.ass.util.character_count(subtitle.text) /
                            max(1, subtitle.duration / 1000.0))
                        if subtitle.duration > 0
                        else '-')
                }
                self._cache[row_number][_CACHE_TEXT] = data
            return data[column_type]

        elif role == QtCore.Qt.BackgroundRole:
            row_number = index.row()
            column_number = index.column()
            column_type = self.column_order[column_number]

            subtitle = self._subtitles[row_number]
            if subtitle.is_comment:
                return bubblesub.ui.util.get_color(self._api, 'grid/comment')

            if column_type != SubsModelColumn.CharactersPerSecond:
                return QtCore.QVariant()

            data = self._cache[row_number][_CACHE_CPS_BK]
            if not data:
                ratio = (
                    bubblesub.ass.util.character_count(subtitle.text) /
                    max(1, subtitle.duration / 1000.0))
                ratio -= self._character_limit
                ratio = max(0, ratio)
                ratio /= self._character_limit
                ratio = min(1, ratio)
                data = QtGui.QColor(
                    bubblesub.ui.util.blend_colors(
                        self.parent().palette().base().color(),
                        self.parent().palette().highlight().color(),
                        ratio))
                self._cache[row_number][_CACHE_CPS_BK] = data
            return data

        elif role == QtCore.Qt.TextAlignmentRole:
            column_number = index.column()
            column_type = self.column_order[column_number]
            if column_type in (SubsModelColumn.Text, SubsModelColumn.Note):
                return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
            return QtCore.Qt.AlignCenter

        return QtCore.QVariant()

    def flags(self, _index: QtCore.QModelIndex) -> int:
        return T.cast(
            int,
            QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

    def reset_cache(self, idx: T.Optional[int] = None) -> None:
        if idx:
            self._cache[idx] = [None, None]
        else:
            self._cache = [[None, None] for i in range(len(self._subtitles))]

    def _proxy_data_changed(self, idx: int) -> None:
        self.reset_cache(idx)

        # XXX: this causes qt to call .data() for EVERY VISIBLE CELL. really.
        # self.dataChanged.emit(
        #     self.index(idx, 0),
        #     self.index(idx, self.columnCount() - 1),
        #     [QtCore.Qt.DisplayRole | QtCore.Qt.BackgroundRole])
        for i in range(self.columnCount()):
            self.dataChanged.emit(
                self.index(idx, i),
                self.index(idx, i),
                [QtCore.Qt.DisplayRole, QtCore.Qt.BackgroundRole])

    def _proxy_items_inserted(self, idx: int, count: int) -> None:
        self.reset_cache()
        if count:
            self.rowsInserted.emit(QtCore.QModelIndex(), idx, idx + count - 1)

    def _proxy_items_removed(self, idx: int, count: int) -> None:
        self.reset_cache()
        if count:
            self.rowsRemoved.emit(QtCore.QModelIndex(), idx, idx + count - 1)
