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
import typing as T

import pytest
from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.ui.vim_text_edit import VimTextEdit

KEYMAP = {
    "<CR>": QtCore.Qt.Key_Return,
    "<Esc>": QtCore.Qt.Key_Escape,
    "<BS>": QtCore.Qt.Key_Backspace,
    "<Del>": QtCore.Qt.Key_Delete,
    "<Right>": QtCore.Qt.Key_Right,
    "<Left>": QtCore.Qt.Key_Left,
    "<Up>": QtCore.Qt.Key_Up,
    "<Down>": QtCore.Qt.Key_Down,
    "<Home>": QtCore.Qt.Key_Home,
    "<End>": QtCore.Qt.Key_End,
}

TESTS = []

# basic tests
TESTS += [
    ("", "", 0),
    ("ifoo", "foo", 3),
    ("ifoo<Esc>", "foo", 2),
    ("ifoo<CR>bar<Esc>", "foo\nbar", 6),
]

# test gg
TESTS += [
    ("ifoo<Esc>gg", "foo", 0),
    ("ifoo<CR>bar<Esc>gg", "foo\nbar", 0),
]

# test G
TESTS += [
    ("ifoo<Esc>ggG", "foo", 0),
    ("ifoo<Esc>gglG", "foo", 0),
    ("ifoo<CR>bar<Esc>ggG", "foo\nbar", 4),
]

# test ^
TESTS += [
    ("ifoo<Esc>^", "foo", 0),
    ("ifoo<CR>bar<Esc>^", "foo\nbar", 4),
    ("ifoo<CR>bar<Esc>2^", "foo\nbar", 4),
]

# test 0
TESTS += [
    ("ifoo<Esc>0", "foo", 0),
    ("ifoo<CR>bar<Esc>0", "foo\nbar", 4),
    ("ifoo<CR>bar<Esc>20", "foo\nbar", 6),
]

# test $
TESTS += [
    ("ifoo<Esc>^$", "foo", 2),
    ("ifoo<CR>bar<Esc>^$", "foo\nbar", 6),
    ("ifoo<CR>bar<CR>baz<Esc>gg2$", "foo\nbar\nbaz", 6),
]

# test h
TESTS += [
    ("ifoo<Esc>h", "foo", 1),
    ("ifoo<Esc>hh", "foo", 0),
    ("ifoo<Esc>hhh", "foo", 0),
    ("ifoo<Esc>1h", "foo", 1),
    ("ifoo<Esc>2h", "foo", 0),
    ("ifoo<Esc>3h", "foo", 0),
    ("ifoo<CR>bar<Esc>h", "foo\nbar", 5),
    ("ifoo<CR>bar<Esc>3h", "foo\nbar", 4),
]

# test l
TESTS += [
    ("ifoo<Esc>10hl", "foo", 1),
    ("ifoo<Esc>10h2l", "foo", 2),
    ("ifoo<Esc>10h4l", "foo", 3),
    ("ifoo<CR>bar<Esc>ggl", "foo\nbar", 1),
    ("ifoo<CR>bar<Esc>gg4l", "foo\nbar", 3),
]

# test j
TESTS += [
    ("ifoo<Esc>j", "foo", 2),
    ("ifoo<CR>bar<CR>baz<Esc>ggj", "foo\nbar\nbaz", 4),
    ("ifoo<CR>bar<CR>baz<Esc>gglj", "foo\nbar\nbaz", 5),
    ("ifoo<CR>bar<CR>baz<Esc>gg2j", "foo\nbar\nbaz", 8),
    ("ifoo<CR>bar<CR>baz<Esc>ggl2j", "foo\nbar\nbaz", 9),
]

# test k
TESTS += [
    ("ifoo<Esc>k", "foo", 2),
    ("ifoo<CR>bar<CR>baz<Esc>Gk", "foo\nbar\nbaz", 4),
    ("ifoo<CR>bar<CR>baz<Esc>Glk", "foo\nbar\nbaz", 5),
    ("ifoo<CR>bar<CR>baz<Esc>G2k", "foo\nbar\nbaz", 0),
    ("ifoo<CR>bar<CR>baz<Esc>Gl2k", "foo\nbar\nbaz", 1),
]

