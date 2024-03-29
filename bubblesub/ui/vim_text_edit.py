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

# pylint: disable=import-outside-toplevel

import contextlib
import logging
from collections.abc import Iterator
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import (
    QFocusEvent,
    QInputMethodEvent,
    QKeyEvent,
    QSyntaxHighlighter,
    QTextCursor,
)
from PyQt5.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

KEYMAP = {
    Qt.Key.Key_Return: "<CR>",
    Qt.Key.Key_Escape: "\x1B",
    Qt.Key.Key_Backspace: "<BS>",
    Qt.Key.Key_Delete: "<Del>",
    Qt.Key.Key_Right: "<Right>",
    Qt.Key.Key_Left: "<Left>",
    Qt.Key.Key_Up: "<Up>",
    Qt.Key.Key_Down: "<Down>",
    Qt.Key.Key_Home: "<Home>",
    Qt.Key.Key_End: "<End>",
}


def byte_pos_to_string_pos(lines: list[str], col_b: int, row: int) -> int:
    return len(lines[row].encode()[:col_b].decode())


def rel_pos_to_abs_pos(lines: list[str], row: int, col: int) -> int:
    return sum(len(lines[y]) + 1 for y in range(row)) + min(
        len(lines[row]), col
    )


class VimTextEdit(QPlainTextEdit):
    def __init__(self, parent: QWidget) -> None:
        self._nvim = None
        self._vim_mode_enabled = False
        self.vim_arguments: list[str] = []
        self._signals_connected = 0
        super().__init__(parent)
        self._connect_ui_signals()
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.highlighter: Optional[QSyntaxHighlighter]

        self.selectionChanged.connect(self._selection_changed)
        self.cursorPositionChanged.connect(self._cursor_position_changed)
        self.textChanged.connect(self._text_changed)

    @property
    def vim_mode_enabled(self) -> bool:
        return self._vim_mode_enabled

    @vim_mode_enabled.setter
    def vim_mode_enabled(self, enabled: bool) -> None:
        self._vim_mode_enabled = enabled
        self._restart_session()
        with self._ignore_ui_signals():
            self._sync_ui()

    def reset(self) -> None:
        if self._vim_mode_enabled and self._nvim:
            with self._reconnect_guard():
                self._nvim.input("\x1B")
                self._nvim.input("\x1B")
                with self._ignore_ui_signals():
                    self._sync_ui()

    def _text_changed(self) -> None:
        if self._signals_connected <= 0:
            return
        if self.vim_mode_enabled and self._nvim:
            with self._ignore_ui_signals(), self._reconnect_guard():
                text = self.property(self.metaObject().userProperty().name())

                self._nvim.input("\x1B")
                self._nvim.input("\x1B")
                self._nvim.command("%bufdo! bd!")
                self._nvim.current.buffer[:] = text.splitlines()
                self._nvim.input("\x1B")

    def _cursor_position_changed(self) -> None:
        if self._signals_connected <= 0:
            return
        if self.vim_mode_enabled and self._nvim:
            with self._ignore_ui_signals(), self._reconnect_guard():
                self._sync_ui()

    def _selection_changed(self) -> None:
        if self._signals_connected <= 0:
            return
        if self.vim_mode_enabled and self._nvim:
            with self._ignore_ui_signals(), self._reconnect_guard():
                self._sync_ui()

    @contextlib.contextmanager
    def _reconnect_guard(self) -> Iterator[None]:
        if self.vim_mode_enabled and self._nvim:
            try:
                yield
            except OSError as ex:
                logging.exception(ex)
                self._restart_session()
                with self._ignore_ui_signals():
                    self._sync_ui()
        else:
            yield

    @contextlib.contextmanager
    def _ignore_ui_signals(self) -> Iterator[None]:
        self._disconnect_ui_signals()
        try:
            yield
        finally:
            self._connect_ui_signals()

    def _disconnect_ui_signals(self) -> None:
        self._signals_connected -= 1

    def _connect_ui_signals(self) -> None:
        self._signals_connected += 1

    def inputMethodEvent(self, event: QInputMethodEvent) -> None:
        if self.vim_mode_enabled and self._nvim:
            with self._ignore_ui_signals(), self._reconnect_guard():
                self._nvim.input(event.commitString())
                self._sync_ui()
        else:
            super().inputMethodEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.vim_mode_enabled and self._nvim:
            with self._ignore_ui_signals(), self._reconnect_guard():
                if event.key() in KEYMAP:
                    self._nvim.input(KEYMAP[event.key()])
                    self._sync_ui()
                elif event.text():
                    self._nvim.input(event.text())
                    self._sync_ui()
                else:
                    super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:
        super().focusInEvent(event)
        if self.vim_mode_enabled and self._nvim:
            with self._ignore_ui_signals():
                self._sync_ui()

    def _restart_session(self) -> None:
        try:
            from pynvim import attach

            self._nvim = attach(
                "child",
                argv=["/usr/bin/env", "nvim", "--embed", "--headless"]
                + self.vim_arguments,
            )
            if not self._nvim:
                return
            self._nvim.command("set clipboard+=unnamed")
            self._nvim.command("set clipboard+=unnamedplus")
            with self._ignore_ui_signals():
                self._sync_ui()
        except (ImportError, OSError) as ex:
            logging.exception(ex)
            self._nvim = None

    def _sync_ui(self) -> None:
        # pylint: disable=too-many-statements
        if self._nvim is None:
            return

        response = self._nvim.request("nvim_get_mode")
        mode = response["mode"]
        blocking = response["blocking"]

        self.setCursorWidth({"no": 10, "n": 10}.get(mode, 1))

        if blocking:
            return

        lines = list(self._nvim.current.buffer)
        self.setPlainText("\n".join(lines))

        def get_pos(mark: str) -> tuple[int, int]:
            row, col_b = self._nvim.eval(f'getpos("{mark}")')[1:3]
            row -= 1
            col_b -= 1
            col = byte_pos_to_string_pos(lines, col_b, row)
            return row, col

        start_row, start_col = get_pos("v")
        start_pos = rel_pos_to_abs_pos(lines, start_row, start_col)

        end_row, end_col = get_pos(".")
        end_pos = rel_pos_to_abs_pos(lines, end_row, end_col)

        cursor = self.textCursor()
        cursor.setPosition(end_pos)
        self.setTextCursor(cursor)

        if mode == "v":
            cursor1 = self.textCursor()
            cursor1.setPosition(start_pos)
            cursor1.setPosition(end_pos, cursor.KeepAnchor)
            cursor2 = self.textCursor()
            cursor2.setPosition(start_pos)
            cursor2.movePosition(cursor.Right, cursor.KeepAnchor, 1)
            cursor3 = self.textCursor()
            cursor3.setPosition(end_pos)
            cursor3.movePosition(cursor.Right, cursor.KeepAnchor, 1)
            self.setExtraSelections(
                [
                    self._create_extra_selection(cursor1),
                    self._create_extra_selection(cursor2),
                    self._create_extra_selection(cursor3),
                ]
            )

        elif mode == "V":
            # line-wise selection
            (start_row, end_row) = sorted((start_row, end_row))
            cursor = self.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.Down, 0, start_row)
            cursor.movePosition(cursor.Start, cursor.KeepAnchor)
            cursor.movePosition(cursor.Down, cursor.KeepAnchor, end_row)
            cursor.movePosition(cursor.EndOfLine, cursor.KeepAnchor)
            self.setExtraSelections([self._create_extra_selection(cursor)])

        elif mode == "":
            # block-wise selection
            (start_row, end_row) = sorted((start_row, end_row))
            ess = []
            for row in range(start_row, end_row + 1):
                row_start_pos = rel_pos_to_abs_pos(lines, row, start_col)
                row_end_pos = rel_pos_to_abs_pos(lines, row, end_col)
                cursor = self.textCursor()
                if end_col >= start_col:
                    cursor.setPosition(row_start_pos)
                    cursor.setPosition(row_end_pos + 1, cursor.KeepAnchor)
                else:
                    cursor.setPosition(row_start_pos + 1)
                    cursor.setPosition(row_end_pos, cursor.KeepAnchor)
                ess.append(self._create_extra_selection(cursor))
            self.setExtraSelections(ess)

    def _create_extra_selection(
        self, cursor: QTextCursor
    ) -> QTextEdit.ExtraSelection:
        palette = self.palette()
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(palette.color(palette.Highlight))
        selection.format.setForeground(palette.color(palette.HighlightedText))
        selection.cursor = cursor
        return selection
