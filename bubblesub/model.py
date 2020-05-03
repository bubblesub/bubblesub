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

"""Common containers, decorators, etc."""

import typing as T

from PyQt5 import QtCore

TItem = T.TypeVar("TItem")


class ObservableObject:
    """Class capable of observing changes to its properties."""

    def __init__(self) -> None:
        """Initialize self."""
        self._setattr_impl = self._setattr_normal
        self._dirty = False

    def __setattr__(self, prop: str, new_value: T.Any) -> None:
        """Set attribute.

        Called whenever the user changes any of the class attributes.
        Changes to properties starting with _ won't be tracked.
        Changes to other properties will trigger self._after_change callback.

        :param prop: property name
        :param new_value: new value
        """
        if prop.startswith("_"):
            super().__setattr__(prop, new_value)
        else:
            try:
                old_value = getattr(self, prop)
            except AttributeError:
                super().__setattr__(prop, new_value)
            else:
                if new_value != old_value:
                    self._setattr_impl(prop, new_value)

    def _setattr_normal(self, prop: str, new_value: T.Any) -> None:
        """Regular implementation of attribute setter.

        Calls _before_change and _after_change immediately.

        :param prop: property name
        :param new_value: new value
        """
        self._before_change()
        super().__setattr__(prop, new_value)
        self._after_change()

    def _setattr_throttled(self, prop: str, new_value: T.Any) -> None:
        """Throttled implementation of attribute setter.

        Doesn't call _after_change until after the user calls the .end_update()
        method. Calls before_change if it wasn't called before.

        :param prop: property name
        :param new_value: new value
        """
        if not self._dirty:
            self._before_change()
        super().__setattr__(prop, new_value)
        self._dirty = True

    def begin_update(self) -> None:
        """Start throttling calls to ._after_change() method.

        Useful for batch object updates - rather than having .before_change()
        and .after_change() methods called after every change to the instance
        properties, they're getting called only once, on .begin_update() and
        .end_update(), and only if there was a change to the class properties.
        """
        self._setattr_impl = self._setattr_throttled

    def end_update(self) -> None:
        """Stop throttling calls to ._after_change() method.

        If the object was modified in the meantime, calls ._after_change()
        method only once.
        """
        if self._dirty:
            self._after_change()
        self._setattr_impl = self._setattr_normal
        self._dirty = False

    def _before_change(self) -> None:
        """Meant to be overriden by the user.

        Called before class properties have changed.
        """

    def _after_change(self) -> None:
        """Meant to be overriden by the user.

        Called after class properties have changed.
        """


class _ObservableListSignals(QtCore.QObject):
    # QObject doesn't play nice with multiple inheritance, hence composition
    item_modified = QtCore.pyqtSignal([int])
    items_about_to_be_inserted = QtCore.pyqtSignal([int, int])
    items_about_to_be_removed = QtCore.pyqtSignal([int, int])
    items_about_to_be_moved = QtCore.pyqtSignal([int, int, int])
    items_inserted = QtCore.pyqtSignal([int, int])
    items_removed = QtCore.pyqtSignal([int, int])
    items_moved = QtCore.pyqtSignal([int, int, int])