# test b
TESTS += [
    ("ifoo bar<Esc>b", "foo bar", 4),
    ("ifoo bar<Esc>bb", "foo bar", 0),
    ("ifoo()bar baz<Esc>b", "foo()bar baz", 9),
    ("ifoo()bar baz<Esc>bb", "foo()bar baz", 5),
    ("ifoo()bar baz<Esc>bbb", "foo()bar baz", 3),
    ("ifoo()bar baz<Esc>bbbb", "foo()bar baz", 0),
    ("ifoo()bar baz<Esc>1b", "foo()bar baz", 9),
    ("ifoo()bar baz<Esc>2b", "foo()bar baz", 5),
    ("ifoo()bar baz<Esc>3b", "foo()bar baz", 3),
    ("ifoo()bar baz<Esc>4b", "foo()bar baz", 0),
    ("i asd <Esc>l", " asd ", 5),
    ("i asd <Esc>lb", " asd ", 1),
    ("i asd  <Esc>lb", " asd  ", 1),
    ("i  asd <Esc>lb", "  asd ", 2),
    ("i  asd <Esc>l2b", "  asd ", 0),
    ("ifoo<CR><CR>bar<Esc>b", "foo\n\nbar", 5),
    ("ifoo<CR><CR>bar<Esc>2b", "foo\n\nbar", 4),
    ("ifoo<CR>x<CR>bar<Esc>2b", "foo\nx\nbar", 4),
]

# test B
TESTS += [
    ("ifoo()bar baz<Esc>B", "foo()bar baz", 9),
    ("ifoo()bar baz<Esc>BB", "foo()bar baz", 0),
    ("ifoo()bar baz<Esc>BBB", "foo()bar baz", 0),
    ("ifoo()bar baz<Esc>1B", "foo()bar baz", 9),
    ("ifoo()bar baz<Esc>2B", "foo()bar baz", 0),
    ("ifoo()bar baz<Esc>3B", "foo()bar baz", 0),
    ("i asd <Esc>lB", " asd ", 1),
    ("i asd  <Esc>lB", " asd  ", 1),
    ("i  asd <Esc>lB", "  asd ", 2),
    ("i  asd <Esc>l2B", "  asd ", 0),
    ("ifoo<CR><CR>bar<Esc>B", "foo\n\nbar", 5),
    ("ifoo<CR><CR>bar<Esc>2B", "foo\n\nbar", 4),
]

# test w
TESTS += [
    ("ifoo bar<Esc>ggw", "foo bar", 4),
    ("ifoo bar<Esc>gg2w", "foo bar", 7),
    ("ifoo()bar<Esc>ggw", "foo()bar", 3),
    ("ifoo()bar<Esc>gg2w", "foo()bar", 5),
    ("ifoo()bar<Esc>gg3w", "foo()bar", 8),
    ("ifoo bar<CR>baz<Esc>gg2w", "foo bar\nbaz", 8),
    ("i foo <Esc>0w", " foo ", 1),
    ("i foo <Esc>02w", " foo ", 5),
    ("i  foo <Esc>0w", "  foo ", 2),
    ("i  foo <Esc>02w", "  foo ", 6),
    ("ifoo<CR><CR>bar<Esc>ggw", "foo\n\nbar", 4),
    ("ifoo<CR><CR>bar<Esc>gg2w", "foo\n\nbar", 5),
    ("ifoo<CR><CR>bar<Esc>gg3w", "foo\n\nbar", 8),
]

