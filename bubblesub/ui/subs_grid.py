import bubblesub.util
from PyQt5 import QtCore
from PyQt5 import QtWidgets


class SubsGridModel(QtCore.QAbstractTableModel):
    def __init__(self, subtitles):
        super().__init__()
        self._subtitles = subtitles
        self._subtitles.item_changed.connect(self._proxy_data_changed)
        self._subtitles.items_inserted.connect(self._proxy_items_inserted)
        self._subtitles.items_removed.connect(self._proxy_items_removed)
        self._header_labels = [
            'Start time',
            'End time',
            'Style',
            'Actor',
            'Text',
            'Duration',
            'CPS']

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole \
                and orientation == QtCore.Qt.Horizontal:
            return self._header_labels[section]
        return super().headerData(section, orientation, role)

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._subtitles)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self._header_labels)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            subtitle = self._subtitles[index.row()]
            column = index.column()
            if column == 0:
                return bubblesub.util.ms_to_str(subtitle.start)
            elif column == 1:
                return bubblesub.util.ms_to_str(subtitle.end)
            elif column == 2:
                return subtitle.style
            elif column == 3:
                return subtitle.actor
            elif column == 4:
                return bubblesub.util.ass_to_plaintext(subtitle.text, True)
            elif column == 5:
                return '{:.1f}'.format(subtitle.duration / 1000.0)
            elif column == 6:
                return (
                    '{:.0f}'.format(
                        bubblesub.util.character_count(subtitle.text) /
                        (subtitle.duration / 1000.0))
                    if subtitle.duration > 0
                    else '-')
        return QtCore.QVariant()

    def flags(self, index):
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
        self.setModel(SubsGridModel(api.subs.lines))
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

    def _widget_selection_changed(self, selected, deselected):
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
            self.scrollTo(self.model().index(self._api.subs.selected_lines[0], 0))
