import functools

from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets

import bubblesub.util


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
        self._button.clicked.connect(self._on_button_click)
        layout = QtWidgets.QHBoxLayout(self, margin=0)
        layout.addWidget(self._label)
        layout.addWidget(self._button)
        self._color = QtGui.QColor(0, 0, 0, 0)
        self.set_color(self._color)

    def _on_button_click(self, _event):
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

        value = self.get_value()
        delta = 10
        if event.key() == QtCore.Qt.Key_Up:
            value += delta
        elif event.key() == QtCore.Qt.Key_Down:
            value -= delta

        self.set_value(value)

    def get_value(self):
        return bubblesub.util.str_to_ms(self.text())

    def set_value(self, time):
        text = bubblesub.util.ms_to_str(time)
        if self._allow_negative and time >= 0:
            text = '+' + text
        self.setText(text)
        self.textEdited.emit(self.text())
        self.setCursorPosition(0)


def _window_from_menu(menu):
    window = menu
    while window.parent() is not None:
        window = window.parent()
    return window


def _on_menu_about_to_show(menu):
    window = _window_from_menu(menu)
    window.setProperty('focused-widget', window.focusWidget())
    for action in menu.actions():
        if hasattr(action, 'cmd') and action.cmd:
            action.setEnabled(action.cmd.is_enabled)


def _on_menu_about_to_hide(menu):
    window = _window_from_menu(menu)
    focused_widget = window.property('focused-widget')
    if focused_widget:
        focused_widget.setFocus()


class _CommandAction(QtWidgets.QAction):
    def __init__(self, api, cmd_name, cmd_args, parent):
        super().__init__(parent)
        self.cmd = api.cmd.get(cmd_name, cmd_args)
        self.triggered.connect(lambda: api.cmd.run(self.cmd))


def setup_cmd_menu(api, parent, menu_def):
    action_map = {}
    if hasattr(parent, 'aboutToShow'):
        parent.aboutToShow.connect(
            functools.partial(_on_menu_about_to_show, parent))
        parent.aboutToHide.connect(
            functools.partial(_on_menu_about_to_hide, parent))
    for item in menu_def:
        if item is None:
            parent.addSeparator()
        elif len(item) > 1 and isinstance(item[1], list):
            submenu = parent.addMenu(item[0])
            action_map.update(setup_cmd_menu(api, submenu, item[1]))
        else:
            cmd_name, *cmd_args = item
            action = _CommandAction(api, cmd_name, cmd_args, parent)
            action.setText(api.cmd.get(cmd_name, cmd_args).menu_name)
            parent.addAction(action)
            action_map[(cmd_name, *cmd_args)] = action
    return action_map


def get_color(api, color_name):
    current_palette = api.opt.general['current_palette']
    palette_def = api.opt.general['palettes'][current_palette]
    color_value = palette_def[color_name]
    return QtGui.QColor(*color_value)


def load_dialog(parent, file_filter, directory=None):
    path, _ = QtWidgets.QFileDialog.getOpenFileName(
        parent,
        directory=directory or QtCore.QDir.homePath(),
        filter=file_filter)
    return path


def save_dialog(parent, file_filter, directory=None, file_name=None):
    directory = directory or QtCore.QDir.homePath()
    if file_name:
        directory += '/' + file_name
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent,
        directory=directory,
        filter=file_filter)
    return path


def time_jump_dialog(
        parent,
        value=0,
        relative_label='Time:',
        absolute_label='Time:',
        relative_checked=True,
        show_radio=True):
    class TimeJumpDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)

            self._label = QtWidgets.QLabel('', self)
            self._time_edit = bubblesub.ui.util.TimeEdit(self)
            self._radio_rel = QtWidgets.QRadioButton('Relative', self)
            self._radio_abs = QtWidgets.QRadioButton('Absolute', self)
            if relative_checked:
                self._radio_rel.setChecked(True)
            else:
                self._radio_abs.setChecked(True)
            strip = QtWidgets.QDialogButtonBox(self)
            strip.addButton(strip.Ok)
            strip.addButton(strip.Cancel)

            if not show_radio:
                self._radio_abs.setHidden(True)
                self._radio_rel.setHidden(True)

            strip.accepted.connect(self.accept)
            strip.rejected.connect(self.reject)
            self._radio_rel.clicked.connect(self._on_radio_click)
            self._radio_abs.clicked.connect(self._on_radio_click)

            layout = QtWidgets.QVBoxLayout(self)
            layout.addWidget(self._label)
            layout.addWidget(self._time_edit)
            layout.addWidget(self._radio_rel)
            layout.addWidget(self._radio_abs)
            layout.addWidget(strip)

            self._on_radio_click()
            self._time_edit.set_value(value)

        def _on_radio_click(self):
            is_relative = self._radio_rel.isChecked()
            if is_relative:
                self._label.setText(relative_label)
            else:
                self._label.setText(absolute_label)
            self._time_edit.set_allow_negative(is_relative)

        def value(self):
            return (
                self._time_edit.get_value(),
                self._radio_rel.isChecked())

    dialog = TimeJumpDialog(parent)
    if dialog.exec_():
        return dialog.value()
    return None