# test W
TESTS += [
    ("ifoo bar<Esc>ggW", "foo bar", 4),
    ("ifoo bar<Esc>gg2W", "foo bar", 7),
    ("i foo <Esc>0W", " foo ", 1),
    ("i foo <Esc>02W", " foo ", 5),
    ("i  foo <Esc>0W", "  foo ", 2),
    ("i  foo <Esc>02W", "  foo ", 6),
    ("ifoo()bar<Esc>ggW", "foo()bar", 8),
    ("ifoo()bar baz<Esc>ggW", "foo()bar baz", 9),
    ("ifoo()bar baz<Esc>gg2W", "foo()bar baz", 12),
    ("ifoo()bar baz<Esc>gg3W", "foo()bar baz", 12),
    ("ifoo bar<CR>baz<Esc>gg2W", "foo bar\nbaz", 8),
    ("ifoo<CR><CR>bar<Esc>ggW", "foo\n\nbar", 4),
    ("ifoo<CR><CR>bar<Esc>gg2W", "foo\n\nbar", 5),
    ("ifoo<CR><CR>bar<Esc>gg3W", "foo\n\nbar", 8),
]

# test e
TESTS += [
    ("ifoo<Esc>gge", "foo", 2),
    ("ifoo<Esc>ggle", "foo", 2),
    ("ifoo<Esc>gg2le", "foo", 3),
    ("ifoo bar<Esc>gge", "foo bar", 2),
    ("ifoo bar<Esc>gg3le", "foo bar", 6),
    ("ifoo bar<Esc>gg2e", "foo bar", 6),
    ("ifoo()bar<Esc>gge", "foo()bar", 2),
    ("ifoo()bar<Esc>gg2e", "foo()bar", 4),
    ("ifoo()bar<Esc>gg3e", "foo()bar", 7),
    ("ifoo bar<CR>baz<Esc>gg2e", "foo bar\nbaz", 6),
    ("i foo <Esc>gge", " foo ", 3),
    ("i foo <Esc>gg2e", " foo ", 5),
    ("i  foo <Esc>gge", "  foo ", 4),
    ("i  foo <Esc>gg2e", "  foo ", 6),
]

# test E
TESTS += [
    ("ifoo<Esc>ggE", "foo", 2),
    ("ifoo<Esc>gglE", "foo", 2),
    ("ifoo<Esc>gg2lE", "foo", 3),
    ("ifoo bar<Esc>ggE", "foo bar", 2),
    ("ifoo bar<Esc>gg3lE", "foo bar", 6),
    ("ifoo bar<Esc>gg2E", "foo bar", 6),
    ("ifoo()bar<Esc>ggE", "foo()bar", 7),
    ("ifoo()bar<Esc>gg2E", "foo()bar", 8),
    ("ifoo()bar<Esc>gg3E", "foo()bar", 8),
    ("ifoo bar<CR>baz<Esc>gg2E", "foo bar\nbaz", 6),
    ("i foo <Esc>ggE", " foo ", 3),
    ("i foo <Esc>gg2E", " foo ", 5),
    ("i  foo <Esc>ggE", "  foo ", 4),
    ("i  foo <Esc>gg2E", "  foo ", 6),
]

# test f
TESTS += [
    ("ifoo bar baz<Esc>^fb", "foo bar baz", 4),
    ("ifoo bar baz<Esc>^fz", "foo bar baz", 10),
    ("ifoo bar baz<Esc>^2fb", "foo bar baz", 8),
    ("ifoo bar baz<Esc>^3fb", "foo bar baz", 0),
    ("ifoo bar<CR>baz<Esc>ggfb", "foo bar\nbaz", 4),
    ("ifoo bar<CR>baz<Esc>ggl2fb", "foo bar\nbaz", 1),
    ("ifoo bar<CR>baz<Esc>ggfz", "foo bar\nbaz", 0),
    ("ifoo<CR>bar<Esc>gg$fb", "foo\nbar", 2),
    ("ifoo<CR>bar<Esc>gg$lfb", "foo\nbar", 3),
]

