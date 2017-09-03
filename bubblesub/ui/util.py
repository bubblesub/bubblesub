import functools
import bubblesub.util
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets


def error(msg):
    box = QtWidgets.QMessageBox()
    box.setIcon(QtWidgets.QMessageBox.Critical)
    box.setText(msg)
    box.exec_()


def notice(msg):
    box = QtWidgets.QMessageBox()
    box.setIcon(QtWidgets.QMessageBox.Information)
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
    return QtGui.qRgb(
        color1.red() * (1 - ratio) + color2.red() * ratio,
        color1.green() * (1 - ratio) + color2.green() * ratio,
        color1.blue() * (1 - ratio) + color2.blue() * ratio)


class ColorPicker(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self._label = QtWidgets.QLabel(self)
        self._button = QtWidgets.QPushButton('Change', self)
        self._button.clicked.connect(self._button_clicked)
        layout = QtWidgets.QHBoxLayout(self, margin=0)
        layout.addWidget(self._label)
        layout.addWidget(self._button)
        self._color = QtGui.QColor(0, 0, 0, 0)
        self.set_color(self._color)

    def _button_clicked(self, _event):
        dialog = QtWidgets.QColorDialog(self)
        dialog.setCurrentColor(self._color)
        dialog.setOption(dialog.ShowAlphaChannel, True)
        if dialog.exec_():
            self.set_color(dialog.selectedColor())

    def get_color(self):
        return self._color

    def set_color(self, color):
        style = '''QLabel:enabled {{
            background-color: #{:02x}{:02x}{:02x};
            opacity: {};
            border: 1px solid black;
        }}'''.format(color.red(), color.green(), color.blue(), color.alpha())
        self._label.setStyleSheet(style)
        if self._color != color:
            self._color = color
            self.changed.emit()

    color = QtCore.pyqtProperty(QtGui.QColor, get_color, set_color)


class TimeEdit(QtWidgets.QLineEdit):
    def __init__(self, parent=None, allow_negative=False):
        super().__init__(parent)
        self._allow_negative = False
        self.set_allow_negative(allow_negative)

    def set_allow_negative(self, allow):
        self._allow_negative = allow
        if allow:
            self.setInputMask('X9:99:99.999')
            self.setValidator(
                QtGui.QRegExpValidator(
                    QtCore.QRegExp(r'[+-]\d:\d\d:\d\d\.\d\d\d'),
                    self.parent()))
        else:
            self.setInputMask('9:99:99.999')
        self.reset_text()

    def reset_text(self):
        if self._allow_negative:
            self.setText('+0:00:00.000')
        else:
            self.setText('0:00:00.000')
        self.setCursorPosition(0)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)

        if not event.key() in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
            return

        text = self.text()
        delta = 10
        if event.key() == QtCore.Qt.Key_Up:
            time = bubblesub.util.str_to_ms(text) + delta
        elif event.key() == QtCore.Qt.Key_Down:
            time = bubblesub.util.str_to_ms(text) - delta

        text = bubblesub.util.ms_to_str(time)
        if self._allow_negative and time >= 0:
            text = '+' + text

        self.setText(text)
        self.textEdited.emit(self.text())


def _menu_about_to_show(menu):
    for action in menu.actions():
        if hasattr(action, 'cmd') and action.cmd:
            action.setEnabled(action.cmd.enabled())


class _CommandAction(QtWidgets.QAction):
    def __init__(self, api, cmd_name, cmd_args):
        super().__init__()
        self.api = api
        self.cmd_name = cmd_name
        self.cmd = api.cmd.get(cmd_name, cmd_args)
        self.triggered.connect(functools.partial(api.cmd.run, self.cmd))


def setup_cmd_menu(api, parent, menu_def):
    action_map = {}
    if hasattr(parent, 'aboutToShow'):
        parent.aboutToShow.connect(
            functools.partial(_menu_about_to_show, parent))
    for item in menu_def:
        if item is None:
            parent.addSeparator()
        elif len(item) > 1 and isinstance(item[1], list):
            submenu = parent.addMenu(item[0])
            submenu.aboutToShow.connect(
                functools.partial(_menu_about_to_show, submenu))
            action_map.update(setup_cmd_menu(api, submenu, item[1]))
        else:
            cmd_name, *cmd_args = item
            action = _CommandAction(api, cmd_name, cmd_args)
            action.setParent(parent)
            action.setText(api.cmd.get(cmd_name, cmd_args).menu_name)
            parent.addAction(action)
            action_map[(cmd_name, *cmd_args)] = action
    return action_map


def get_color(api, color_name):
    current_palette = api.opt.general['current_palette']
    palette_def = api.opt.general['palettes'][current_palette]
    red, green, blue = palette_def[color_name]
    return QtGui.QColor(red, green, blue)


def load_dialog(parent, filter, directory=None):
    path, _ = QtWidgets.QFileDialog.getOpenFileName(
        parent,
        directory=directory or QtCore.QDir.homePath(),
        filter=filter)
    return path


def save_dialog(parent, filter, directory=None, file_name=None):
    directory = directory or QtCore.QDir.homePath()
    if file_name:
        directory += '/' + file_name
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent,
        directory=directory,
        filter=filter)
    return path
