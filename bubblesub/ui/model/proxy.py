import typing as T

from PyQt5 import QtCore

import bubblesub.cache
import bubblesub.model


class ObservableListTableAdapter(QtCore.QAbstractTableModel):
    """Make ObservableList usable as Qt's QAbstractTableModel."""

    def __init__(
            self,
            parent: QtCore.QObject,
            list_: bubblesub.model.ObservableList
    ) -> None:
        """
        Initialize self.

        :param parent: owner object
        :param list_: the list to adapt
        """
        super().__init__(parent)
        self._list = list_
        self._list.item_changed.connect(self._proxy_data_changed)
        self._list.items_inserted.connect(self._proxy_items_inserted)
        self._list.items_removed.connect(self._proxy_items_removed)

    def rowCount(
            self,
            _parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> int:
        """
        Return number of rows.

        :param _parent: unused
        :return: number of rows
        """
        return len(self._list)

    def columnCount(
            self,
            _parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> int:
        """
        Return number of columns.

        :param _parent: unused
        :return: number of columns
        """
        return self._column_count

    def data(
            self,
            index: QtCore.QModelIndex,
            role: int = QtCore.Qt.DisplayRole
    ) -> T.Any:
        """
        Retrieve cell data at the specified position.

        :param index: cell position
        :param role: what kind of information to retrieve
        :return: associated cell data
        """
        row_idx = index.row()
        col_idx = index.column()
        return self._get_data(row_idx, col_idx, role)

    def setData(
            self,
            index: QtCore.QModelIndex,
            value: T.Any,
            role: int = QtCore.Qt.DisplayRole
    ) -> bool:
        """
        Update cell data at the specified position.

        :param index: cell position
        :param value: new associated cell data
        :param role: what kind of information to set
        :return: whether the cell was changed
        """
        if role == QtCore.Qt.EditRole:
            row_idx = index.row()
            col_idx = index.column()
            if row_idx not in range(len(self._list)):
                return False
            return self._set_data(row_idx, col_idx, role, value)
        return False

    def wipe_cache(self, row_idx: T.Optional[int] = None) -> None:
        """
        Delete .data() cache values.

        :param row_idx: row position to delete the cache for
        """
        if row_idx is not None:
            for role in [
                    QtCore.Qt.DisplayRole,
                    QtCore.Qt.EditRole,
                    QtCore.Qt.BackgroundRole,
                    QtCore.Qt.TextAlignmentRole
            ]:
                for col_idx in range(self.columnCount()):
                    # pylint: disable=no-member
                    self._get_data.wipe_cache_at(row_idx, col_idx, role)
                    # pylint: enable=no-member
        else:
            self._get_data.wipe_cache()  # pylint: disable=no-member

    @property
    def _column_count(self) -> int:
        raise NotImplementedError('Not implemented')

    @bubblesub.cache.Memoize
    def _get_data(self, row_idx: int, col_idx: int, role: int) -> T.Any:
        raise NotImplementedError('Not implemented')

    def _set_data(
            self, row_idx: int, col_idx: int, role: int, new_value: T.Any
    ) -> bool:
        raise NotImplementedError('Not implemented')

    def _proxy_data_changed(self, row_idx: int) -> None:
        self.wipe_cache(row_idx)
        # XXX: this causes qt to call .data() for EVERY VISIBLE CELL. really.
        # self.dataChanged.emit(
        #     self.index(row_idx, 0),
        #     self.index(row_idx, self.columnCount() - 1),
        #     [QtCore.Qt.DisplayRole | QtCore.Qt.BackgroundRole]
        # )
        for col_idx in range(self.columnCount()):
            self.dataChanged.emit(
                self.index(row_idx, col_idx),
                self.index(row_idx, col_idx),
                [QtCore.Qt.DisplayRole, QtCore.Qt.BackgroundRole]
            )

    def _proxy_items_inserted(self, row_idx: int, count: int) -> None:
        if count:
            self.wipe_cache()
            self.rowsInserted.emit(
                QtCore.QModelIndex(),
                row_idx, row_idx + count - 1
            )

    def _proxy_items_removed(self, row_idx: int, count: int) -> None:
        if count:
            self.wipe_cache()
            self.rowsRemoved.emit(
                QtCore.QModelIndex(),
                row_idx, row_idx + count - 1
            )