# test F
TESTS += [
    ("ifoo bar baz<Esc>$Fb", "foo bar baz", 8),
    ("ifoo bar baz<Esc>$2Fb", "foo bar baz", 4),
    ("ifoo bar baz<Esc>$3Fb", "foo bar baz", 10),
    ("ifoo bar<CR>baz<Esc>G$Fb", "foo bar\nbaz", 8),
    ("ifoo bar<CR>baz<Esc>G$2Fb", "foo bar\nbaz", 10),
    ("ifoo<CR>bar<Esc>^Fo", "foo\nbar", 4),
    ("ifoo<CR>bar<Esc>^lFb", "foo\nbar", 4),
    ("ifoo<CR>bar<Esc>gg$tb", "foo\nbar", 2),
    ("ifoo<CR>bar<Esc>gg$ltb", "foo\nbar", 3),
]

# test t
TESTS += [
    ("ifoo bar baz<Esc>^tb", "foo bar baz", 3),
    ("ifoo bar baz<Esc>^tz", "foo bar baz", 9),
    ("ifoo bar baz<Esc>^2tb", "foo bar baz", 7),
    ("ifoo bar baz<Esc>^3tb", "foo bar baz", 0),
    ("ifoo bar<CR>baz<Esc>ggtb", "foo bar\nbaz", 3),
    ("ifoo bar<CR>baz<Esc>ggl2tb", "foo bar\nbaz", 1),
    ("ifoo bar<CR>baz<Esc>ggtz", "foo bar\nbaz", 0),
]

# test T
TESTS += [
    ("ibar<Esc>Ta", "bar", 2),
    ("ibar<Esc>lTa", "bar", 2),
    ("ibar<Esc>Tb", "bar", 1),
    ("ibar<Esc>lTb", "bar", 1),
    ("ifoo bar baz<Esc>$Tb", "foo bar baz", 9),
    ("ifoo bar baz<Esc>$2Tb", "foo bar baz", 5),
    ("ifoo bar baz<Esc>$3Tb", "foo bar baz", 10),
    ("ifoo bar<CR>baz<Esc>G$Tb", "foo bar\nbaz", 9),
    ("ifoo bar<CR>baz<Esc>G$2Tb", "foo bar\nbaz", 10),
]

# test ;
TESTS += [
    ("ifoo bar baz<Esc>ggfb;", "foo bar baz", 8),
    ("ifoo bar baz<Esc>ggfb0;", "foo bar baz", 4),
    ("ifoo bar baz<Esc>ggfb02;", "foo bar baz", 8),
    ("ifoo bar baz<Esc>gg$Fb$2;", "foo bar baz", 4),
]

# test ,
TESTS += [
    ("ifoo bar baz<Esc>ggfb,", "foo bar baz", 4),
    ("ifoo bar baz<Esc>ggfb$,", "foo bar baz", 8),
    ("ifoo bar baz<Esc>ggfb$2,", "foo bar baz", 4),
    ("ifoo bar baz<Esc>gg$Fb^2,", "foo bar baz", 8),
]

# test x
TESTS += [
    ("ibar<Esc>x", "ba", 2),
    ("ibar<Esc>^x", "ar", 0),
    ("ibar<Esc>^2x", "r", 0),
    ("ibar<Esc>^lx", "br", 1),
    ("ibar<Esc>^l2x", "b", 1),
    ("ibar<Esc>^l3x", "b", 1),
    ("ibar<CR>baz<Esc>gg3lx", "bar\nbaz", 3),
    ("ibar<Esc>xp", "bar", 2),
]

# test X
TESTS += [
    ("ibar<Esc>X", "br", 1),
    ("ibar<Esc>2X", "r", 0),
    ("ibar<Esc>lX", "ba", 2),
    ("ibar<Esc>l2X", "b", 1),
    ("ibar<Esc>3X", "r", 0),
    ("ibar<CR>baz<Esc>GX", "bar\nbaz", 4),
    ("ibar<CR>baz<Esc>G2l3X", "bar\nz", 4),
    ("ibar<Esc>Xp", "bra", 2),
    ("ibar<Esc>2Xp", "rba", 2),
]

