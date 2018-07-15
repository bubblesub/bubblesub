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

import datetime
import re
import typing as T

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ui.util
from bubblesub.api.log import LogLevel


class ConsoleSyntaxHighlight(QtGui.QSyntaxHighlighter):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtCore.QObject
    ) -> None:
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
            r'^'
            r'(?P<prefix>\[(?P<log_level>[ewid])\] )'
            r'(?P<timestamp>\[[^\]]+\]) '
            r'(?P<text>.*)'
            r'$'
        )

        self.update_style_map()

    def get_font(self) -> QtGui.QFont:
        return self._font

    def set_font(self, font: QtGui.QFont) -> None:
        self._font = font
        self.update_style_map()

    def update_style_map(self) -> None:
        self._style_map = {
            'e': self._get_format('console/error'),
            'w': self._get_format('console/warning'),
            'i': self._get_format('console/info'),
            'd': self._get_format('console/debug'),
            'timestamp': self._get_format('console/timestamp'),
            'command': self._get_format('console/command'),
        }
        QtWidgets.QApplication.setOverrideCursor(
            QtGui.QCursor(QtCore.Qt.WaitCursor)
        )
        self.rehighlight()
        QtWidgets.QApplication.restoreOverrideCursor()

    def highlightBlock(self, text: str) -> None:
        for match in re.finditer(self._regex, text):
            start = match.start()
            start_of_timestamp = match.start() + len(match.group('prefix'))
            start_of_text = start_of_timestamp + len(match.group('timestamp'))
            end = match.end()

            self.setFormat(
                start, start_of_timestamp - start, self._invisible_fmt
            )
            self.setFormat(
                start_of_timestamp,
                start_of_text - start_of_timestamp,
                self._style_map['timestamp']
            )
            self.setFormat(
                start_of_text,
                end - start,
                self._style_map['command']
                if match.group('text').startswith('/')
                else self._style_map[match.group('log_level')]
            )

    def _get_format(self, color_name: str) -> QtGui.QTextCharFormat:
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(bubblesub.ui.util.get_color(self._api, color_name))
        fmt.setFont(self._font)
        return fmt


class ConsoleTextEdit(QtWidgets.QTextEdit):
    scroll_lock_changed = QtCore.pyqtSignal()

    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._scroll_lock = False

        self._syntax_highlight = ConsoleSyntaxHighlight(api, self)
        self.setReadOnly(True)
        self.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)

        api.log.logged.connect(self._on_log)

    def _on_log(self, level: LogLevel, text: str) -> None:
        print(f'{datetime.datetime.now()} [{level.name.lower()[0]}] {text}')
        if level == LogLevel.Debug:
            return

        old_pos_x = self.horizontalScrollBar().value()
        old_pos_y = self.verticalScrollBar().value()
        separator = '\n' if self.toPlainText().strip() else ''

        self.moveCursor(QtGui.QTextCursor.End)
        cursor = QtGui.QTextCursor(self.textCursor())
        cursor.insertText(
            f'{separator}'
            f'[{level.name.lower()[0]}] '
            f'[{datetime.datetime.now():%H:%M:%S.%f}] '
            f'{text}'
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
            self._api.opt.general.gui.fonts['console'] = font.toString()
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


class Console(QtWidgets.QWidget):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)

        self._text_edit = ConsoleTextEdit(api, self)
        self._auto_scroll_chkbox = QtWidgets.QCheckBox(
            'Auto scroll', self
        )
        self._auto_scroll_chkbox.setChecked(not self._text_edit.scroll_lock)

        self._text_edit.scroll_lock_changed.connect(
            self._on_text_edit_scroll_lock_change
        )
        self._auto_scroll_chkbox.stateChanged.connect(
            self._on_auto_scroll_chkbox_change
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text_edit)
        layout.addWidget(self._auto_scroll_chkbox)

    def _on_text_edit_scroll_lock_change(self):
        self._auto_scroll_chkbox.setChecked(not self._text_edit.scroll_lock)

    def _on_auto_scroll_chkbox_change(self):
        self._text_edit.scroll_lock = not self._auto_scroll_chkbox.isChecked()
