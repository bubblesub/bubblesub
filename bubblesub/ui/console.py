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

import argparse
import datetime
import re
import typing as T
from dataclasses import dataclass

from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.api.cmd import CommandError
from bubblesub.api.log import LogLevel


class ConsoleSyntaxHighlight(QtGui.QSyntaxHighlighter):
    def __init__(self, api: Api, parent: QtCore.QObject) -> None:
        super().__init__(parent)
        self._api = api

        self._font = QtGui.QFontDatabase.systemFont(
            QtGui.QFontDatabase.FixedFont
        )
        self._style_map: T.Dict[str, QtGui.QTextCharFormat] = {}

        self._invisible_fmt = QtGui.QTextCharFormat()
        self._invisible_fmt.setFontStretch(1)
        self._invisible_fmt.setFontPointSize(1)
        self._invisible_fmt.setForeground(QtCore.Qt.transparent)

        self._regex = re.compile(
            r"^"
            r"(?P<prefix>\[(?P<log_level>[ewidc])\] )"
            r"(?P<timestamp>\[[^\]]+\]) "
            r"(?P<text>.*)"
            r"$"
        )

        self.update_style_map()

    def get_font(self) -> QtGui.QFont:
        return self._font

    def set_font(self, font: QtGui.QFont) -> None:
        self._font = font
        self.update_style_map()

    def update_style_map(self) -> None:
        self._style_map = {
            "e": self._get_format("console/error"),
            "w": self._get_format("console/warning"),
            "i": self._get_format("console/info"),
            "d": self._get_format("console/debug"),
            "c": self._get_format("console/command"),
            "timestamp": self._get_format("console/timestamp"),
        }
        QtWidgets.QApplication.setOverrideCursor(
            QtGui.QCursor(QtCore.Qt.WaitCursor)
        )
        self.rehighlight()
        QtWidgets.QApplication.restoreOverrideCursor()

    def highlightBlock(self, text: str) -> None:
        for match in re.finditer(self._regex, text):
            start = match.start()
            start_of_timestamp = match.start() + len(match.group("prefix"))
            start_of_text = start_of_timestamp + len(match.group("timestamp"))
            end = match.end()

            self.setFormat(
                start, start_of_timestamp - start, self._invisible_fmt
            )
            self.setFormat(
                start_of_timestamp,
                start_of_text - start_of_timestamp,
                self._style_map["timestamp"],
            )
            self.setFormat(
                start_of_text,
                end - start,
                self._style_map[match.group("log_level")],
            )

    def _get_format(self, color_name: str) -> QtGui.QTextCharFormat:
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(self._api.gui.get_color(color_name))
        fmt.setFont(self._font)
        return fmt


class ConsoleLogWindow(QtWidgets.QTextEdit):
    scroll_lock_changed = QtCore.pyqtSignal()

    def __init__(self, api: Api, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._api = api
        self._scroll_lock = False
        self._empty = True

        self._syntax_highlight = ConsoleSyntaxHighlight(api, self)
        self.setObjectName("console")
        self.setReadOnly(True)
        self.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)

        api.log.logged.connect(self._on_log)

    def _on_log(self, level: LogLevel, text: str) -> None:
        if level == LogLevel.Debug:
            return

        old_pos_x = self.horizontalScrollBar().value()
        old_pos_y = self.verticalScrollBar().value()
        separator = "" if self._empty else "\n"

        self.moveCursor(QtGui.QTextCursor.End)
        cursor = QtGui.QTextCursor(self.textCursor())
        cursor.insertText(
            f"{separator}"
            f"[{level.name.lower()[0]}] "
            f"[{datetime.datetime.now():%H:%M:%S.%f}] "
            f"{text}"
        )

        self.horizontalScrollBar().setValue(
            old_pos_x
            if self._scroll_lock
            else self.verticalScrollBar().minimum()
        )
        self.verticalScrollBar().setValue(
            old_pos_y
            if self._scroll_lock
            else self.verticalScrollBar().maximum()
        )
        self._empty = False

    def changeEvent(self, _event: QtCore.QEvent) -> None:
        self._syntax_highlight.update_style_map()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.modifiers() & QtCore.Qt.ControlModifier:
            distance = 1 if event.angleDelta().y() > 0 else -1
            font = self._syntax_highlight.get_font()
            new_size = font.pointSize() + distance
            if new_size < 5:
                return
            font.setPointSize(new_size)
            self._syntax_highlight.set_font(font)
            self._api.opt.general.gui.fonts["console"] = font.toString()
        else:
            super().wheelEvent(event)
            maximum = self.verticalScrollBar().maximum()
            current = self.verticalScrollBar().value()
            delta = maximum - current
            self.scroll_lock = delta > 5

    @property
    def scroll_lock(self) -> bool:
        return self._scroll_lock

    @scroll_lock.setter
    def scroll_lock(self, value: bool) -> None:
        self._scroll_lock = value
        self.scroll_lock_changed.emit()


@dataclass
class Completion:
    prefix: str
    suffix: str
    index: int
    start_pos: int
    suggestions: T.List[str]