# test d
TESTS += [
    ("ifoo<Esc>dgg", "", 0),
    ("ifoo bar<Esc>0dw", "bar", 0),
    ("ifoo  bar<Esc>0dw", "bar", 0),
    ("ifoo: bar<Esc>0dw", ": bar", 0),
    ("ifoo: bar<Esc>0dW", "bar", 0),
    ("ifoo: bar<Esc>0dwp", ":foo bar", 3),
    ("ifoo: bar<Esc>0dwP", "foo: bar", 2),
    ("ifoo<Esc>dd", "", 0),
    ("ifoo<Esc>ddp", "\nfoo", 1),
    ("ifoo<Esc>ddP", "foo\n", 0),
    ("ifoo<CR>bar<Esc>ggddp", "bar\nfoo", 4),
    ("ifoo<CR>bar<Esc>ggddP", "foo\nbar", 0),
    ("ifoo<CR>bar<Esc>gg2dd", "", 0),
    ("ifoo<CR>bar<Esc>gg3dd", "", 0),
    ("ifoo<CR>bar<CR>baz<Esc>ggdd", "bar\nbaz", 0),
    ("ifoo<CR>bar<CR>baz<Esc>ggjdd", "foo\nbaz", 4),
    ("ifoo<CR>bar<CR>baz<Esc>ggjjdd", "foo\nbar", 4),
    ("ifoo<CR>bar<CR>baz<Esc>gg2dd", "baz", 0),
    ("ifoo<CR>bar<CR>baz<Esc>ggj2dd", "foo", 0),
    # ("ifoo<CR>bar<CR>baz<Esc>ggjj2dd", "foo\nbar\nbaz", 8), # quite silly
    ("ifoo<CR>bar<CR>baz<Esc>ggdj", "baz", 0),
    ("ifoo<CR>bar<CR>baz<Esc>Gdk", "foo", 0),
    ("ifoo bar<Esc>02d2l", "bar", 0),
    ("if<CR>o<CR>o<CR>b<CR>a<CR>r<Esc>gg2d2j", "r", 0),
    ("if<CR>o<CR>o<CR>b<CR>a<CR>r<Esc>G2d2k", "f", 0),
]

# test c
TESTS += [
    ("ifoo bar<Esc>0cw", " bar", 0),
    ("ifoo  bar<Esc>0cw", "  bar", 0),
    ("ifoo: bar<Esc>0cw", ": bar", 0),
    ("ifoo: bar<Esc>0cW", " bar", 0),
    ("ifoo bar<Esc>02lce", "fo", 2),
    ("ifoo: bar<Esc>0cw<Esc>p", ":foo bar", 3),
    ("ifoo: bar<Esc>0cw<Esc>P", "foo: bar", 2),
    ("ifoo<Esc>cc", "", 0),
    ("ifoo<Esc>cc<Esc>p", "\nfoo", 1),
    ("ifoo<Esc>cc<Esc>P", "foo\n", 0),
    ("ifoo<CR>bar<Esc>ggcc<Esc>p", "\nfoo\nbar", 1),
    ("ifoo<CR>bar<Esc>ggcc<Esc>P", "foo\n\nbar", 0),
    ("ifoo<CR>bar<Esc>gg2cc", "", 0),
    ("ifoo<CR>bar<Esc>gg3cc", "", 0),
    ("ifoo<CR>bar<CR>baz<Esc>ggcc", "\nbar\nbaz", 0),
    ("ifoo<CR>bar<CR>baz<Esc>ggjcc", "foo\n\nbaz", 4),
    ("ifoo<CR>bar<CR>baz<Esc>ggjjcc", "foo\nbar\n", 8),
    ("ifoo<CR>bar<CR>baz<Esc>gg2cc", "\nbaz", 0),
    ("ifoo<CR>bar<CR>baz<Esc>ggj2cc", "foo\n", 4),
    # ("ifoo<CR>bar<CR>baz<Esc>ggjj2cc", "foo\nbar\nbaz", 8), # quite silly
    ("ifoo<CR>bar<CR>baz<Esc>ggcj", "\nbaz", 0),
    ("ifoo<CR>bar<CR>baz<Esc>Gck", "foo\n", 4),
]