class ObservableList(T.Generic[TItem]):
    """Alternative to QtCore.QAbstractListModel that simplifies indexing."""

    item_modified = property(lambda self: self._signals.item_modified)
    items_about_to_be_inserted = property(
        lambda self: self._signals.items_about_to_be_inserted
    )
    items_about_to_be_removed = property(
        lambda self: self._signals.items_about_to_be_removed
    )
    items_about_to_be_moved = property(
        lambda self: self._signals.items_about_to_be_moved
    )
    items_inserted = property(lambda self: self._signals.items_inserted)
    items_removed = property(lambda self: self._signals.items_removed)
    items_moved = property(lambda self: self._signals.items_moved)

    def __init__(self) -> None:
        """Initialize self."""
        super().__init__()
        self._signals = _ObservableListSignals()
        self._items: T.List[TItem] = []

    def __getstate__(self) -> T.Any:
        """Return pickle compatible object representation.

        :return: object representation
        """
        return self._items

    def __setstate__(self, state: T.Any) -> None:
        """Load class state from pickle compatible object representation.

        :param state: object representation
        """
        self._items = state

    def __len__(self) -> int:
        """Return how many items the collection contains.

        :return: number of items
        """
        return len(self._items)

    def __bool__(self) -> bool:
        """Return if the collection is empty.

        :return: True, if the collection is empty, False otherwise
        """
        return bool(self._items)

    @T.overload
    def __getitem__(self, idx: slice) -> T.List[TItem]:
        """Retrieve item at given position.

        :param idx: item position
        :return: value at given position
        """
        ...

    @T.overload  # pylint: disable=function-redefined
    def __getitem__(self, idx: int) -> TItem:
        """Retrieve item at given position.

        :param idx: item position
        :return: value at given position
        """
        ...

    def __getitem__(
        self, idx: T.Any
    ) -> T.Any:  # pylint: disable=function-redefined
        """Retrieve item at given position.

        :param idx: item position
        :return: value at given position
        """
        return self._items[idx]

    def __setitem__(self, idx: T.Union[slice, int], value: T.Any) -> None:
        """Set item at given position.

        :param idx: position to modify
        :param value: new value
        """
        if isinstance(idx, slice):
            start, stop, step = idx.indices(len(self._items))
            if step != 1:
                raise RuntimeError(
                    "slice assignment with variable steps is not supported"
                )
            if start < 0 or stop < 0:
                raise RuntimeError(
                    "slice assignment with negative steps is not supported"
                )

            self.items_about_to_be_removed.emit(start, stop - start)
            self.items_about_to_be_inserted.emit(start, len(value))
            self._items[start:stop] = value
            self.items_removed.emit(start, stop - start)
            self.items_inserted.emit(start, len(value))
        else:
            self.items_about_to_be_removed.emit(idx, 1)
            self.items_about_to_be_inserted.emit(idx, 1)
            self._items[idx] = value
            self.items_removed.emit(idx, 1)
            self.items_inserted.emit(idx, 1)

    def __iter__(self) -> T.Iterator[TItem]:
        """Iterate directly over the collection values.

        :return: iterator
        """
        yield from self._items

    def __reversed__(self) -> T.Iterator[TItem]:
        """Iterate over the collection values in a reverse order.

        :return: iterator
        """
        yield from self._items[::-1]

    def get(
        self, idx: int, default: T.Optional[TItem] = None
    ) -> T.Optional[TItem]:
        """Retrieve item at given position.

        :param idx: item's position
        :param default: value to return if position is out of bounds
        :return: value at given position, default if position out of bounds
        """
        if idx < 0 or idx >= len(self):
            return default
        return self._items[idx]

    def index(self, item: TItem) -> T.Optional[int]:
        """Look up item's position in the collection.

        :param item: item to look up
        :return: item's position if found, None otherwise
        """
        for idx, other_item in enumerate(self._items):
            if other_item == item:
                return idx
        return None

    def append(self, *items: TItem) -> None:
        """Insert new values at the end of the list.

        Emits items_about_to_be_inserted items_inserted events.

        :param items: items to append
        """
        self.insert(len(self), *items)

    def insert(self, idx: int, *items: TItem) -> None:
        """Insert new values at given position.

        Emits items_about_to_be_inserted and items_inserted events.

        :param idx: where to put the new items
        :param items: items to insert
        """
        if not items:
            return
        self.items_about_to_be_inserted.emit(idx, len(items))
        self._items = self._items[:idx] + list(items) + self._items[idx:]
        self.items_inserted.emit(idx, len(items))

    def remove(self, idx: int, count: int) -> None:
        """Remove part of the collection's content.

        Emits items_about_to_be_removed and items_removed events.

        :param idx: where to start the removal
        :param count: how many elements to remove
        """
        self.items_about_to_be_removed.emit(idx, count)
        self._items = self._items[:idx] + self._items[idx + count :]
        self.items_removed.emit(idx, count)

    def clear(self) -> None:
        """Clear the entire collection.

        Emits items_about_to_be_removed and items_removed events.
        """
        self.remove(0, len(self))

    def move(self, idx: int, count: int, new_idx: int) -> None:
        """Move one item to a new position.

        Emits items_about_to_be_moved and items_moved events.

        :param idx: source position
        :param count: how many elements to move
        :param new_idx: target position
        """
        self.items_about_to_be_moved.emit(idx, count, new_idx)
        items = self._items[idx : idx + count]
        self._items = self._items[:idx] + self._items[idx + count :]
        self._items = self._items[:new_idx] + items + self._items[new_idx:]
        self.items_moved.emit(idx, count, new_idx)

    def replace(self, values: T.List[TItem]) -> None:
        """Replace the entire collection with new content.

        Emits items_about_to_be_removed, items_removed,
        items_about_to_be_inserted and items_inserted events.

        :param values: new content
        """
        self.clear()
        self.insert(0, *values)