class ConsoleInput(QtWidgets.QLineEdit):
    def __init__(self, api: Api, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._api = api
        self._edited = False
        self._compl: T.Optional[Completion] = None

        self._history_pos = 0
        self._history: T.List[str] = []

        self.setObjectName("console-input")
        self.setFont(
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        )

        self.returnPressed.connect(self._on_return_press)
        self.textEdited.connect(self._on_edit)

    def event(self, event: QtCore.QEvent) -> bool:
        if event.type() != QtCore.QEvent.KeyPress:
            return super().event(event)

        if event.key() not in {QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab}:
            return super().event(event)

        if self._compl is None:
            compl = self._make_autocomplete()
            if not compl.suggestions:
                return True
            self._compl = compl
            self._compl.index = 0 if event.key() == QtCore.Qt.Key_Tab else -1
        else:
            self._compl.index += 1 if event.key() == QtCore.Qt.Key_Tab else 1

        self._compl.index %= len(self._compl.suggestions)
        self.setText(
            self._compl.prefix[: self._compl.start_pos]
            + self._compl.suggestions[self._compl.index]
        )
        return True

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if not self._edited or not self.text():
            if event.key() == QtCore.Qt.Key_Up:
                if self._history_pos > 0:
                    self._history_pos -= 1
                    self.setText(self._history[self._history_pos])
                    self._edited = False
                return

            if event.key() == QtCore.Qt.Key_Down:
                if self._history_pos + 1 < len(self._history):
                    self._history_pos += 1
                    self.setText(self._history[self._history_pos])
                    self._edited = False
                return

        super().keyPressEvent(event)

    def _on_edit(self) -> None:
        self._edited = True
        self._compl = None

    def _on_return_press(self) -> None:
        if not self.text():
            return

        try:
            index = self._history.index(self.text())
        except ValueError:
            pass
        else:
            del self._history[index]

        self._history.append(self.text())
        self._history_pos = len(self._history)

        try:
            cmds = self._api.cmd.parse_cmdline(self.text())
        except CommandError as ex:
            self._api.log.error(str(ex))
        else:
            for cmd in cmds:
                self._api.cmd.run(cmd)

        self.setText("")
        self._edited = False

    def _make_autocomplete(self) -> Completion:
        compl = Completion(
            prefix=self.text()[: self.cursorPosition()],
            suffix=self.text()[self.cursorPosition() :],
            suggestions=[],
            index=0,
            start_pos=0,
        )

        # command names
        match = re.match("^(?P<cmd>[^ ]+) ?$", compl.prefix)
        if match:
            for cls in self._api.cmd.get_all():
                for name in cls.names:
                    if name.startswith(match.group("cmd")):
                        compl.suggestions.append(name + " ")
            compl.suggestions.sort()

        # command arguments
        match = re.match(
            "^(?P<cmd>[^ ]+) (?:.*?)(?P<arg>-[^ =]*)$", compl.prefix
        )
        if match:
            cls = self._api.cmd.get(match.group("cmd"))
            if cls:
                parser = argparse.ArgumentParser(add_help=False)
                cls.decorate_parser(self._api, parser)
                for action in parser._actions:  # pylint: disable=W0212
                    if any(
                        opt.startswith(match.group("arg"))
                        for opt in action.option_strings
                    ):
                        compl.start_pos = match.start("arg")
                        compl.suggestions.append(
                            list(sorted(action.option_strings, key=len))[-1]
                            + " "
                        )

        return compl


class Console(QtWidgets.QWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

        self._api = api
        self.log_window = ConsoleLogWindow(api, self)

        strip = QtWidgets.QWidget(self)
        self.input = ConsoleInput(api, strip)
        self.auto_scroll_chkbox = QtWidgets.QCheckBox("Auto scroll", strip)
        self.clear_btn = QtWidgets.QPushButton("Clear", strip)
        self.auto_scroll_chkbox.setChecked(not self.log_window.scroll_lock)

        self.clear_btn.clicked.connect(self._on_clear_btn_click)
        self.log_window.scroll_lock_changed.connect(
            self._on_text_edit_scroll_lock_change
        )
        self.auto_scroll_chkbox.stateChanged.connect(
            self._on_auto_scroll_chkbox_change
        )

        strip_layout = QtWidgets.QHBoxLayout(strip)
        strip_layout.setSpacing(4)
        strip_layout.setContentsMargins(0, 0, 0, 0)
        strip_layout.addWidget(self.input)
        strip_layout.addWidget(self.auto_scroll_chkbox)
        strip_layout.addWidget(self.clear_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.log_window)
        layout.addWidget(strip)

    def _on_text_edit_scroll_lock_change(self) -> None:
        self.auto_scroll_chkbox.setChecked(not self.log_window.scroll_lock)

    def _on_auto_scroll_chkbox_change(self) -> None:
        self.log_window.scroll_lock = not self.auto_scroll_chkbox.isChecked()
        if self.auto_scroll_chkbox.isChecked():
            self.log_window.horizontalScrollBar().setValue(
                self.log_window.horizontalScrollBar().minimum()
            )
            self.log_window.verticalScrollBar().setValue(
                self.log_window.verticalScrollBar().maximum()
            )

    def _on_clear_btn_click(self) -> None:
        self.log_window.document().setPlainText("")