# test J
TESTS += [
    ("ifoo<CR>bar<Esc>ggJ", "foo bar", 3),
    ("ifoo<CR> bar<Esc>ggJ", "foo bar", 3),
    ("ifoo <CR>bar<Esc>ggJ", "foo bar", 4),
    ("ifoo <CR> bar<Esc>ggJ", "foo bar", 4),
    ("ifoo  <CR>bar<Esc>ggJ", "foo  bar", 5),
    ("ifoo  <CR> bar<Esc>ggJ", "foo  bar", 5),
    ("ifoo<Esc>J", "foo", 2),
    ("ifoo<CR>bar<CR>baz<Esc>gg2J", "foo bar\nbaz", 3),
    ("ifoo<CR>bar<CR>baz<Esc>gg3J", "foo bar baz", 7),
]

# test I
TESTS += [
    ("ibar<Esc>Ifoo", "foobar", 3),
    ("ibar<Esc>2Ifoo<Esc>", "foofoobar", 5),
]

# test A
TESTS += [
    ("ifoo<Esc>^Abar", "foobar", 6),
    ("ifoo<Esc>^2Abar<Esc>", "foobarbar", 8),
]

# test C
TESTS += [
    ("ifoo<Esc>Cbar", "fobar", 5),
    ("ifoo<Esc>2Cbar<Esc>", "froo", 1),
    ("ibar<Esc>C<Esc>P", "bra", 1),
]

# test S
TESTS += [
    ("ifoo<Esc>S", "", 0),
    ("ifoo<CR>bar<CR>baz<Esc>k0S", "foo\n\nbaz", 4),
    ("ifoo<CR>bar<CR>baz<Esc>k0lS", "foo\n\nbaz", 4),
]

# test D
TESTS += [
    ("ifoo<Esc>D", "fo", 2),
    ("ifoo<Esc>lD", "fo", 2),
    ("ifoo<Esc>2D", "foo", 2),
    ("ibar<Esc>DP", "bar", 2),
    ("ifoo<CR>bar<CR>baz<Esc>k$D", "foo\nba\nbaz", 6),
    ("ifoo<CR>bar<CR>baz<Esc>k^D", "foo\n\nbaz", 4),
    ("ifoo<CR>bar<CR>baz<Esc>k^DD", "foo\n\nbaz", 4),
]

# test o, O
TESTS += [
    ("o", "\n", 1),
    ("O", "\n", 0),
    ("2ofoo<Esc>", "\nfoo\nfoo", 7),
    ("2Ofoo<Esc>", "foo\nfoo\n", 6),
    ("ifoo<Esc>o", "foo\n", 4),
    ("ifoo<Esc>O", "\nfoo", 0),
    ("ifoo<CR>bar<Esc>ko", "foo\n\nbar", 4),
    ("ifoo<CR>bar<Esc>kO", "\nfoo\nbar", 0),
]

