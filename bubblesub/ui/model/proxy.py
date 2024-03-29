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

from typing import Any, Generic, TypeVar

from ass_parser.observable_sequence_mixin import (
    ObservableSequenceItemInsertionEvent,
    ObservableSequenceItemModificationEvent,
    ObservableSequenceItemRemovalEvent,
    ObservableSequenceMixin,
)
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt

from bubblesub.util import make_ranges

TItem = TypeVar("TItem")


class ObservableListTableAdapter(Generic[TItem], QAbstractTableModel):
    """Make ObservableList usable as Qt's QAbstractTableModel."""

    def __init__(
        self, parent: QObject, list_: ObservableSequenceMixin[TItem]
    ) -> None:
        """Initialize self.

        :param parent: owner object
        :param list_: the list to adapt
        """
        super().__init__(parent)
        self._list = list_
        self._list.items_modified.subscribe(self._proxy_data_changed)
        self._list.items_inserted.subscribe(self._proxy_items_inserted)
        self._list.items_about_to_be_removed.subscribe(
            self._proxy_items_removed
        )

    def rowCount(self, _parent: QModelIndex = QModelIndex()) -> int:
        """Return number of rows.

        :param _parent: unused
        :return: number of rows
        """
        return len(self._list)

    def columnCount(self, _parent: QModelIndex = QModelIndex()) -> int:
        """Return number of columns.

        :param _parent: unused
        :return: number of columns
        """
        return self._column_count

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        """Retrieve cell data at the specified position.

        :param index: cell position
        :param role: what kind of information to retrieve
        :return: associated cell data
        """
        row_idx = index.row()
        col_idx = index.column()
        return self._get_data(row_idx, col_idx, role)

    def setData(
        self,
        index: QModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> bool:
        """Update cell data at the specified position.

        :param index: cell position
        :param value: new associated cell data
        :param role: what kind of information to set
        :return: whether the cell was changed
        """
        if role == Qt.ItemDataRole.EditRole:
            row_idx = index.row()
            col_idx = index.column()
            if row_idx not in range(len(self._list)):
                return False
            return self._set_data(row_idx, col_idx, role, value)
        return False

    @property
    def _column_count(self) -> int:
        raise NotImplementedError("not implemented")

    def _get_data(self, row_idx: int, col_idx: int, role: int) -> Any:
        raise NotImplementedError("not implemented")

    def _set_data(
        self, row_idx: int, col_idx: int, role: int, new_value: Any
    ) -> bool:
        raise NotImplementedError("not implemented")

    def _proxy_data_changed(
        self, event: ObservableSequenceItemModificationEvent
    ) -> None:
        row_idx = event.item.index
        # XXX: this causes qt to call .data() for EVERY VISIBLE CELL. sic.
        # self.dataChanged.emit(
        #     self.index(row_idx, 0),
        #     self.index(row_idx, self.columnCount() - 1),
        #     [Qt.ItemDataRole.DisplayRole | Qt.ItemDataRole.BackgroundRole]
        # )
        for col_idx in range(self.columnCount()):
            self.dataChanged.emit(
                self.index(row_idx, col_idx),
                self.index(row_idx, col_idx),
                [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.BackgroundRole],
            )

    def _proxy_items_inserted(
        self, event: ObservableSequenceItemInsertionEvent
    ) -> None:
        for idx, count in make_ranges(item.index for item in event.items):
            self.rowsInserted.emit(QModelIndex(), idx, idx + count - 1)

    def _proxy_items_removed(
        self, event: ObservableSequenceItemRemovalEvent
    ) -> None:
        for idx, count in make_ranges(item.index for item in event.items):
            self.rowsRemoved.emit(QModelIndex(), idx, idx + count - 1)
