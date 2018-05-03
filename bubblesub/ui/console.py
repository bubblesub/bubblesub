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
        self._style_map: T.Dict[str, QtGui.QTextCharFormat] = {}
        self.update_style_map()

        self._invisible_fmt = QtGui.QTextCharFormat()
        self._invisible_fmt.setFontStretch(1)
        self._invisible_fmt.setFontPointSize(1)
        self._invisible_fmt.setForeground(QtCore.Qt.transparent)

    def _get_format(self, color_name: str) -> QtGui.QTextCharFormat:
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(bubblesub.ui.util.get_color(self._api, color_name))
        fmt.setFont(
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        )
        return fmt

    def update_style_map(self) -> None:
        self._style_map = {
            'e': self._get_format('console/error'),
            'w': self._get_format('console/warning'),
            'i': self._get_format('console/info'),
            'd': self._get_format('console/debug'),
        }

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


class Console(QtWidgets.QTextEdit):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self.syntax_highlight = ConsoleSyntaxHighlight(api, self)
        self.setReadOnly(True)
        self.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)

        api.log.logged.connect(self._on_log)

    def _on_log(self, level: LogLevel, text: str) -> None:
        print(f'[{level.name.lower()[0]}] {text}')
        if level == LogLevel.Debug:
            return
        self.log(level, text)

    def log(self, level: LogLevel, text: str) -> None:
        self.moveCursor(QtGui.QTextCursor.End)
        cursor = QtGui.QTextCursor(self.textCursor())
        cursor.insertText(f'[{level.name.lower()[0]}] {text}\n')
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def changeEvent(self, _event: QtCore.QEvent) -> None:
        self.syntax_highlight.update_style_map()
        self.syntax_highlight.rehighlight()
