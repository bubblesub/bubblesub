from PyQt5 import QtCore


class classproperty(property):
    def __init__(self, func):
        super().__init__()
        self.func = func

    def __get__(self, cls, owner):
        return self.func(owner)


class ObservableObject:
    _dirty = False
    _throttled = False

    def __setattr__(self, prop, new_value):
        if prop.startswith('_'):
            super().__setattr__(prop, new_value)
            return

        try:
            old_value = getattr(self, prop)
        except AttributeError:
            super().__setattr__(prop, new_value)
            return

        if new_value == old_value:
            return

        throttled = self._throttled
        self._throttled = True

        if not throttled:
            self._before_change()

        super().__setattr__(prop, new_value)
        self._dirty = True

        if not throttled:
            self._after_change()

        self._throttled = throttled

    def begin_update(self):
        self._throttled = True
        self._before_change()

    def end_update(self):
        self._throttled = False
        if self._dirty:
            self._after_change()
            self._dirty = False

    def _before_change(self):
        pass

    def _after_change(self):
        pass


# alternative to QtCore.QAbstractListModel that simplifies indexing
class ObservableList(QtCore.QObject):
    items_inserted = QtCore.pyqtSignal([int, int])
    items_removed = QtCore.pyqtSignal([int, int])
    item_changed = QtCore.pyqtSignal([int])
    items_about_to_be_inserted = QtCore.pyqtSignal([int, int])
    items_about_to_be_removed = QtCore.pyqtSignal([int, int])
    item_about_to_change = QtCore.pyqtSignal([int])

    def __init__(self):
        super().__init__()
        self._items = []

    def __getstate__(self):
        return self._items

    def __setstate__(self, state):
        self._items = state

    def __len__(self):
        return len(self._items)

    def __getitem__(self, idx):
        return self._items[idx]

    def __setitem__(self, idx, value):
        if isinstance(idx, slice):
            raise RuntimeError('Slice assignment is not supported')
        else:
            self._items[idx] = value
            self.item_changed.emit(idx)

    def get(self, idx, default=None):
        if idx < 0 or idx >= len(self):
            return default
        return self[idx]

    def index(self, items):
        for idx, item in enumerate(self):
            if item == items:
                return idx
        return None

    def insert(self, idx, items):
        if not items:
            return
        self.items_about_to_be_inserted.emit(idx, len(items))
        self._items = self._items[:idx] + items + self._items[idx:]
        self.items_inserted.emit(idx, len(items))

    def remove(self, idx, count):
        self.items_about_to_be_removed.emit(idx, count)
        self._items = self._items[:idx] + self._items[idx + count:]
        self.items_removed.emit(idx, count)

    def clear(self):
        self.remove(0, len(self))

    def move(self, idx, new_idx):
        item = self._items[idx]
        self.remove(idx, 1)
        self.insert(new_idx, [item])

    def replace(self, values):
        old_size = len(self)
        new_size = len(values)
        self.items_about_to_be_removed.emit(0, old_size)
        self._items[:] = []
        self.items_removed.emit(0, old_size)
        self.items_about_to_be_inserted.emit(0, new_size)
        self._items[:] = values
        self.items_inserted.emit(0, new_size)