# test y, yy, Y, p, P
TESTS += [
    ("ifoo<Esc>y^", "foo", 0),
    ("ifoo<Esc>y^p", "ffooo", 2),
    ("ifoo<Esc>y^P", "fofoo", 1),
    ("ifoo<CR>bar<CR>baz<Esc>ggyj", "foo\nbar\nbaz", 0),
    ("ifoo<CR>bar<CR>baz<Esc>Gk", "foo\nbar\nbaz", 4),
    ("ifoo<CR>bar<CR>baz<Esc>Gllk", "foo\nbar\nbaz", 6),
    ("ifoo<Esc>^lyy", "foo", 1),
    ("ifoo<Esc>^lyyp", "foo\nfoo", 4),
    ("ifoo<CR>bar<CR>baz<Esc>ggll2yy", "foo\nbar\nbaz", 2),
    ("ifoo<CR>bar<CR>baz<Esc>ggll2yyp", "foo\nfoo\nbar\nbar\nbaz", 4),
    ("ifoo<CR>bar<CR>baz<Esc>ggll2yyP", "foo\nbar\nfoo\nbar\nbaz", 0),
    ("ifoo<CR>bar<CR>baz<Esc>ggll2yyjP", "foo\nfoo\nbar\nbar\nbaz", 4),
    ("ifoo<Esc>^lY", "foo", 1),
    ("ifoo<Esc>^lYp", "foo\nfoo", 4),
    ("ifoo<CR>bar<CR>baz<Esc>ggll2Y", "foo\nbar\nbaz", 2),
    ("ifoo<CR>bar<CR>baz<Esc>ggll2Yp", "foo\nfoo\nbar\nbar\nbaz", 4),
    ("ifoo<CR>bar<CR>baz<Esc>ggll2YP", "foo\nbar\nfoo\nbar\nbaz", 0),
    ("ifoo<CR>bar<CR>baz<Esc>ggll2YjP", "foo\nfoo\nbar\nbar\nbaz", 4),
]

# test backspace
TESTS += [
    ("ifoo<Esc><BS>", "foo", 1),
    ("ifoo<Esc>2<BS>", "foo", 0),
    ("ifoo<CR>bar<Esc>^<BS>", "foo\nbar", 2),
    ("ifoo<CR>bar<Esc>^2<BS>", "foo\nbar", 1),
    ("ifoo<CR>bar<Esc>^100<BS>", "foo\nbar", 0),
    ("ifoo bar<Esc>d<BS>", "foo br", 5),
    ("ifoo bar<Esc>2d<BS>", "foo r", 4),
    ("ifoo bar<Esc>2d2<BS>", "for", 2),
]

# test del
TESTS += [
    ("ifoo<Esc>l<Del>", "foo", 3),
    ("ifoo<Esc><Del>", "fo", 2),
    ("ifoo<Esc>^2<Del>", "foo", 0),
    ("ifoo<Esc>^1<Del>", "foo", 0),
    ("ifoo<Esc>^d<Del>", "foo", 0),
]


# test ~
TESTS += [
    ("ifoo<Esc>^~", "Foo", 1),
    ("ifoo<Esc>^2~", "FOo", 2),
    ("ifoo<CR>bar<Esc>ggl~", "fOo\nbar", 2),
    ("ifoo<CR>bar<Esc>ggl100~", "fOO\nbar", 3),
    ("iðelta<Esc>^~", "Ðelta", 1),
]

# test |j
TESTS += [
    ("ifoo<Esc>|", "foo", 0),
    ("ifoo<Esc>2|", "foo", 1),
    ("ifoo<Esc>^100|", "foo", 3),
    ("ibar<Esc>d2|", "br", 1),
]

