from PyQt5 import QtCore


class classproperty(property):
    def __init__(self, func):
        super().__init__()
        self.func = func

    def __get__(self, cls, owner):
        return self.func(owner)


class ObservableProperty:
    def __init__(self, attr):
        self.attr = attr

    def __get__(self, instance, owner):
        return instance.__dict__.get(self.attr, None)

    def __set__(self, instance, value):
        if getattr(instance, self.attr) != value:
            instance.notify_before_property_change()
            instance.__dict__[self.attr] = value
            instance.notify_after_property_change()


class ObservableObject:
    prop = {}
    REQUIRED = object()

    def __init_subclass__(cls):
        if not hasattr(cls, 'prop'):
            raise RuntimeError(
                'Observable object needs to have a "prop" class property '
                'that tells what to observe')
        for key in cls.prop:
            setattr(cls, key, ObservableProperty(key))

    def __init__(self, **kwargs):
        self._dirty = False
        self._throttled = True
        empty = object()
        for key, value in self.prop.items():
            user_value = kwargs.get(key, empty)
            if user_value is empty:
                if value == self.REQUIRED:
                    raise RuntimeError('Missing argument: {}'.format(key))
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, user_value)
        for key in kwargs:
            if key not in self.prop:
                raise RuntimeError('Invalid argument: {}'.format(key))
        self._throttled = False

    def begin_update(self):
        self._throttled = True
        self._before_change()

    def end_update(self):
        self._throttled = False
        if self._dirty:
            self._after_change()
            self._dirty = False

    def notify_before_property_change(self):
        if not self._throttled:
            self._before_change()

    def notify_after_property_change(self):
        self._dirty = True
        if not self._throttled:
            self._after_change()

    def _before_change(self):
        pass

    def _after_change(self):
        pass


# alternative to QtCore.QAbstractListModel that simplifies indexing
class ListModel(QtCore.QObject):
    items_inserted = QtCore.pyqtSignal([int, int])
    items_removed = QtCore.pyqtSignal([int, int])
    item_changed = QtCore.pyqtSignal([int])
    items_about_to_be_inserted = QtCore.pyqtSignal([int, int])
    items_about_to_be_removed = QtCore.pyqtSignal([int, int])
    item_about_to_change = QtCore.pyqtSignal([int])

    def __init__(self):
        super().__init__()
        self._data = []

    def __len__(self):
        return len(self._data)

    def __getitem__(self, idx):
        return self._data[idx]

    def __setitem__(self, idx, value):
        if isinstance(idx, slice):
            raise RuntimeError('Slice assignment is not supported')
        else:
            self._data[idx] = value
            self.item_changed.emit(idx)

    def get(self, idx, default=None):
        if idx < 0 or idx >= len(self):
            return default
        return self[idx]

    def index(self, data):
        for idx, item in enumerate(self):
            if item == data:
                return idx
        return None

    def insert(self, idx, data):
        if not data:
            return
        self.items_about_to_be_inserted.emit(idx, len(data))
        self._data = self._data[:idx] + data + self._data[idx:]
        self.items_inserted.emit(idx, len(data))

    def remove(self, idx, count):
        self.items_about_to_be_removed.emit(idx, count)
        self._data = self._data[:idx] + self._data[idx + count:]
        self.items_removed.emit(idx, count)

    def clear(self):
        self.remove(0, len(self))

    def move(self, idx, new_idx):
        item = self._data[idx]
        self.remove(idx, 1)
        self.insert(new_idx, [item])

    def replace(self, values):
        old_size = len(self)
        new_size = len(values)
        self.items_about_to_be_removed.emit(0, old_size)
        self._data[:] = []
        self.items_removed.emit(0, old_size)
        self.items_about_to_be_inserted.emit(0, new_size)
        self._data[:] = values
        self.items_inserted.emit(0, new_size)
