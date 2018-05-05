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

import re
import typing as T

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ui.util
from bubblesub.ui.model.subs import SubsModel, SubsModelColumn
from bubblesub.ui.util import get_color

# ????
MAGIC_MARGIN1 = 3
MAGIC_MARGIN2 = 1
MAGIC_MARGIN3 = 2


class AssSyntaxHighlight(QtGui.QSyntaxHighlighter):
    def __init__(self, api: bubblesub.api.Api, *args: T.Any) -> None:
        super().__init__(*args)
        self._api = api
        self._style_map: T.Dict[str, QtGui.QTextCharFormat] = {}
        self.update_style_map()

    def update_style_map(self) -> None:
        ass_fmt = QtGui.QTextCharFormat()
        ass_fmt.setForeground(get_color(self._api, 'grid/ass-mark'))

        nonprinting_fmt = QtGui.QTextCharFormat()
        # nonprinting_fmt.setFontWeight(QtGui.QFont.Bold)
        nonprinting_fmt.setBackground(
            get_color(self._api, 'grid/non-printing-mark')
        )

        self._style_map = {
            '\N{FULLWIDTH ASTERISK}': ass_fmt,
            '\N{SYMBOL FOR NEWLINE}': nonprinting_fmt,
        }

    def highlightBlock(self, text: str) -> None:
        for regex, fmt in self._style_map.items():
            for match in re.finditer(regex, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class SubsGridDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(parent)
        self._doc = QtGui.QTextDocument(self)
        self._doc.setDocumentMargin(0)  # ?
        self.syntax_highlight = AssSyntaxHighlight(api, self._doc)

    def paint(
            self,
            painter: QtGui.QPainter,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
    ) -> None:
        if option.state & QtWidgets.QStyle.State_Selected:
            super().paint(painter, option, index)
            return

        item = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(item, index)
        self._doc.setPlainText(item.text)
        item.text = ''

        style = option.widget.style()
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, item, painter)

        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()
        ctx.palette.setColor(
            QtGui.QPalette.Text, option.palette.color(QtGui.QPalette.Text)
        )

        text_rect = style.subElementRect(
            QtWidgets.QStyle.SE_ItemViewItemText, option
        )
        doc_height = self._doc.documentLayout().documentSize().height()
        vertical_offset = (text_rect.height() - doc_height) // 2

        painter.save()
        painter.translate(text_rect.topLeft())
        painter.setClipRect(text_rect.translated(-text_rect.topLeft()))
        painter.translate(0, vertical_offset)
        painter.translate(MAGIC_MARGIN1, MAGIC_MARGIN2)
        self._doc.documentLayout().draw(painter, ctx)
        painter.restore()


class SubsGrid(QtWidgets.QTableView):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(parent)
        self._api = api
        self.setModel(SubsModel(self, api))
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setTabKeyNavigation(False)
        self.horizontalHeader().setSectionsMovable(True)
        self.verticalHeader().setDefaultSectionSize(
            self.fontMetrics().height() + MAGIC_MARGIN3
        )

        self._subs_grid_delegate = SubsGridDelegate(self._api, self)
        for column_idx in (SubsModelColumn.Text, SubsModelColumn.Note):
            self.setItemDelegateForColumn(column_idx, self._subs_grid_delegate)
            self.horizontalHeader().setSectionResizeMode(
                column_idx, QtWidgets.QHeaderView.Stretch
            )

        api.subs.loaded.connect(self._on_subs_load)
        api.subs.selection_changed.connect(self._on_api_selection_change)
        self.selectionModel().selectionChanged.connect(
            self._widget_selection_changed
        )

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_menu)
        self.menu = QtWidgets.QMenu(self)
        bubblesub.ui.util.setup_cmd_menu(
            self._api, self.menu, self._api.opt.menu.context
        )

    def restore_grid_columns(self) -> None:
        header = self.horizontalHeader()
        for col in SubsModelColumn:
            header.hideSection(col.value)
        for new_col_idx, col_name in enumerate(
                self._api.opt.general.grid_columns
        ):
            try:
                col = SubsModelColumn[col_name]
            except KeyError:
                print(f'Unknown column "{col_name}"')
            else:
                old_col_idx = header.visualIndex(col.value)
                header.swapSections(old_col_idx, new_col_idx)
                header.showSection(new_col_idx)

    def store_grid_columns(self) -> None:
        header = self.horizontalHeader()
        self._api.opt.general.grid_columns = [
            SubsModelColumn(header.logicalIndex(i)).name
            for i in SubsModelColumn
            if not header.isSectionHidden(i)
        ]

    def keyboardSearch(self, _text: str) -> None:
        pass

    def changeEvent(self, _event: QtCore.QEvent) -> None:
        self.model().wipe_cache()
        self._subs_grid_delegate.syntax_highlight.update_style_map()

    def _open_menu(self, position: QtCore.QPoint) -> None:
        self.menu.exec_(self.viewport().mapToGlobal(position))

    def _collect_rows(self) -> T.List[int]:
        rows = set()
        for index in self.selectionModel().selectedIndexes():
            rows.add(index.row())
        return list(rows)

    def _on_subs_load(self) -> None:
        self.scrollTo(
            self.model().index(0, 0),
            self.EnsureVisible | self.PositionAtTop
        )

    def _widget_selection_changed(
            self,
            _selected: T.List[int],
            _deselected: T.List[int]
    ) -> None:
        if self._collect_rows() != self._api.subs.selected_indexes:
            self._api.subs.selection_changed.disconnect(
                self._on_api_selection_change
            )
            self._api.subs.selected_indexes = self._collect_rows()
            self._api.subs.selection_changed.connect(
                self._on_api_selection_change
            )

    def _on_api_selection_change(
            self,
            _rows: T.List[int],
            _changed: bool
    ) -> None:
        if self._collect_rows() == self._api.subs.selected_indexes:
            return

        self.setUpdatesEnabled(False)

        self.selectionModel().selectionChanged.disconnect(
            self._widget_selection_changed
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
            QtCore.QItemSelectionModel.Rows |
            QtCore.QItemSelectionModel.Current |
            QtCore.QItemSelectionModel.Select
        )

        self.selectionModel().selectionChanged.connect(
            self._widget_selection_changed
        )

        self.setUpdatesEnabled(True)
