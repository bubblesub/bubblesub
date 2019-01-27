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

import functools
import re
import typing as T

from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.opt.hotkeys import HotkeyContext
from bubblesub.opt.menu import MenuContext
from bubblesub.ui.menu import setup_cmd_menu
from bubblesub.ui.model.subs import SubtitlesModel, SubtitlesModelColumn

MAGIC_MARGIN = 2  # ????
HIGHLIGHTABLE_CHUNKS = {"\N{FULLWIDTH ASTERISK}", "\\N", "\\h", "\\n"}


class SubtitlesGridDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self._api = api
        self._format = self._create_format()

    def on_palette_change(self) -> None:
        self._format = self._create_format()

    def _create_format(self) -> QtGui.QTextCharFormat:
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(self._api.gui.get_color("grid/ass-mark"))
        return fmt

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        model = self.parent().model()
        text = self._process_text(model.data(index, QtCore.Qt.DisplayRole))
        alignment = model.data(index, QtCore.Qt.TextAlignmentRole)
        background = model.data(index, QtCore.Qt.BackgroundRole)

        painter.save()
        if option.state & QtWidgets.QStyle.State_Selected:
            self._paint_selected(painter, option, text, alignment)
        else:
            self._paint_regular(painter, option, text, alignment, background)
        painter.restore()

    def _process_text(self, text: str) -> str:
        return re.sub("{[^}]+}", "\N{FULLWIDTH ASTERISK}", text)

    def _paint_selected(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        text: str,
        alignment: int,
    ) -> None:
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(option.palette.color(QtGui.QPalette.Highlight))
        painter.drawRect(option.rect)

        painter.setPen(option.palette.color(QtGui.QPalette.HighlightedText))
        painter.drawText(option.rect, alignment, text)

    def _paint_regular(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        text: str,
        alignment: int,
        background: QtGui.QColor,
    ) -> None:
        if not isinstance(background, QtCore.QVariant):
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QBrush(background))
            painter.drawRect(option.rect)

        rect = option.rect
        metrics = painter.fontMetrics()
        regex = "({})".format(
            "|".join(re.escape(sep) for sep in HIGHLIGHTABLE_CHUNKS)
        )

        for chunk in re.split(regex, text):
            painter.setPen(
                self._api.gui.get_color("grid/ass-mark")
                if chunk in HIGHLIGHTABLE_CHUNKS
                else option.palette.color(QtGui.QPalette.Text)
            )

            # chunk = metrics.elidedText(
            #     chunk, QtCore.Qt.ElideRight, rect.width()
            # )

            painter.drawText(rect, alignment, chunk)
            rect = rect.adjusted(metrics.width(chunk), 0, 0, 0)


