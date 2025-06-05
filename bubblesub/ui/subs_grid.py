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

import datetime
import re
from functools import partial
from typing import Optional

from PyQt5.QtCore import (
    QEvent,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QPoint,
    Qt,
    QTimer,
    QVariant,
)
from PyQt5.QtGui import QBrush, QColor, QPainter, QPalette, QTextCharFormat
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QHeaderView,
    QMenu,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QWidget,
)

from bubblesub.api import Api
from bubblesub.cfg.hotkeys import HotkeyContext
from bubblesub.cfg.menu import MenuContext
from bubblesub.ui.menu import setup_menu
from bubblesub.ui.model.events import AssEventsModel, AssEventsModelColumn
from bubblesub.ui.themes import ThemeManager

MAGIC_MARGIN = 2  # ????
HIGHLIGHTABLE_CHUNKS = {"\N{FULLWIDTH ASTERISK}", "\\N", "\\h", "\\n"}
SEEK_THRESHOLD = datetime.timedelta(seconds=0.2)


class SubtitlesGridDelegate(QStyledItemDelegate):
    def __init__(
        self,
        api: Api,
        theme_mgr: ThemeManager,
        parent: QWidget,
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._theme_mgr = theme_mgr
        self._format = self._create_format()

    def on_theme_change(self) -> None:
        self._format = self._create_format()

    def _create_format(self) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(self._theme_mgr.get_color("grid/ass-mark"))
        return fmt

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        model = self.parent().model()
        if not model:
            return
        text = self._process_text(
            model.data(index, Qt.ItemDataRole.DisplayRole)
        )
        alignment = model.data(index, Qt.ItemDataRole.TextAlignmentRole)
        background = model.data(index, Qt.ItemDataRole.BackgroundRole)

        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            self._paint_selected(painter, option, text, alignment)
        else:
            self._paint_regular(painter, option, text, alignment, background)
        painter.restore()

    def _process_text(self, text: str) -> str:
        return re.sub("{[^}]+}", "\N{FULLWIDTH ASTERISK}", text)

    def _paint_selected(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        text: str,
        alignment: int,
    ) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(option.palette.color(QPalette.Highlight))
        painter.drawRect(option.rect)

        painter.setPen(option.palette.color(QPalette.HighlightedText))
        painter.drawText(option.rect, alignment, text)

    def _paint_regular(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        text: str,
        alignment: int,
        background: QColor,
    ) -> None:
        if not isinstance(background, QVariant):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(background))
            painter.drawRect(option.rect)

        rect = option.rect
        metrics = painter.fontMetrics()
        regex = f"({'|'.join(re.escape(sep) for sep in HIGHLIGHTABLE_CHUNKS)})"

        for chunk in re.split(regex, text):
            painter.setPen(
                self._theme_mgr.get_color("grid/ass-mark")
                if chunk in HIGHLIGHTABLE_CHUNKS
                else option.palette.color(QPalette.Text)
            )

            # chunk = metrics.elidedText(
            #     chunk, Qt.ElideRight, rect.width()
            # )

            painter.drawText(rect, alignment, chunk)
            rect = rect.adjusted(metrics.width(chunk), 0, 0, 0)


