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

# pylint: disable=too-many-branches,too-many-statements,too-many-lines
import typing as T
from enum import Enum

from PyQt5 import QtCore, QtGui, QtWidgets


def is_keyword(character: str) -> bool:
    if character.isalnum() or character.isdigit():
        return True
    return character == "_"


def utf_class(character: str) -> int:
    classes = [
        (0x037E, 0x037E, 1),  # Greek question mark
        (0x0387, 0x0387, 1),  # Greek ano teleia
        (0x055A, 0x055F, 1),  # Armenian punctuation
        (0x0589, 0x0589, 1),  # Armenian full stop
        (0x05BE, 0x05BE, 1),
        (0x05C0, 0x05C0, 1),
        (0x05C3, 0x05C3, 1),
        (0x05F3, 0x05F4, 1),
        (0x060C, 0x060C, 1),
        (0x061B, 0x061B, 1),
        (0x061F, 0x061F, 1),
        (0x066A, 0x066D, 1),
        (0x06D4, 0x06D4, 1),
        (0x0700, 0x070D, 1),  # Syriac punctuation
        (0x0964, 0x0965, 1),
        (0x0970, 0x0970, 1),
        (0x0DF4, 0x0DF4, 1),
        (0x0E4F, 0x0E4F, 1),
        (0x0E5A, 0x0E5B, 1),
        (0x0F04, 0x0F12, 1),
        (0x0F3A, 0x0F3D, 1),
        (0x0F85, 0x0F85, 1),
        (0x104A, 0x104F, 1),  # Myanmar punctuation
        (0x10FB, 0x10FB, 1),  # Georgian punctuation
        (0x1361, 0x1368, 1),  # Ethiopic punctuation
        (0x166D, 0x166E, 1),  # Canadian Syl. punctuation
        (0x1680, 0x1680, 0),
        (0x169B, 0x169C, 1),
        (0x16EB, 0x16ED, 1),
        (0x1735, 0x1736, 1),
        (0x17D4, 0x17DC, 1),  # Khmer punctuation
        (0x1800, 0x180A, 1),  # Mongolian punctuation
        (0x2000, 0x200B, 0),  # spaces
        (0x200C, 0x2027, 1),  # punctuation and symbols
        (0x2028, 0x2029, 0),
        (0x202A, 0x202E, 1),  # punctuation and symbols
        (0x202F, 0x202F, 0),
        (0x2030, 0x205E, 1),  # punctuation and symbols
        (0x205F, 0x205F, 0),
        (0x2060, 0x27FF, 1),  # punctuation and symbols
        (0x2070, 0x207F, 0x2070),  # superscript
        (0x2080, 0x2094, 0x2080),  # subscript
        (0x20A0, 0x27FF, 1),  # all kinds of symbols
        (0x2800, 0x28FF, 0x2800),  # braille
        (0x2900, 0x2998, 1),  # arrows, brackets, etc.
        (0x29D8, 0x29DB, 1),
        (0x29FC, 0x29FD, 1),
        (0x2E00, 0x2E7F, 1),  # supplemental punctuation
        (0x3000, 0x3000, 0),  # ideographic space
        (0x3001, 0x3020, 1),  # ideographic punctuation
        (0x3030, 0x3030, 1),
        (0x303D, 0x303D, 1),
        (0x3040, 0x309F, 0x3040),  # Hiragana
        (0x30A0, 0x30FF, 0x30A0),  # Katakana
        (0x3300, 0x9FFF, 0x4E00),  # CJK Ideographs
        (0xAC00, 0xD7A3, 0xAC00),  # Hangul Syllables
        (0xF900, 0xFAFF, 0x4E00),  # CJK Ideographs
        (0xFD3E, 0xFD3F, 1),
        (0xFE30, 0xFE6B, 1),  # punctuation forms
        (0xFF00, 0xFF0F, 1),  # half/fullwidth ASCII
        (0xFF1A, 0xFF20, 1),  # half/fullwidth ASCII
        (0xFF3B, 0xFF40, 1),  # half/fullwidth ASCII
        (0xFF5B, 0xFF65, 1),  # half/fullwidth ASCII
        (0x1D000, 0x1D24F, 1),  # Musical notation
        (0x1D400, 0x1D7FF, 1),  # Mathematical Alphanumeric Symbols
        (0x1F000, 0x1F2FF, 1),  # Game pieces; enclosed characters
        (0x1F300, 0x1F9FF, 1),  # Many symbol blocks
        (0x20000, 0x2A6DF, 0x4E00),  # CJK Ideographs
        (0x2A700, 0x2B73F, 0x4E00),  # CJK Ideographs
        (0x2B740, 0x2B81F, 0x4E00),  # CJK Ideographs
        (0x2F800, 0x2FA1F, 0x4E00),  # CJK Ideographs
    ]

    if ord(character) < 0x100:
        if (
            character == " "
            or character == "\t"
            or character == "\0"
            or ord(character) == 0xA0
        ):
            return 0
        if is_keyword(character):
            return 2
        return 1

    bot = 0
    top = len(classes) - 1
    while top >= bot:
        mid = (bot + top) // 2
        if classes[mid][1] < ord(character):
            bot = mid + 1
        elif classes[mid][0] > ord(character):
            top = mid - 1
        else:
            return classes[mid][2]

    # if (intable(emoji_all, ARRAY_SIZE(emoji_all), c)) {
    #   return 3;
    # }

    return 2


