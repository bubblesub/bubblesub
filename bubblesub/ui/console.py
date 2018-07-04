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
        }
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        for match in re.finditer(r'^(\[([ewid])\] )(.*)$', text):
            self.setFormat(
                match.start(),
                match.start() + len(match.group(1)),
                self._invisible_fmt
            )
            self.setFormat(
                match.start() + len(match.group(1)),
                match.end() - match.start(),
                self._style_map[match.group(2)]
            )

    def _get_format(self, color_name: str) -> QtGui.QTextCharFormat:
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(bubblesub.ui.util.get_color(self._api, color_name))
        fmt.setFont(self._font)
        return fmt


class Console(QtWidgets.QTextEdit):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._scroll_lock = False

        self.syntax_highlight = ConsoleSyntaxHighlight(api, self)
        self.setReadOnly(True)
        self.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)

        api.log.logged.connect(self._on_log)

    def _on_log(self, level: LogLevel, text: str) -> None:
        print(f'{datetime.datetime.now()} [{level.name.lower()[0]}] {text}')
        if level == LogLevel.Debug:
            return
        self.log(level, text)

    def log(self, level: LogLevel, text: str) -> None:
        old_pos = self.verticalScrollBar().value()

        self.moveCursor(QtGui.QTextCursor.End)
        cursor = QtGui.QTextCursor(self.textCursor())
        cursor.insertText(f'[{level.name.lower()[0]}] {text}\n')

        self.verticalScrollBar().setValue(
            old_pos
            if self._scroll_lock
            else self.verticalScrollBar().maximum()
        )

    def changeEvent(self, _event: QtCore.QEvent) -> None:
        self.syntax_highlight.update_style_map()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.modifiers() & QtCore.Qt.ControlModifier:
            distance = 1 if event.angleDelta().y() > 0 else -1
            font = self.syntax_highlight.get_font()
            new_size = font.pointSize() + distance
            if new_size < 5:
                return
            font.setPointSize(new_size)
            self.syntax_highlight.set_font(font)
            self._api.opt.general.gui.fonts['console'] = font.toString()
        else:
            super().wheelEvent(event)
            maximum = self.verticalScrollBar().maximum()
            current = self.verticalScrollBar().value()
            delta = maximum - current
            self._scroll_lock = delta > 5
