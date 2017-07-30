import enum
import bubblesub.util
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets


class ColumnType(enum.Enum):
    Start = 0
    End = 1
    Style = 2
    Actor = 3
    Text = 4
    Duration = 5
    CharactersPerSecond = 6


_HEADERS = {
    ColumnType.Start: 'Start',
    ColumnType.End: 'End',
    ColumnType.Style: 'Style',
    ColumnType.Actor: 'Actor',
    ColumnType.Text: 'Text',
    ColumnType.Duration: 'Duration',
    ColumnType.CharactersPerSecond: 'CPS',
}


class SubsGridModel(QtCore.QAbstractTableModel):
    def __init__(self, subtitles, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subtitles = subtitles
        self._subtitles.item_changed.connect(self._proxy_data_changed)
        self._subtitles.items_inserted.connect(self._proxy_items_inserted)
        self._subtitles.items_removed.connect(self._proxy_items_removed)
        self._column_order = [
            ColumnType.Start,
            ColumnType.End,
            ColumnType.Style,
            ColumnType.Actor,
            ColumnType.Text,
            ColumnType.Duration,
            ColumnType.CharactersPerSecond,
        ]

        self._header_labels = [
            _HEADERS[column_type] for column_type in self._column_order]

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole \
                and orientation == QtCore.Qt.Horizontal:
            return self._header_labels[section]
        return super().headerData(section, orientation, role)

    def rowCount(self, _parent=QtCore.QModelIndex()):
        return len(self._subtitles)

    def columnCount(self, _parent=QtCore.QModelIndex()):
        return len(self._header_labels)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            column_number = index.column()
            column_type = self._column_order[column_number]
            subtitle = self._subtitles[index.row()]
            if column_type == ColumnType.Start:
                return bubblesub.util.ms_to_str(subtitle.start)
            elif column_type == ColumnType.End:
                return bubblesub.util.ms_to_str(subtitle.end)
            elif column_type == ColumnType.Style:
                return subtitle.style
            elif column_type == ColumnType.Actor:
                return subtitle.actor
            elif column_type == ColumnType.Text:
                return bubblesub.util.ass_to_plaintext(subtitle.text, True)
            elif column_type == ColumnType.Duration:
                return '{:.1f}'.format(subtitle.duration / 1000.0)
            elif column_type == ColumnType.CharactersPerSecond:
                return (
                    '{:.0f}'.format(
                        bubblesub.util.character_count(subtitle.text) /
                        (subtitle.duration / 1000.0))
                    if subtitle.duration > 0
                    else '-')

        return QtCore.QVariant()

    def flags(self, _index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def _proxy_data_changed(self, idx):
        self.dataChanged.emit(
            self.index(idx, 0),
            self.index(idx, len(self._header_labels)),
            [QtCore.Qt.EditRole])

    def _proxy_items_inserted(self, idx, count):
        if count:
            self.rowsInserted.emit(QtCore.QModelIndex(), idx, idx + count - 1)

    def _proxy_items_removed(self, idx, count):
        if count:
            self.rowsRemoved.emit(QtCore.QModelIndex(), idx, idx + count - 1)


class SubsGrid(QtWidgets.QTableView):
    def __init__(self, api):
        super().__init__()
        self._api = api
        self.setModel(SubsGridModel(api.subs.lines, self))
        self.horizontalHeader().setSectionResizeMode(
            4, QtWidgets.QHeaderView.Stretch)
        self.verticalHeader().setDefaultSectionSize(24)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setTabKeyNavigation(False)

        api.subs.selection_changed.connect(self._api_selection_changed)
        self.selectionModel().selectionChanged.connect(
            self._widget_selection_changed)

    def _collect_rows(self):
        rows = set()
        for index in self.selectionModel().selectedIndexes():
            rows.add(index.row())
        return list(rows)

    def _widget_selection_changed(self, _selected, _deselected):
        if self._collect_rows() != self._api.subs.selected_lines:
            self._api.subs.selected_lines = self._collect_rows()

    def _api_selection_changed(self):
        if self._collect_rows() == self._api.subs.selected_lines:
            return

        selection = QtCore.QItemSelection()
        for row in self._api.subs.selected_lines:
            idx = self.model().index(row, 0)
            selection.select(idx, idx)

        self.selectionModel().select(
            selection,
            QtCore.QItemSelectionModel.Clear |
            QtCore.QItemSelectionModel.Rows |
            QtCore.QItemSelectionModel.Select)

        if self._api.subs.selected_lines:
            self.scrollTo(
                self.model().index(self._api.subs.selected_lines[0], 0))