def character_at(cursor: QtGui.QTextCursor) -> str:
    return cursor.document().characterAt(cursor.position())


def character_class(cursor: QtGui.QTextCursor, big: bool = False) -> int:
    character = character_at(cursor)
    if character in " \t\0":
        return 0
    cls = utf_class(character)
    if cls != 0 and big:
        return 1
    return cls


def get_selected_text_from_cursor(cursor: QtGui.QTextCursor) -> str:
    return cursor.selectedText().replace("\N{PARAGRAPH SEPARATOR}", "\n")


def is_empty_line(cursor: QtGui.QTextCursor) -> bool:
    return cursor.block().text() in {"\N{PARAGRAPH SEPARATOR}", "\n", ""}


class VimTextEditMode(Enum):
    Normal = "normal"
    Insert = "insert"
    GCommand = "g_command"
    Delete = "delete"
    GetOperatorCount = "get_operator_count"


class VimTextEditOperator(Enum):
    Delete = "delete"
    Change = "change"
    Yank = "yank"
    JumpToNextCharacter = "jump_to_next_character"
    JumpToPrevCharacter = "jump_to_prev_character"
    JumpBeforeNextCharacter = "jump_before_next_character"
    JumpBeforePrevCharacter = "jump_before_prev_character"
    TurnLowercase = "lowercase"
    TurnUppercase = "uppercase"


class VimTextEditSelectionMode(Enum):
    Character = "character"
    Line = "line"
    Block = "block"


