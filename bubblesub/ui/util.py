from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets


# alternative to QtCore.QAbstractListModel that simplifies indexing
class ListModel(QtCore.QObject):
    items_inserted = QtCore.pyqtSignal([int, int])
    items_removed = QtCore.pyqtSignal([int, int])
    item_changed = QtCore.pyqtSignal([int])

    def __init__(self):
        super().__init__()
        self._data = []

    def __len__(self):
        return len(self._data)

    def __getitem__(self, idx):
        return self._data[idx]

    def __setitem__(self, idx, value):
        self._data[idx] = value
        self.item_changed.emit(idx)

    def insert(self, idx, data):
        if not data:
            return
        self._data = self._data[:idx] + data + self._data[idx:]
        self.items_inserted.emit(idx, len(data))

    def remove(self, idx, count):
        self._data = self._data[:idx] + self._data[:idx + count]
        self.items_removed.emit(idx, count)


def error(msg):
    box = QtWidgets.QMessageBox()
    box.setIcon(QtWidgets.QMessageBox.Critical)
    box.setText(msg)
    box.exec_()


def ask(msg):
    box = QtWidgets.QMessageBox()
    box.setText(msg)
    box.setIcon(QtWidgets.QMessageBox.Question)
    box.addButton('Yes', QtWidgets.QMessageBox.YesRole)
    box.addButton('No', QtWidgets.QMessageBox.NoRole)
    return box.exec_() == 0


class ResultObj(QtCore.QObject):
    def __init__(self, value):
        self.value = value


class SimpleThread(QtCore.QThread):
    finished = QtCore.pyqtSignal(object)

    def __init__(self, queue, callback, parent=None):
        super().__init__(parent)
        self.queue = queue
        self.finished.connect(callback)

    def run(self):
        while True:
            arg = self.queue.get()
            if arg is None:
                return
            self.finished.emit(ResultObj(self.work(arg)))

    def work(self, arg):
        raise NotImplementedError()


def blend_colors(color1, color2, ratio):
    r = color1.red() * (1 - ratio) + color2.red() * ratio
    g = color1.green() * (1 - ratio) + color2.green() * ratio
    b = color1.blue() * (1 - ratio) + color2.blue() * ratio
    return QtGui.qRgb(r, g, b)