class SubtitlesGrid(QTableView):
    def __init__(
        self,
        api: Api,
        theme_mgr: ThemeManager,
        parent: QWidget,
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._theme_mgr = theme_mgr
        self.setObjectName("subtitles-grid")
        self.setTabKeyNavigation(False)
        self.horizontalHeader().setSectionsMovable(True)
        self.verticalHeader().setDefaultSectionSize(
            self.fontMetrics().height() + MAGIC_MARGIN
        )

        self._scheduled_seek: Optional[int] = None
        self._last_seek = datetime.datetime.min

        self._timer = QTimer(self)
        self._timer.setInterval(int(SEEK_THRESHOLD.total_seconds()))
        self._timer.timeout.connect(self._execute_scheduled_seek)

        self._subs_grid_delegate = SubtitlesGridDelegate(
            self._api, self._theme_mgr, self
        )

        self._subs_menu = QMenu(self)

        api.cmd.commands_loaded.connect(self._rebuild_subs_menu)
        api.gui.terminated.connect(self._store_grid_columns)
        api.subs.loaded.connect(self._on_subs_load)
        api.subs.selection_changed.connect(self._sync_api_selection_to_video)
        api.subs.selection_changed.connect(self._sync_api_selection_to_grid)

    def _setup_subs_menu(self) -> None:
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_subs_menu)
        self._rebuild_subs_menu()

    def _rebuild_subs_menu(self) -> None:
        setup_menu(
            self._api,
            self._subs_menu,
            self._api.cfg.menu[MenuContext.SUBTITLES_GRID],
            HotkeyContext.SUBTITLES_GRID,
        )

    def _setup_header_menu(self) -> None:
        if not self.model():
            return
        header = self.horizontalHeader()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        for col_idx in [AssEventsModelColumn.TEXT, AssEventsModelColumn.NOTE]:
            self.setItemDelegateForColumn(col_idx, self._subs_grid_delegate)
            self.horizontalHeader().setSectionResizeMode(
                col_idx, QHeaderView.Stretch
            )
        for col_idx in [
            AssEventsModelColumn.LONG_DURATION,
            AssEventsModelColumn.LAYER,
            AssEventsModelColumn.MARGIN_VERTICAL,
            AssEventsModelColumn.MARGIN_LEFT,
            AssEventsModelColumn.MARGIN_RIGHT,
            AssEventsModelColumn.IS_COMMENT,
        ]:
            self.setColumnHidden(col_idx, True)
        for column in AssEventsModelColumn:
            action = QAction(self)
            action.setText(
                self.model().headerData(column, Qt.Orientation.Horizontal)
            )
            action.setCheckable(True)
            action.setChecked(not self.isColumnHidden(column))
            action.setData(column)
            action.changed.connect(partial(self.toggle_column, action))
            header.addAction(action)

    def toggle_column(self, action: QAction) -> None:
        column: AssEventsModelColumn = action.data()
        self.horizontalHeader().setSectionHidden(
            column.value, not action.isChecked()
        )

    def restore_grid_columns(self) -> None:
        header = self.horizontalHeader()
        data = self._api.cfg.opt["gui"]["grid_columns"]
        if data:
            header.restoreState(data)
        for action in header.actions():
            column: AssEventsModelColumn = action.data()
            action.setChecked(not header.isSectionHidden(column.value))

    def keyboardSearch(self, text: str) -> None:
        pass

    def changeEvent(self, event: QEvent) -> None:
        self._subs_grid_delegate.on_theme_change()

    def _store_grid_columns(self) -> None:
        self._api.cfg.opt["gui"]["grid_columns"] = bytes(
            self.horizontalHeader().saveState()
        )

    def _open_subs_menu(self, position: QPoint) -> None:
        self._subs_menu.exec_(self.viewport().mapToGlobal(position))

    def _collect_rows(self) -> list[int]:
        if not self.selectionModel():
            return []
        rows = set()
        for index in self.selectionModel().selectedIndexes():
            rows.add(index.row())
        return list(rows)

    def _on_subs_load(self) -> None:
        self.setModel(AssEventsModel(self._api, self._theme_mgr, self))
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.selectionModel().selectionChanged.connect(
            self._sync_grid_selection_to_api
        )
        self.scrollTo(
            self.model().index(0, 0),
            self.ScrollHint(
                self.ScrollHint.EnsureVisible | self.ScrollHint.PositionAtTop
            ),
        )

        self._setup_subs_menu()
        self._setup_header_menu()

    def _sync_grid_selection_to_api(
        self, selected: list[int], deselected: list[int]
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
        self, rows: list[int], changed: bool
    ) -> None:
        if not self.model():
            return
        if self._collect_rows() == self._api.subs.selected_indexes:
            return
        self.setUpdatesEnabled(False)

        self.selectionModel().selectionChanged.disconnect(
            self._sync_grid_selection_to_api
        )

        selection = QItemSelection()
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
            QItemSelectionModel.SelectionFlag(
                QItemSelectionModel.SelectionFlag.Rows
                | QItemSelectionModel.SelectionFlag.Current
                | QItemSelectionModel.SelectionFlag.Select
            ),
        )

        self.selectionModel().selectionChanged.connect(
            self._sync_grid_selection_to_api
        )

        self.setUpdatesEnabled(True)

    def _sync_api_selection_to_video(
        self, rows: list[int], _changed: bool
    ) -> None:
        if (
            len(rows) == 1
            and self._api.cfg.opt["video"]["sync_pos_to_selection"]
            and self._api.playback.is_ready
        ):
            pts = self._api.subs.events[rows[0]].start
            if (datetime.datetime.now() - self._last_seek) >= SEEK_THRESHOLD:
                self._seek(pts)
            else:
                self._timer.start()
                self._scheduled_seek = pts

    def _execute_scheduled_seek(self) -> None:
        pts = self._scheduled_seek
        if pts is not None:
            self._api.playback.seek(pts)
            self._scheduled_seek = None
        self._timer.stop()

    def _seek(self, pts: int) -> None:
        self._api.playback.is_paused = True
        self._api.playback.seek(pts)
        self._last_seek = datetime.datetime.now()
