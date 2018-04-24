import enum
import typing as T

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import bubblesub.cache
import bubblesub.ass.event
import bubblesub.ass.util
import bubblesub.ui.util
import bubblesub.util


class SubsModelColumn(enum.Enum):
    Start = 'start'
    End = 'end'
    Style = 'style'
    Actor = 'actor'
    Text = 'text'
    Note = 'note'
    Duration = 'duration'
    CharactersPerSecond = 'cps'


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


class SubtitleTextCache(bubblesub.cache.MemoryCache):
    def __init__(self, api: bubblesub.api.Api) -> None:
        super().__init__()
        self._subtitles = api.subs.lines

    def _real_get(self, index: T.Tuple[int, int]) -> T.Any:
        row, column_type = index
        subtitle = self._subtitles[row]
        if column_type == SubsModelColumn.Start:
            return bubblesub.util.ms_to_str(subtitle.start)
        elif column_type == SubsModelColumn.End:
            return bubblesub.util.ms_to_str(subtitle.end)
        elif column_type == SubsModelColumn.Style:
            return subtitle.style
        elif column_type == SubsModelColumn.Actor:
            return subtitle.actor
        elif column_type == SubsModelColumn.Text:
            return bubblesub.ass.util.ass_to_plaintext(subtitle.text, True)
        elif column_type == SubsModelColumn.Note:
            return bubblesub.ass.util.ass_to_plaintext(subtitle.note, True)
        elif column_type == SubsModelColumn.Duration:
            return '{:.1f}'.format(subtitle.duration / 1000.0)
        elif column_type == SubsModelColumn.CharactersPerSecond:
            return (
                '{:.1f}'.format(
                    bubblesub.ass.util.character_count(
                        subtitle.text) /
                    max(1, subtitle.duration / 1000.0))
                if subtitle.duration > 0 else
                '-'
            )
        raise RuntimeError


class SubtitleBackgroundCache(bubblesub.cache.MemoryCache):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget
    ) -> None:
        super().__init__()
        self._api = api
        self._subtitles = api.subs.lines
        self._parent = parent

    def _real_get(self, index: T.Any) -> T.Any:
        row, column_type = index
        subtitle = self._subtitles[row]

        if subtitle.is_comment:
            return bubblesub.ui.util.get_color(self._api, 'grid/comment')

        if column_type != SubsModelColumn.CharactersPerSecond:
            return QtCore.QVariant()

        ratio = (
            bubblesub.ass.util.character_count(subtitle.text) /
            max(1, subtitle.duration / 1000.0)
        )
        character_limit = (
            self._api.opt.general['subs']['max_characters_per_second']
        )

        ratio -= character_limit
        ratio = max(0, ratio)
        ratio /= character_limit
        ratio = min(1, ratio)
        return QtGui.QColor(
            bubblesub.ui.util.blend_colors(
                self._parent.palette().base().color(),
                self._parent.palette().highlight().color(),
                ratio)
            )


class SubsModel(QtCore.QAbstractTableModel):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self._api = api

        self.column_order = [
            SubsModelColumn(name)
            for name in api.opt.general['grid']['columns']
        ]

        self._subtitles = api.subs.lines
        self._subtitles.item_changed.connect(self._proxy_data_changed)
        self._subtitles.items_inserted.connect(self._proxy_items_inserted)
        self._subtitles.items_removed.connect(self._proxy_items_removed)
        self._text_cache = SubtitleTextCache(api)
        self._background_cache = SubtitleBackgroundCache(api, parent)

    def rowCount(
            self,
            _parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> int:
        return len(self._subtitles)

    def columnCount(
            self,
            _parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> int:
        return len(self.column_order)

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
            role: int = QtCore.Qt.DisplayRole
    ) -> T.Any:
        row_number = index.row()
        column_number = index.column()
        column_type = self.column_order[column_number]

        if role == QtCore.Qt.DisplayRole:
            return self._text_cache[row_number, column_type]

        elif role == QtCore.Qt.BackgroundRole:
            return self._background_cache[row_number, column_type]

        elif role == QtCore.Qt.TextAlignmentRole:
            if column_type in (SubsModelColumn.Text, SubsModelColumn.Note):
                return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
            return QtCore.Qt.AlignCenter

        return QtCore.QVariant()

    def flags(self, _index: QtCore.QModelIndex) -> int:
        return T.cast(
            int,
            QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        )

    def reset_cache(self, idx: T.Optional[int] = None) -> None:
        if idx:
            for col in SubsModelColumn:
                del self._text_cache[idx, col]
                del self._background_cache[idx, col]
        else:
            self._text_cache.wipe()
            self._background_cache.wipe()

    def _proxy_data_changed(self, idx: int) -> None:
        self.reset_cache(idx)

        # XXX: this causes qt to call .data() for EVERY VISIBLE CELL. really.
        # self.dataChanged.emit(
        #     self.index(idx, 0),
        #     self.index(idx, self.columnCount() - 1),
        #     [QtCore.Qt.DisplayRole | QtCore.Qt.BackgroundRole]
        # )
        for i in range(self.columnCount()):
            self.dataChanged.emit(
                self.index(idx, i),
                self.index(idx, i),
                [QtCore.Qt.DisplayRole, QtCore.Qt.BackgroundRole]
            )

    def _proxy_items_inserted(self, idx: int, count: int) -> None:
        self.reset_cache()
        if count:
            self.rowsInserted.emit(QtCore.QModelIndex(), idx, idx + count - 1)

    def _proxy_items_removed(self, idx: int, count: int) -> None:
        self.reset_cache()
        if count:
            self.rowsRemoved.emit(QtCore.QModelIndex(), idx, idx + count - 1)
