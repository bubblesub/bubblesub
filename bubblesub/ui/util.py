import sys
import time
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets


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
        self.start_work()
        while True:
            arg = self.queue.get()
            if arg is None:
                break
            try:
                value = self.work(arg)
            except Exception as ex:
                print(ex, file=sys.stderr)
                time.sleep(1)
            else:
                self.finished.emit(ResultObj(value))
        self.end_work()

    def start_work(self):
        pass

    def end(self):
        pass

    def work(self, arg):
        raise NotImplementedError()


def blend_colors(color1, color2, ratio):
    r = color1.red() * (1 - ratio) + color2.red() * ratio
    g = color1.green() * (1 - ratio) + color2.green() * ratio
    b = color1.blue() * (1 - ratio) + color2.blue() * ratio
    return QtGui.qRgb(r, g, b)
