import bubblesub.ui.util
from bubblesub.ui.subs_model import SubsModel, SubsModelColumn
from PyQt5 import QtCore
from PyQt5 import QtWidgets


class SubsGrid(QtWidgets.QTableView):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self._api = api
        self.setModel(SubsModel(api, self))
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setTabKeyNavigation(False)
        self.verticalHeader().setDefaultSectionSize(
            self.fontMetrics().height() + 2)

        for i, column_type in enumerate(self.model().column_order):
            if column_type in (SubsModelColumn.Text, SubsModelColumn.Note):
                self.horizontalHeader().setSectionResizeMode(
                    i, QtWidgets.QHeaderView.Stretch)

        api.subs.loaded.connect(self._on_subs_load)
        api.subs.selection_changed.connect(self._on_api_selection_change)
        self.selectionModel().selectionChanged.connect(
            self._widget_selection_changed)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_menu)
        self.menu = QtWidgets.QMenu(self)
        bubblesub.ui.util.setup_cmd_menu(
            self._api, self.menu, self._api.opt.context_menu)

    def keyboardSearch(self, _text):
        pass

    def changeEvent(self, _event):
        self.model().reset_cache()

    def _open_menu(self, position):
        self.menu.exec_(self.viewport().mapToGlobal(position))

    def _collect_rows(self):
        rows = set()
        for index in self.selectionModel().selectedIndexes():
            rows.add(index.row())
        return list(rows)

    def _on_subs_load(self):
        self.scrollTo(
            self.model().index(0, 0),
            self.EnsureVisible | self.PositionAtTop)

    def _widget_selection_changed(self, _selected, _deselected):
        if self._collect_rows() != self._api.subs.selected_indexes:
            self._api.subs.selection_changed.disconnect(
                self._on_api_selection_change)
            self._api.subs.selected_indexes = self._collect_rows()
            self._api.subs.selection_changed.connect(
                self._on_api_selection_change)

    def _on_api_selection_change(self, _rows, _changed):
        if self._collect_rows() == self._api.subs.selected_indexes:
            return

        self.selectionModel().selectionChanged.disconnect(
            self._widget_selection_changed)

        selection = QtCore.QItemSelection()
        for row in self._api.subs.selected_indexes:
            idx = self.model().index(row, 0)
            selection.select(idx, idx)

        self.selectionModel().clear()

        if self._api.subs.selected_indexes:
            first_row = self._api.subs.selected_indexes[0]
            cell_index = self.model().index(first_row, 0)
            self.setCurrentIndex(cell_index)
            self.scrollTo(cell_index)

        self.selectionModel().select(
            selection,
            QtCore.QItemSelectionModel.Rows |
            QtCore.QItemSelectionModel.Current |
            QtCore.QItemSelectionModel.Select)

        self.selectionModel().selectionChanged.connect(
            self._widget_selection_changed)