class VimTextEdit(QtWidgets.QPlainTextEdit):
    def __init__(self, parent: QtWidgets.QWidget, **kwargs: T.Any) -> None:
        super().__init__(parent, **kwargs)
        self._mode = VimTextEditMode.Normal
        self._count: T.Optional[int] = None
        self._count_mul = 0
        self._count_reset = 0
        self._anchor: T.Optional[QtGui.QTextCursor] = None
        self._main_operator: T.Optional[VimTextEditOperator] = None
        self._jump_operator: T.Optional[VimTextEditOperator] = None
        self._last_jump_operator: T.Optional[VimTextEditOperator] = None
        self._additional_character = ""
        self._yanked_text = ""
        self._selection_mode: T.Optional[VimTextEditSelectionMode] = None
        self.reset()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        self.consume(event)

    def consume(self, event: QtGui.QKeyEvent) -> None:
        method_name = "consume_" + self._mode.value
        getattr(self, method_name)(event)

    def consume_normal(self, event: QtGui.QKeyEvent) -> None:
        if event.modifiers() & QtCore.Qt.ControlModifier:
            super().keyPressEvent(event)
            return

        if not event.text():
            return

        if self._jump_operator:
            self._additional_character = event.text()
            self._last_jump_operator = self._jump_operator
            self.exec_pending_operator()
            self._jump_operator = None
        elif event.text() == "i":
            self.insert()
        elif event.text() == "I":
            self.insert_sol()
        elif event.text() == "a":
            self.append()
        elif event.text() == "A":
            self.append(before=True)
        elif event.text() == "o":
            self.open_new_line()
        elif event.text() == "O":
            self.open_new_line(before=True)
        elif event.text() == "g":
            self.set_mode(VimTextEditMode.GCommand, reset=False)
        elif event.text() == "f":
            self._jump_operator = VimTextEditOperator.JumpToNextCharacter
        elif event.text() == "F":
            self._jump_operator = VimTextEditOperator.JumpToPrevCharacter
        elif event.text() == "t":
            self._jump_operator = VimTextEditOperator.JumpBeforeNextCharacter
        elif event.text() == "T":
            self._jump_operator = VimTextEditOperator.JumpBeforePrevCharacter
        elif event.text() == "Y":
            self.yank_line()
        elif event.text() == "y":
            if self._main_operator == VimTextEditOperator.Yank:
                self.yank_line()
            else:
                self._anchor = self.textCursor()
                self._main_operator = VimTextEditOperator.Yank
        elif event.text() == "P":
            self.paste(before=True)
        elif event.text() == "p":
            self.paste()
        elif event.text() == "d":
            if self._main_operator == VimTextEditOperator.Delete:
                self.delete_line()
            else:
                self._anchor = self.textCursor()
                self._main_operator = VimTextEditOperator.Delete
        elif event.text() == "c":
            if self._main_operator == VimTextEditOperator.Change:
                self.change_line()
            else:
                self._anchor = self.textCursor()
                self._main_operator = VimTextEditOperator.Change
        elif event.text() in "123456789":
            self.set_mode(VimTextEditMode.GetOperatorCount, reset=False)
            self._count = int(event.text())
        elif event.text() == "s":
            self.replace()
        elif event.text() == "C":
            self.replace_to_end_of_line()
        elif event.text() == "D":
            self.delete_to_end_of_line()
        elif event.text() == "S":
            self.replace_line()
        elif event.text() == "J":
            self.join_lines()
        elif event.text() == "w":
            if self._main_operator == VimTextEditOperator.Change:
                self.go_forward_end_word()
            else:
                self.go_forward_word()
            self.exec_pending_operator()
        elif event.text() == "e":
            self.go_forward_end_word()
            self.exec_pending_operator()
        elif event.text() == "W":
            if self._main_operator == VimTextEditOperator.Change:
                self.go_forward_end_word(big=True)
            else:
                self.go_forward_word(big=True)
            self.exec_pending_operator()
        elif event.text() == "E":
            self.go_forward_end_word(big=True)
            self.exec_pending_operator()
        elif event.key() == QtCore.Qt.Key_Backspace:
            self.backspace()
            self.exec_pending_operator()
        elif event.key() == QtCore.Qt.Key_Delete:
            self.delete()
            self.exec_pending_operator()
        elif event.text() == "~":
            self.tilde()
        elif event.text() == "|":
            self.pipe()
        elif (
            event.text() == "U"
            and self._main_operator == VimTextEditOperator.TurnUppercase
        ):
            self.uppercase_line()
            self.reset()
        elif (
            event.text() == "u"
            and self._main_operator == VimTextEditOperator.TurnLowercase
        ):
            self.lowercase_line()
            self.reset()
        else:
            method = {
                "G": self.go_to_last_line,
                "b": self.go_back_word,
                "B": lambda **kwargs: self.go_back_word(big=True, **kwargs),
                "h": self.go_left,
                "j": self.go_down,
                "k": self.go_up,
                "l": self.go_right,
                # "-": self.go_up,
                # "+": self.go_down,
                "0": self.go_to_beginning_of_line,
                "^": self.go_to_beginning_of_line,
                "$": self.go_to_end_of_line,
                "x": self.delete_character,
                "X": self.delete_backwards_character,
                ";": self.repeat_character_jump_forward,
                ",": self.repeat_character_jump_backward,
            }.get(event.text())

            # TODO: r
            # TODO: R

            # TODO: /
            # TODO: n
            # TODO: N
            # TODO: #
            # TODO: *

            # TODO: -
            # TODO: +

            # TODO: u
            # TODO: ctrl+r

            # TODO: v
            # TODO: V
            # TODO: ctrl-v

            if method:
                method()
                self.exec_pending_operator()
            else:
                self.reset()

    def consume_insert(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key_Escape:
            self.reset()
            self.go_left()
        else:
            super().keyPressEvent(event)

    def consume_get_operator_count(self, event: QtGui.QKeyEvent) -> None:
        if not event.text():
            return

        if event.key() == QtCore.Qt.Key_Escape:
            self.reset()
        elif event.text() in "0123456789":
            if self._count_reset == 1:
                self._count = 0
                self._count_reset = 2
            self._count *= 10
            self._count += int(event.text())
        else:
            if self._count_reset == 0:
                self._count_mul = self._count
                self._count_reset = 1
            elif self._count_reset == 2:
                self._count *= self._count_mul
            self.consume_normal(event)

    def consume_g_command(self, event: QtGui.QKeyEvent) -> None:
        if event.text() == "g":
            self.go_to_first_line()
            self.exec_pending_operator()
        elif event.text() == "u":
            if self._main_operator == VimTextEditOperator.TurnLowercase:
                self.lowercase_line()
                self.reset()
            else:
                self.set_mode(VimTextEditMode.Normal, reset=False)
                self._anchor = self.textCursor()
                self._main_operator = VimTextEditOperator.TurnLowercase
        elif event.text() == "U":
            if self._main_operator == VimTextEditOperator.TurnUppercase:
                self.uppercase_line()
                self.reset()
            else:
                self.set_mode(VimTextEditMode.Normal, reset=False)
                self._anchor = self.textCursor()
                self._main_operator = VimTextEditOperator.TurnUppercase
        else:
            self.reset()

    def get_mode(self) -> VimTextEditMode:
        return self._mode

    def set_mode(self, mode: VimTextEditMode, reset: bool = True) -> None:
        self._mode = mode
        if reset:
            self._main_operator = None
            self._jump_operator = None
            self._count = None
            self._count_mul = 1
            self._selection_mode = None
        self.setCursorWidth(1 if self._mode == VimTextEditMode.Insert else 10)

    def go_left(self) -> None:
        cursor = self.textCursor()
        for _ in range(self._count or 1):
            if cursor.positionInBlock() > 0:
                cursor.movePosition(QtGui.QTextCursor.Left)
                self.setTextCursor(cursor)

    def go_right(self) -> None:
        cursor = self.textCursor()
        for _ in range(self._count or 1):
            if cursor.positionInBlock() < cursor.block().length() - 1:
                cursor.movePosition(QtGui.QTextCursor.Right)
                self.setTextCursor(cursor)

    def go_up(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(
            QtGui.QTextCursor.Up,
            QtGui.QTextCursor.MoveAnchor,
            self._count or 1,
        )
        self.setTextCursor(cursor)
        if self._main_operator and not self._selection_mode:
            self._selection_mode = VimTextEditSelectionMode.Line

    def go_down(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(
            QtGui.QTextCursor.Down,
            QtGui.QTextCursor.MoveAnchor,
            self._count or 1,
        )
        if self._main_operator and not self._selection_mode:
            self._selection_mode = VimTextEditSelectionMode.Line
        self.setTextCursor(cursor)

    def go_back_word(self, big: bool = False) -> None:
        for _ in range(self._count or 1):
            self.go_back_one_word(big=big)

    def go_forward_word(self, big: bool = False) -> None:
        for _ in range(self._count or 1):
            self.go_forward_one_word(big=big)

    def go_forward_end_word(self, big: bool = False) -> None:
        for _ in range(self._count or 1):
            self.go_forward_one_end_word(big=big)
        if self._main_operator and not self._selection_mode:
            self._count = 1
            self.go_right()

    def go_back_one_word(self, big: bool = False) -> None:
        cursor = self.textCursor()
        if cursor.movePosition(QtGui.QTextCursor.Left):
            while character_class(cursor, big=big) == 0:
                if is_empty_line(cursor):
                    self.setTextCursor(cursor)
                    return
                if not cursor.movePosition(QtGui.QTextCursor.Left):
                    break

            cls = character_class(cursor, big=big)
            while character_class(cursor, big=big) == cls:
                if not cursor.movePosition(QtGui.QTextCursor.Left):
                    break
            else:
                # overshot
                cursor.movePosition(
                    QtGui.QTextCursor.Right, QtGui.QTextCursor.MoveAnchor,
                )

        self.setTextCursor(cursor)

    def go_forward_one_word(self, big: bool = False) -> None:
        cursor = self.textCursor()
        if cursor.position() == cursor.document().characterCount() - 1:
            return

        cls = character_class(cursor, big=big)
        cursor.movePosition(QtGui.QTextCursor.Right)

        while character_class(cursor, big=big) == cls:
            if not cursor.movePosition(QtGui.QTextCursor.Right):
                break

        while (
            character_class(cursor, big=big) == 0
            or character_at(cursor) == "\n"
        ):
            if is_empty_line(cursor):
                self.setTextCursor(cursor)
                return
            if not cursor.movePosition(QtGui.QTextCursor.Right):
                break

        self.setTextCursor(cursor)

    def go_forward_one_end_word(self, big: bool = False) -> None:
        cursor = self.textCursor()
        if cursor.position() == cursor.document().characterCount() - 1:
            return

        cls = character_class(cursor, big=big)
        cursor.movePosition(QtGui.QTextCursor.Right)

        if character_class(cursor, big=big) == cls and cls != 0:
            while character_class(cursor, big=big) == cls:
                cursor.movePosition(QtGui.QTextCursor.Right)
                if cursor.positionInBlock() == cursor.block().length() - 1:
                    break
        else:
            while character_class(cursor, big=big) == 0:
                if cursor.positionInBlock() == cursor.block().length() - 1:
                    self.setTextCursor(cursor)
                    return
                cursor.movePosition(QtGui.QTextCursor.Right)

            cls = character_class(cursor, big=big)
            while character_class(cursor, big=big) == cls:
                if cursor.positionInBlock() == cursor.block().length() - 1:
                    self.setTextCursor(cursor)
                    return
                cursor.movePosition(QtGui.QTextCursor.Right)

        # overshot
        cursor.movePosition(QtGui.QTextCursor.Left)
        self.setTextCursor(cursor)

    def go_to_first_line(self) -> None:
        if self._count is not None:
            self.go_to_specific_line()
            return
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.Start)
        self.setTextCursor(cursor)
        if self._main_operator and not self._selection_mode:
            self._selection_mode = VimTextEditSelectionMode.Line

    def go_to_last_line(self) -> None:
        if self._count is not None:
            self.go_to_specific_line()
            return
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        self.setTextCursor(cursor)
        if self._main_operator and not self._selection_mode:
            self._selection_mode = VimTextEditSelectionMode.Line

    def go_to_specific_line(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.Start)
        if self._count and self._count > 1:
            cursor.movePosition(
                QtGui.QTextCursor.Down,
                QtGui.QTextCursor.MoveAnchor,
                self._count - 1,
            )
        self.setTextCursor(cursor)
        if self._main_operator and not self._selection_mode:
            self._selection_mode = VimTextEditSelectionMode.Line

    def go_to_beginning_of_line(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        self.setTextCursor(cursor)

    def go_to_end_of_line(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(
            QtGui.QTextCursor.Down,
            QtGui.QTextCursor.MoveAnchor,
            (self._count or 1) - 1,
        )
        cursor.movePosition(QtGui.QTextCursor.EndOfLine)
        if not self._main_operator:
            cursor.movePosition(QtGui.QTextCursor.Left)
        self.setTextCursor(cursor)

    def delete_character(self) -> None:
        cursor = self.textCursor()
        for _ in range(self._count or 1):
            if cursor.positionInBlock() == cursor.block().length() - 1:
                break
            cursor.movePosition(
                QtGui.QTextCursor.Right, QtGui.QTextCursor.KeepAnchor,
            )
        self._yanked_text = get_selected_text_from_cursor(cursor)
        cursor.removeSelectedText()

    def delete_backwards_character(self) -> None:
        cursor = self.textCursor()
        for _ in range(self._count or 1):
            if cursor.positionInBlock() == 0:
                break
            cursor.movePosition(
                QtGui.QTextCursor.Left, QtGui.QTextCursor.KeepAnchor,
            )
        self._yanked_text = get_selected_text_from_cursor(cursor)
        cursor.removeSelectedText()

    def select_cursor_for_operator_line(
        self,
    ) -> T.Tuple[QtGui.QTextCursor, bool]:
        cursor = self.textCursor()
        if not cursor.movePosition(QtGui.QTextCursor.Up):
            before = True
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
            if not cursor.movePosition(
                QtGui.QTextCursor.Down,
                QtGui.QTextCursor.KeepAnchor,
                self._count or 1,
            ):
                cursor.movePosition(
                    QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor,
                )
        else:
            before = False
            cursor.movePosition(QtGui.QTextCursor.EndOfLine)
            cursor.movePosition(
                QtGui.QTextCursor.Down,
                QtGui.QTextCursor.KeepAnchor,
                self._count or 1,
            )
            cursor.movePosition(
                QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor
            )
        return cursor, before

    def yank_line(self) -> None:
        cursor, _ = self.select_cursor_for_operator_line()
        self._yanked_text = get_selected_text_from_cursor(cursor)
        if not self._yanked_text.endswith("\n"):
            self._yanked_text += "\n"
        self.reset()

    def lowercase_line(self) -> None:
        old_pos = self.textCursor().position()
        cursor, _ = self.select_cursor_for_operator_line()
        text = "".join(
            c.lower() for c in get_selected_text_from_cursor(cursor)
        )
        cursor.insertText(text)
        cursor.setPosition(old_pos)
        if text.count("\n") == 1:
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        self.setTextCursor(cursor)
        self.reset()

    def uppercase_line(self) -> None:
        old_pos = self.textCursor().position()
        cursor, _ = self.select_cursor_for_operator_line()
        text = "".join(
            c.upper() for c in get_selected_text_from_cursor(cursor)
        )
        cursor.insertText(text)
        cursor.setPosition(old_pos)
        if text.count("\n") == 1:
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        self.setTextCursor(cursor)
        self.reset()

    def delete_line(self) -> None:
        cursor, before = self.select_cursor_for_operator_line()
        self._yanked_text = get_selected_text_from_cursor(cursor)
        if not self._yanked_text.endswith("\n"):
            self._yanked_text += "\n"
        cursor.removeSelectedText()
        if before:
            cursor.movePosition(
                QtGui.QTextCursor.StartOfLine, QtGui.QTextCursor.KeepAnchor
            )
        else:
            cursor.movePosition(QtGui.QTextCursor.Down)
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        self.setTextCursor(cursor)
        self.reset()

    def change_line(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        if (self._count or 1) > 1:
            cursor.movePosition(
                QtGui.QTextCursor.Down,
                self._count - 1,
                QtGui.QTextCursor.KeepAnchor,
            )
        cursor.movePosition(
            QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor
        )
        self._yanked_text = get_selected_text_from_cursor(cursor)
        if not self._yanked_text.endswith("\n"):
            self._yanked_text += "\n"
        cursor.removeSelectedText()
        self.setTextCursor(cursor)
        self.insert()

    def replace(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(
            QtGui.QTextCursor.Right,
            QtGui.QTextCursor.KeepAnchor,
            self._count or 1,
        )
        cursor.removeSelectedText()
        self.setTextCursor(cursor)
        self.set_mode(VimTextEditMode.Insert)

    def reset(self) -> None:
        self.set_mode(VimTextEditMode.Normal)

    def insert(self) -> None:
        if self._mode == VimTextEditMode.Insert:
            return
        self.set_mode(VimTextEditMode.Insert)

    def insert_sol(self) -> None:
        if self._mode == VimTextEditMode.Insert:
            return
        self.set_mode(VimTextEditMode.Insert)
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        self.setTextCursor(cursor)

    def append(self, before: bool = False) -> None:
        if self._mode == VimTextEditMode.Insert:
            return
        self.set_mode(VimTextEditMode.Insert)
        cursor = self.textCursor()
        if before:
            cursor.movePosition(QtGui.QTextCursor.EndOfLine)
            self.setTextCursor(cursor)
        elif cursor.positionInBlock() < cursor.block().length() - 1:
            cursor.movePosition(QtGui.QTextCursor.Right)
            self.setTextCursor(cursor)

    def open_new_line(self, before: bool = False) -> None:
        if self._mode == VimTextEditMode.Insert:
            return
        self.set_mode(VimTextEditMode.Insert)
        cursor = self.textCursor()
        if before:
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        else:
            cursor.movePosition(QtGui.QTextCursor.EndOfLine)
            self.setTextCursor(cursor)
        cursor.insertText("\n")
        if before:
            cursor.movePosition(QtGui.QTextCursor.Up)
            self.setTextCursor(cursor)

    def select_cursor_for_operator(
        self, lines: bool
    ) -> T.Tuple[QtGui.QTextCursor, bool]:
        old_pos = self._anchor.position()
        new_pos = self.textCursor().position()

        cursor = self.textCursor()
        if old_pos <= new_pos:
            cursor.setPosition(old_pos)
            if (
                self._selection_mode
                and self._selection_mode == VimTextEditSelectionMode.Line
            ):
                cursor.movePosition(QtGui.QTextCursor.StartOfLine)
            cursor.setPosition(new_pos, QtGui.QTextCursor.KeepAnchor)
            if (
                self._selection_mode
                and self._selection_mode == VimTextEditSelectionMode.Line
            ):
                if not lines and cursor.movePosition(
                    QtGui.QTextCursor.Down, QtGui.QTextCursor.KeepAnchor
                ):
                    cursor.movePosition(
                        QtGui.QTextCursor.StartOfLine,
                        QtGui.QTextCursor.KeepAnchor,
                    )
                else:
                    cursor.movePosition(
                        QtGui.QTextCursor.EndOfLine,
                        QtGui.QTextCursor.KeepAnchor,
                    )

        else:
            cursor.setPosition(old_pos)
            if (
                self._selection_mode
                and self._selection_mode == VimTextEditSelectionMode.Line
            ):
                cursor.movePosition(QtGui.QTextCursor.StartOfLine)
                if not cursor.movePosition(QtGui.QTextCursor.Down):
                    cursor.movePosition(QtGui.QTextCursor.EndOfLine)
            cursor.setPosition(new_pos, QtGui.QTextCursor.KeepAnchor)
            if (
                self._selection_mode
                and self._selection_mode == VimTextEditSelectionMode.Line
            ):
                if not lines and cursor.movePosition(
                    QtGui.QTextCursor.Up, QtGui.QTextCursor.KeepAnchor
                ):
                    cursor.movePosition(
                        QtGui.QTextCursor.EndOfLine,
                        QtGui.QTextCursor.KeepAnchor,
                    )
                else:
                    cursor.movePosition(
                        QtGui.QTextCursor.StartOfLine,
                        QtGui.QTextCursor.KeepAnchor,
                    )

        return cursor

    def operator_yank(self) -> None:
        old_pos = self._anchor.position()
        new_pos = self.textCursor().position()
        cursor = self.select_cursor_for_operator(lines=False)
        self._yanked_text = get_selected_text_from_cursor(cursor)
        if old_pos <= new_pos:
            cursor.setPosition(old_pos)
            self.setTextCursor(cursor)
        self.reset()

    def operator_delete(self) -> None:
        cursor = self.select_cursor_for_operator(lines=False)
        self._yanked_text = get_selected_text_from_cursor(cursor)
        cursor.removeSelectedText()
        if self._selection_mode == VimTextEditSelectionMode.Line:
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        self.setTextCursor(cursor)
        self.reset()

    def operator_change(self) -> None:
        cursor = self.select_cursor_for_operator(lines=True)
        self._yanked_text = get_selected_text_from_cursor(cursor)
        cursor.removeSelectedText()
        if self._selection_mode == VimTextEditSelectionMode.Line:
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        self.setTextCursor(cursor)
        self.insert()

    def operator_lowercase(self) -> None:
        old_pos = self._anchor.position()
        new_pos = self.textCursor().position()
        cursor = self.select_cursor_for_operator(lines=True)
        self._yanked_text = get_selected_text_from_cursor(cursor)
        cursor.insertText(
            "".join(c.lower() for c in get_selected_text_from_cursor(cursor))
        )
        if old_pos <= new_pos:
            cursor.setPosition(old_pos)
            self.setTextCursor(cursor)
        self.reset()

    def operator_uppercase(self) -> None:
        old_pos = self._anchor.position()
        new_pos = self.textCursor().position()
        cursor = self.select_cursor_for_operator(lines=True)
        self._yanked_text = get_selected_text_from_cursor(cursor)
        cursor.insertText(
            "".join(c.upper() for c in get_selected_text_from_cursor(cursor))
        )
        if old_pos <= new_pos:
            cursor.setPosition(old_pos)
            self.setTextCursor(cursor)
        self.reset()

    def jump_to_next_character(self) -> None:
        cursor = self.textCursor()
        if cursor.positionInBlock() == cursor.block().length() - 1:
            return
        for _ in range(self._count or 1):
            cursor.movePosition(QtGui.QTextCursor.Right)
            while character_at(cursor) != self._additional_character:
                if character_at(cursor) in {"\n", "\N{PARAGRAPH SEPARATOR}"}:
                    return
                cursor.movePosition(QtGui.QTextCursor.Right)
        if self._main_operator:
            cursor.movePosition(QtGui.QTextCursor.Right)
        self.setTextCursor(cursor)

    def jump_to_prev_character(self) -> None:
        cursor = self.textCursor()
        for _ in range(self._count or 1):
            cursor.movePosition(QtGui.QTextCursor.Left)
            while character_at(cursor) != self._additional_character:
                if character_at(cursor) in {"\n", "\N{PARAGRAPH SEPARATOR}"}:
                    return
                if not cursor.movePosition(QtGui.QTextCursor.Left):
                    return
        self.setTextCursor(cursor)

    def jump_before_next_character(self) -> None:
        cursor = self.textCursor()
        for _ in range(self._count or 1):
            cursor.movePosition(QtGui.QTextCursor.Right)
            while character_at(cursor) != self._additional_character:
                if character_at(cursor) in {"\n", "\N{PARAGRAPH SEPARATOR}"}:
                    return
                cursor.movePosition(QtGui.QTextCursor.Right)
        cursor.movePosition(QtGui.QTextCursor.Left)
        if self._main_operator:
            cursor.movePosition(QtGui.QTextCursor.Right)
        self.setTextCursor(cursor)

    def jump_before_prev_character(self) -> None:
        cursor = self.textCursor()
        for _ in range(self._count or 1):
            cursor.movePosition(QtGui.QTextCursor.Left)
            while character_at(cursor) != self._additional_character:
                if character_at(cursor) in {"\n", "\N{PARAGRAPH SEPARATOR}"}:
                    return
                if not cursor.movePosition(QtGui.QTextCursor.Left):
                    return
        cursor.movePosition(QtGui.QTextCursor.Right)
        self.setTextCursor(cursor)

    def repeat_character_jump_forward(self) -> None:
        if not self._last_jump_operator:
            return
        method = getattr(self, self._last_jump_operator.value)
        method()

    def repeat_character_jump_backward(self) -> None:
        if not self._last_jump_operator:
            return
        method = getattr(
            self,
            {
                VimTextEditOperator.JumpToNextCharacter: (
                    VimTextEditOperator.JumpToPrevCharacter
                ),
                VimTextEditOperator.JumpToPrevCharacter: (
                    VimTextEditOperator.JumpToNextCharacter
                ),
                VimTextEditOperator.JumpBeforeNextCharacter: (
                    VimTextEditOperator.JumpBeforePrevCharacter
                ),
                VimTextEditOperator.JumpBeforePrevCharacter: (
                    VimTextEditOperator.JumpBeforeNextCharacter
                ),
            }[self._last_jump_operator].value,
        )
        method()

    def paste(self, before: bool = False) -> None:
        if not self._yanked_text:
            return
        if "\n" in self._yanked_text:
            cursor = self.textCursor()
            if before:
                cursor.movePosition(QtGui.QTextCursor.StartOfLine)
                pos = cursor.position()
                cursor.insertText(self._yanked_text)
            else:
                cursor.movePosition(QtGui.QTextCursor.EndOfLine)
                cursor.insertText("\n")
                pos = cursor.position()
                if self._yanked_text.endswith("\n"):
                    cursor.insertText(self._yanked_text[:-1])
                else:
                    cursor.insertText(self._yanked_text)
            cursor.setPosition(pos)
            self.setTextCursor(cursor)
        else:
            cursor = self.textCursor()
            if (
                not before
                and cursor.positionInBlock() < cursor.block().length() - 1
            ):
                cursor.movePosition(QtGui.QTextCursor.Right)
            cursor.insertText(self._yanked_text)
            if cursor.positionInBlock() > 0:
                cursor.movePosition(QtGui.QTextCursor.Left)
            self.setTextCursor(cursor)

    def exec_pending_operator(self) -> None:
        if self._jump_operator:
            method = getattr(self, self._jump_operator.value)
            method()
        if self._main_operator:
            method = getattr(self, "operator_" + self._main_operator.value)
            method()
        else:
            self.reset()

    def replace_to_end_of_line(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(
            QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor
        )
        self._yanked_text = get_selected_text_from_cursor(cursor)
        cursor.removeSelectedText()
        self.insert()

    def delete_to_end_of_line(self) -> None:
        cursor = self.textCursor()
        if not cursor.movePosition(
            QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor
        ):
            if cursor.positionInBlock() > 0:
                cursor.movePosition(
                    QtGui.QTextCursor.Left, QtGui.QTextCursor.KeepAnchor
                )
            else:
                return
        self._yanked_text = get_selected_text_from_cursor(cursor)
        cursor.removeSelectedText()
        self.reset()

    def replace_line(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        cursor.movePosition(
            QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor
        )
        cursor.removeSelectedText()
        self.insert()

    def join_lines(self) -> None:
        for _ in range(self._count - 1 if self._count else 1):
            cursor = self.textCursor()
            if not cursor.movePosition(QtGui.QTextCursor.Down):
                break

            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.EndOfLine)

            if cursor.positionInBlock() > 0:
                cursor.movePosition(QtGui.QTextCursor.Left)
                has_whitespace = character_class(cursor) == 0
                cursor.movePosition(QtGui.QTextCursor.Right)

            cursor.movePosition(
                QtGui.QTextCursor.Right, QtGui.QTextCursor.KeepAnchor
            )
            while character_class(cursor) == 0:
                if not cursor.movePosition(
                    QtGui.QTextCursor.Right, QtGui.QTextCursor.KeepAnchor
                ):
                    break
            cursor.removeSelectedText()
            if not has_whitespace:
                cursor.insertText(" ")
                cursor.movePosition(QtGui.QTextCursor.Left)
            self.setTextCursor(cursor)

    def backspace(self) -> None:
        cursor = self.textCursor()
        for _ in range(self._count or 1):
            if cursor.positionInBlock() > 0:
                cursor.movePosition(QtGui.QTextCursor.Left)
            else:
                if not cursor.movePosition(QtGui.QTextCursor.Up):
                    break
                cursor.movePosition(QtGui.QTextCursor.EndOfLine)
                if cursor.positionInBlock() > 0:
                    cursor.movePosition(QtGui.QTextCursor.Left)
        self.setTextCursor(cursor)

    def delete(self) -> None:
        if self._count is not None or self._main_operator:
            self.reset()
            return
        cursor = self.textCursor()
        if cursor.positionInBlock() < cursor.block().length() - 1:
            cursor.movePosition(
                QtGui.QTextCursor.Right, QtGui.QTextCursor.KeepAnchor
            )
            cursor.removeSelectedText()

    def tilde(self) -> None:
        cursor = self.textCursor()
        for _ in range(self._count or 1):
            if cursor.positionInBlock() < cursor.block().length() - 1:
                cursor.movePosition(
                    QtGui.QTextCursor.Right, QtGui.QTextCursor.KeepAnchor
                )
        cursor.insertText(
            "".join(
                c.lower() if c.isupper() else c.upper()
                for c in get_selected_text_from_cursor(cursor)
            )
        )
        self.setTextCursor(cursor)
        self.reset()

    def pipe(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        for _ in range(self._count - 1 if self._count else 0):
            if cursor.positionInBlock() < cursor.block().length() - 1:
                cursor.movePosition(QtGui.QTextCursor.Right)
        self.setTextCursor(cursor)
        self.exec_pending_operator()
