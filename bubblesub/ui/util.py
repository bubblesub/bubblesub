from PyQt5 import QtGui
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


def blend_colors(color1, color2, ratio):
    r = color1.red() * (1 - ratio) + color2.red() * ratio
    g = color1.green() * (1 - ratio) + color2.green() * ratio
    b = color1.blue() * (1 - ratio) + color2.blue() * ratio
    return QtGui.qRgb(r, g, b)