# test gu, gU
TESTS += [
    ("ifoo bar<Esc>^gUw", "FOO bar", 0),
    ("ifoo bar<Esc>^lgUw", "fOO bar", 1),
    ("ifoo<CR>bar<CR>baz<Esc>gggUj", "FOO\nBAR\nbaz", 0),
    ("ifoo<CR>bar<CR>baz<Esc>ggjgUj", "foo\nBAR\nBAZ", 4),
    # ("ifoobar<Esc>^l2gU2l", "fOOBAr", 1),
    ("ifoo<Esc>^gUU", "FOO", 0),
    ("ifoo<Esc>^gUgU", "FOO", 0),
    ("ifoo<CR>bar<CR>baz<Esc>^gglgUU", "FOO\nbar\nbaz", 0),
    ("ifoo<CR>bar<CR>baz<Esc>^gglgUgU", "FOO\nbar\nbaz", 0),
    ("ifoo<CR>bar<CR>baz<Esc>^ggl2gUU", "FOO\nBAR\nbaz", 1),
    ("ifoo<CR>bar<CR>baz<Esc>^ggl2gUgU", "FOO\nBAR\nbaz", 1),
    ("ifoo<CR>bar<CR>baz<Esc>^ggl3gUU", "FOO\nBAR\nBAZ", 1),
    ("ifoo<CR>bar<CR>baz<Esc>^ggl3gUgU", "FOO\nBAR\nBAZ", 1),
    ("ifoo<CR>bar<CR>baz<Esc>^ggl4gUU", "FOO\nBAR\nBAZ", 1),
    ("ifoo<CR>bar<CR>baz<Esc>^ggl4gUgU", "FOO\nBAR\nBAZ", 1),
    ("iFOO BAR<Esc>^guw", "foo BAR", 0),
    ("iFOO BAR<Esc>^lguw", "Foo BAR", 1),
    ("iFOO<CR>BAR<CR>BAZ<Esc>ggguj", "foo\nbar\nBAZ", 0),
    ("iFOO<CR>BAR<CR>BAZ<Esc>ggjguj", "FOO\nbar\nbaz", 4),
    # ("iFOOBAR<Esc>^l2gu2l", "FoobaR", 1),
    ("iFOO<Esc>^guu", "foo", 0),
    ("iFOO<Esc>^gugu", "foo", 0),
    ("iFOO<CR>BAR<CR>BAZ<Esc>^gglguu", "foo\nBAR\nBAZ", 0),
    ("iFOO<CR>BAR<CR>BAZ<Esc>^gglgugu", "foo\nBAR\nBAZ", 0),
    ("iFOO<CR>BAR<CR>BAZ<Esc>^ggl2guu", "foo\nbar\nBAZ", 1),
    ("iFOO<CR>BAR<CR>BAZ<Esc>^ggl2gugu", "foo\nbar\nBAZ", 1),
    ("iFOO<CR>BAR<CR>BAZ<Esc>^ggl3guu", "foo\nbar\nbaz", 1),
    ("iFOO<CR>BAR<CR>BAZ<Esc>^ggl3gugu", "foo\nbar\nbaz", 1),
    ("iFOO<CR>BAR<CR>BAZ<Esc>^ggl4guu", "foo\nbar\nbaz", 1),
    ("iFOO<CR>BAR<CR>BAZ<Esc>^ggl4gugu", "foo\nbar\nbaz", 1),
]


# test home/end and arrows
TESTS += [
    ("ifoo<Home>", "foo", 0),
    ("ifoo<Esc>0<End>", "foo", 2),
    ("ifoo<Left>", "foo", 2),
    ("ifoo<Esc>3<Left>", "foo", 0),
    ("ifoo<Home><Right>", "foo", 1),
    ("ifoo<CR>bar<Up>", "foo\nbar", 3),
    ("ifoo<CR>bar<Esc>gg<Down>", "foo\nbar", 4),
]


@pytest.fixture(scope="session")
def root_qt_widget() -> QtWidgets.QWidget:
    """Construct a root QT widget that child objects can reference to avoid
    early garbage collection.

    :return: root QT widget for testing
    """
    return QtWidgets.QWidget()


@pytest.fixture(scope="session")
def text_edit(  # pylint: disable=redefined-outer-name
    qapp: T.Any, root_qt_widget: QtWidgets.QWidget
) -> None:
    """Construct VimTextEdit instance for testing.

    :param qapp: test QApplication
    :param root_qt_widget: root widget
    :return: text edit instance
    """
    widget = VimTextEdit(parent=root_qt_widget)
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
            key_num = ord(key)
            key_text = key
        text_edit.keyPressEvent(
            QtGui.QKeyEvent(
                QtCore.QEvent.KeyPress,
                key_num,
                QtCore.Qt.KeyboardModifiers(),
                0,
                0,
                0,
                key_text,
            )
        )
        text_edit.keyReleaseEvent(
            QtGui.QKeyEvent(
                QtCore.QEvent.KeyRelease,
                key_num,
                QtCore.Qt.KeyboardModifiers(),
                0,
                0,
                0,
                key_text,
            )
        )

    assert text_edit.toPlainText() == expected_text
    assert text_edit.textCursor().position() == expected_position