class SubtitlesGrid(QtWidgets.QTableView):
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self._api = api
        self.setObjectName("subtitles-grid")
        self.setModel(SubtitlesModel(self, api))
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setTabKeyNavigation(False)
        self.horizontalHeader().setSectionsMovable(True)
        self.verticalHeader().setDefaultSectionSize(
            self.fontMetrics().height() + MAGIC_MARGIN
        )

        self._subs_grid_delegate = SubtitlesGridDelegate(self._api, self)
        for col_idx in {SubtitlesModelColumn.Text, SubtitlesModelColumn.Note}:
            self.setItemDelegateForColumn(col_idx, self._subs_grid_delegate)
            self.horizontalHeader().setSectionResizeMode(
                col_idx, QtWidgets.QHeaderView.Stretch
            )
        for col_idx in {
            SubtitlesModelColumn.LongDuration,
            SubtitlesModelColumn.Layer,
            SubtitlesModelColumn.MarginVertical,
            SubtitlesModelColumn.MarginLeft,
            SubtitlesModelColumn.MarginRight,
            SubtitlesModelColumn.IsComment,
        }:
            self.setColumnHidden(col_idx, True)

        self._subs_menu = QtWidgets.QMenu(self)

        api.cmd.commands_loaded.connect(self._rebuild_subs_menu)
        api.gui.quit_confirmed.connect(self._store_grid_columns)
        api.subs.loaded.connect(self._on_subs_load)
        api.subs.selection_changed.connect(self._sync_api_selection_to_video)
        api.subs.selection_changed.connect(self._sync_api_selection_to_grid)
        self.selectionModel().selectionChanged.connect(
            self._sync_grid_selection_to_api
        )

        self._setup_subs_menu()
        self._setup_header_menu()

        self._seek_to: T.Optional[int] = None

        timer = QtCore.QTimer(self)
        timer.setInterval(50)
        timer.timeout.connect(self._sync_sub_selection)
        timer.start()

    def _setup_subs_menu(self) -> None:
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_subs_menu)
        self._rebuild_subs_menu()

    def _rebuild_subs_menu(self) -> None:
        setup_cmd_menu(
            self._api,
            self._subs_menu,
            self._api.opt.menu[MenuContext.SubtitlesGrid],
            HotkeyContext.SubtitlesGrid,
        )

    def _setup_header_menu(self) -> None:
        header = self.horizontalHeader()
        header.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        for column in SubtitlesModelColumn:
            action = QtWidgets.QAction(
                self,
                text=self.model().headerData(column, QtCore.Qt.Horizontal),
                checkable=True,
                checked=not self.isColumnHidden(column),
            )
            action.setData(column)
            action.changed.connect(
                functools.partial(self.toggle_column, action)
            )
            header.addAction(action)

    def toggle_column(self, action: QtWidgets.QAction) -> None:
        column: SubtitlesModelColumn = action.data()
        self.horizontalHeader().setSectionHidden(
            column.value, not action.isChecked()
        )

    def restore_grid_columns(self) -> None:
        header = self.horizontalHeader()
        data = self._api.opt.general.gui.grid_columns
        if data:
            header.restoreState(data)
        for action in header.actions():
            column: SubtitlesModelColumn = action.data()
            action.setChecked(not header.isSectionHidden(column.value))

    def keyboardSearch(self, _text: str) -> None:
        pass

    def changeEvent(self, _event: QtCore.QEvent) -> None:
        self._subs_grid_delegate.on_palette_change()

    def _store_grid_columns(self) -> None:
        self._api.opt.general.gui.grid_columns = (
            self.horizontalHeader().saveState()
        )

    def _sync_sub_selection(self) -> None:
        if (
            self._seek_to is not None
            and self._api.opt.general.video.sync_pos_to_selection
        ):
            self._api.media.is_paused = True
            self._api.media.seek(self._seek_to)
            self._seek_to = None

    def _open_subs_menu(self, position: QtCore.QPoint) -> None:
        self._subs_menu.exec_(self.viewport().mapToGlobal(position))

    def _collect_rows(self) -> T.List[int]:
        rows = set()
        for index in self.selectionModel().selectedIndexes():
            rows.add(index.row())
        return list(rows)

    def _on_subs_load(self) -> None:
        self.scrollTo(
            self.model().index(0, 0), self.EnsureVisible | self.PositionAtTop
        )

    def _sync_grid_selection_to_api(
        self, _selected: T.List[int], _deselected: T.List[int]
    ) -> None:
        rows = self._collect_rows()
        if rows != self._api.subs.selected_indexes:
            self._api.subs.selection_changed.disconnect(
                self._sync_api_selection_to_grid
            )
            self._api.subs.selected_indexes = rows
            self._api.subs.selection_changed.connect(
                self._sync_api_selection_to_grid
            )

    def _sync_api_selection_to_grid(
        self, _rows: T.List[int], _changed: bool
    ) -> None:
        if self._collect_rows() == self._api.subs.selected_indexes:
            return

        self.setUpdatesEnabled(False)

        self.selectionModel().selectionChanged.disconnect(
            self._sync_grid_selection_to_api
        )

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
            QtCore.QItemSelectionModel.Rows
            | QtCore.QItemSelectionModel.Current
            | QtCore.QItemSelectionModel.Select,
        )

        self.selectionModel().selectionChanged.connect(
            self._sync_grid_selection_to_api
        )

        self.setUpdatesEnabled(True)

    def _sync_api_selection_to_video(
        self, rows: T.List[int], _changed: bool
    ) -> None:
        if len(rows) == 1:
            self._seek_to = self._api.subs.events[rows[0]].start
