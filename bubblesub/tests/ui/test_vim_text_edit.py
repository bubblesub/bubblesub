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

"""Test VimTextEdit class."""

import re
from pathlib import Path
from typing import Any

import pytest
from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QWidget

from bubblesub.ui.vim_text_edit import VimTextEdit

KEYMAP = {
    "<CR>": Qt.Key.Key_Return,
    "<Esc>": Qt.Key.Key_Escape,
    "<BS>": Qt.Key.Key_Backspace,
    "<Del>": Qt.Key.Key_Delete,
    "<Right>": Qt.Key.Key_Right,
    "<Left>": Qt.Key.Key_Left,
    "<Up>": Qt.Key.Key_Up,
    "<Down>": Qt.Key.Key_Down,
    "<Home>": Qt.Key.Key_Home,
    "<End>": Qt.Key.Key_End,
}

TESTS = [
    ("", "", 0),
    ("ifoo", "foo", 3),
    ("ifoo<Esc>", "foo", 2),
    ("ifoo<CR>bar<Esc>", "foo\nbar", 6),
    ("ifoo<Esc>^", "foo", 0),
    ("ifoo<CR>bar<Esc>^", "foo\nbar", 4),
    ("ifoo<CR>bar<Esc>2^", "foo\nbar", 4),
    ("ifoo<Esc>0", "foo", 0),
    ("ifoo<CR>bar<Esc>0", "foo\nbar", 4),
    ("ifoo<CR>bar<Esc>20", "foo\nbar", 6),
    ("ifoo<Esc>^$", "foo", 2),
    ("ifoo<CR>bar<Esc>^$", "foo\nbar", 6),
    ("ifoo<CR>bar<CR>baz<Esc>gg2$", "foo\nbar\nbaz", 6),
    ("ifoo<Esc>2h", "foo", 0),
    ("ifoo bar<Esc>gg2w", "foo bar", 7),
    ("ifoo bar<CR>baz<Esc>gg2w", "foo bar\nbaz", 8),
    ("i foo <Esc>0w", " foo ", 1),
    ("i foo <Esc>02w", " foo ", 5),
    ("i  foo <Esc>0w", "  foo ", 2),
    ("i  foo <Esc>02w", "  foo ", 6),
    ("ifoo<CR><CR>bar<Esc>ggw", "foo\n\nbar", 4),
    ("ifoo<CR><CR>bar<Esc>gg2w", "foo\n\nbar", 5),
    ("ifoo<CR><CR>bar<Esc>gg3w", "foo\n\nbar", 8),
]


@pytest.fixture(scope="session")
def root_qt_widget() -> QWidget:
    """Construct a root QT widget that child objects can reference to avoid
    early garbage collection.

    :return: root QT widget for testing
    """
    return QWidget()


@pytest.fixture(scope="session")
def text_edit(  # pylint: disable=redefined-outer-name
    qapp: Any, root_qt_widget: QWidget
) -> QWidget:
    """Construct VimTextEdit instance for testing.

    :param qapp: test QApplication
    :param root_qt_widget: root widget
    :return: text edit instance
    """
    widget = VimTextEdit(parent=root_qt_widget)
    widget.vim_arguments = ["-u", str(Path(__file__).parent / "nvimrc")]
    widget.vim_mode_enabled = True
    return widget


@pytest.mark.parametrize(
    "keys,expected_text,expected_position",
    TESTS,
)
def test_vim_text_edit(  # pylint: disable=redefined-outer-name
    text_edit: VimTextEdit,
    keys: str,
    expected_text: str,
    expected_position: int,
) -> None:
    """Test VimTextEdit behavior.

    :param text_edit: VimTextEdit instance
    :param keys: keys to send to the input
    :param expected_text: expected text contents of the edit
    :param expected_position: expected caret position
    """
    text_edit.setPlainText("")
    text_edit.reset()
    for key in re.findall("<[^>]+>|.", keys):
        if key.startswith("<"):
            key_num = KEYMAP[key]
            key_text = ""
        else:
            key_num = Qt.Key(ord(key))
            key_text = key
        text_edit.keyPressEvent(
            QKeyEvent(
                QEvent.Type.KeyPress,
                key_num,
                Qt.KeyboardModifiers(),
                0,
                0,
                0,
                key_text,
            )
        )
        text_edit.keyReleaseEvent(
            QKeyEvent(
                QEvent.Type.KeyRelease,
                key_num,
                Qt.KeyboardModifiers(),
                0,
                0,
                0,
                key_text,
            )
        )

    assert text_edit.toPlainText() == expected_text
    assert text_edit.textCursor().position() == expected_position
