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

TESTS = []

# basic tests
TESTS += [
    ("", "", 0),
    ("ifoo", "foo", 3),
    ("ifoo<esc>", "foo", 2),
    ("ifoo<cr>bar<esc>", "foo\nbar", 6),
]

# test gg
TESTS += [
    ("ifoo<esc>gg", "foo", 0),
    ("ifoo<cr>bar<esc>gg", "foo\nbar", 0),
]

# test G
TESTS += [
    ("ifoo<esc>ggG", "foo", 0),
    ("ifoo<esc>gglG", "foo", 0),
    ("ifoo<cr>bar<esc>ggG", "foo\nbar", 4),
]

# test ^
TESTS += [
    ("ifoo<esc>^", "foo", 0),
    ("ifoo<cr>bar<esc>^", "foo\nbar", 4),
    ("ifoo<cr>bar<esc>2^", "foo\nbar", 4),
]

# test 0
TESTS += [
    ("ifoo<esc>0", "foo", 0),
    ("ifoo<cr>bar<esc>0", "foo\nbar", 4),
    ("ifoo<cr>bar<esc>20", "foo\nbar", 6),
]

# test $
TESTS += [
    ("ifoo<esc>^$", "foo", 2),
    ("ifoo<cr>bar<esc>^$", "foo\nbar", 6),
    ("ifoo<cr>bar<cr>baz<esc>gg2$", "foo\nbar\nbaz", 6),
]

# test h
TESTS += [
    ("ifoo<esc>h", "foo", 1),
    ("ifoo<esc>hh", "foo", 0),
    ("ifoo<esc>hhh", "foo", 0),
    ("ifoo<esc>1h", "foo", 1),
    ("ifoo<esc>2h", "foo", 0),
    ("ifoo<esc>3h", "foo", 0),
    ("ifoo<cr>bar<esc>h", "foo\nbar", 5),
    ("ifoo<cr>bar<esc>3h", "foo\nbar", 4),
]

# test l
TESTS += [
    ("ifoo<esc>10hl", "foo", 1),
    ("ifoo<esc>10h2l", "foo", 2),
    ("ifoo<esc>10h4l", "foo", 3),
    ("ifoo<cr>bar<esc>ggl", "foo\nbar", 1),
    ("ifoo<cr>bar<esc>gg4l", "foo\nbar", 3),
]

# test j
TESTS += [
    ("ifoo<esc>j", "foo", 2),
    ("ifoo<cr>bar<cr>baz<esc>ggj", "foo\nbar\nbaz", 4),
    ("ifoo<cr>bar<cr>baz<esc>gglj", "foo\nbar\nbaz", 5),
    ("ifoo<cr>bar<cr>baz<esc>gg2j", "foo\nbar\nbaz", 8),
    ("ifoo<cr>bar<cr>baz<esc>ggl2j", "foo\nbar\nbaz", 9),
]

# test k
TESTS += [
    ("ifoo<esc>k", "foo", 2),
    ("ifoo<cr>bar<cr>baz<esc>Gk", "foo\nbar\nbaz", 4),
    ("ifoo<cr>bar<cr>baz<esc>Glk", "foo\nbar\nbaz", 5),
    ("ifoo<cr>bar<cr>baz<esc>G2k", "foo\nbar\nbaz", 0),
    ("ifoo<cr>bar<cr>baz<esc>Gl2k", "foo\nbar\nbaz", 1),
]

# test b
TESTS += [
    ("ifoo bar<esc>b", "foo bar", 4),
    ("ifoo bar<esc>bb", "foo bar", 0),
    ("ifoo()bar baz<esc>b", "foo()bar baz", 9),
    ("ifoo()bar baz<esc>bb", "foo()bar baz", 5),
    ("ifoo()bar baz<esc>bbb", "foo()bar baz", 3),
    ("ifoo()bar baz<esc>bbbb", "foo()bar baz", 0),
    ("ifoo()bar baz<esc>1b", "foo()bar baz", 9),
    ("ifoo()bar baz<esc>2b", "foo()bar baz", 5),
    ("ifoo()bar baz<esc>3b", "foo()bar baz", 3),
    ("ifoo()bar baz<esc>4b", "foo()bar baz", 0),
    ("i asd <esc>l", " asd ", 5),
    ("i asd <esc>lb", " asd ", 1),
    ("i asd  <esc>lb", " asd  ", 1),
    ("i  asd <esc>lb", "  asd ", 2),
    ("i  asd <esc>l2b", "  asd ", 0),
    ("ifoo<cr><cr>bar<esc>b", "foo\n\nbar", 5),
    ("ifoo<cr><cr>bar<esc>2b", "foo\n\nbar", 4),
    ("ifoo<cr>x<cr>bar<esc>2b", "foo\nx\nbar", 4),
]

# test B
TESTS += [
    ("ifoo()bar baz<esc>B", "foo()bar baz", 9),
    ("ifoo()bar baz<esc>BB", "foo()bar baz", 0),
    ("ifoo()bar baz<esc>BBB", "foo()bar baz", 0),
    ("ifoo()bar baz<esc>1B", "foo()bar baz", 9),
    ("ifoo()bar baz<esc>2B", "foo()bar baz", 0),
    ("ifoo()bar baz<esc>3B", "foo()bar baz", 0),
    ("i asd <esc>lB", " asd ", 1),
    ("i asd  <esc>lB", " asd  ", 1),
    ("i  asd <esc>lB", "  asd ", 2),
    ("i  asd <esc>l2B", "  asd ", 0),
    ("ifoo<cr><cr>bar<esc>B", "foo\n\nbar", 5),
    ("ifoo<cr><cr>bar<esc>2B", "foo\n\nbar", 4),
]

# test w
TESTS += [
    ("ifoo bar<esc>ggw", "foo bar", 4),
    ("ifoo bar<esc>gg2w", "foo bar", 7),
    ("ifoo()bar<esc>ggw", "foo()bar", 3),
    ("ifoo()bar<esc>gg2w", "foo()bar", 5),
    ("ifoo()bar<esc>gg3w", "foo()bar", 8),
    ("ifoo bar<cr>baz<esc>gg2w", "foo bar\nbaz", 8),
    ("i foo <esc>ggw", " foo ", 1),
    ("i foo <esc>gg2w", " foo ", 5),
    ("i  foo <esc>ggw", "  foo ", 2),
    ("i  foo <esc>gg2w", "  foo ", 6),
    ("ifoo<cr><cr>bar<esc>ggw", "foo\n\nbar", 4),
    ("ifoo<cr><cr>bar<esc>gg2w", "foo\n\nbar", 5),
    ("ifoo<cr><cr>bar<esc>gg3w", "foo\n\nbar", 8),
]

# test W
TESTS += [
    ("ifoo bar<esc>ggW", "foo bar", 4),
    ("ifoo bar<esc>gg2W", "foo bar", 7),
    ("i foo <esc>ggW", " foo ", 1),
    ("i foo <esc>gg2W", " foo ", 5),
    ("i  foo <esc>ggW", "  foo ", 2),
    ("i  foo <esc>gg2W", "  foo ", 6),
    ("ifoo()bar<esc>ggW", "foo()bar", 8),
    ("ifoo()bar baz<esc>ggW", "foo()bar baz", 9),
    ("ifoo()bar baz<esc>gg2W", "foo()bar baz", 12),
    ("ifoo()bar baz<esc>gg3W", "foo()bar baz", 12),
    ("ifoo bar<cr>baz<esc>gg2W", "foo bar\nbaz", 8),
    ("ifoo<cr><cr>bar<esc>ggW", "foo\n\nbar", 4),
    ("ifoo<cr><cr>bar<esc>gg2W", "foo\n\nbar", 5),
    ("ifoo<cr><cr>bar<esc>gg3W", "foo\n\nbar", 8),
]

# test e
TESTS += [
    ("ifoo<esc>gge", "foo", 2),
    ("ifoo<esc>ggle", "foo", 2),
    ("ifoo<esc>gg2le", "foo", 3),
    ("ifoo bar<esc>gge", "foo bar", 2),
    ("ifoo bar<esc>gg3le", "foo bar", 6),
    ("ifoo bar<esc>gg2e", "foo bar", 6),
    ("ifoo()bar<esc>gge", "foo()bar", 2),
    ("ifoo()bar<esc>gg2e", "foo()bar", 4),
    ("ifoo()bar<esc>gg3e", "foo()bar", 7),
    ("ifoo bar<cr>baz<esc>gg2e", "foo bar\nbaz", 6),
    ("i foo <esc>gge", " foo ", 3),
    ("i foo <esc>gg2e", " foo ", 5),
    ("i  foo <esc>gge", "  foo ", 4),
    ("i  foo <esc>gg2e", "  foo ", 6),
]

# test E
TESTS += [
    ("ifoo<esc>ggE", "foo", 2),
    ("ifoo<esc>gglE", "foo", 2),
    ("ifoo<esc>gg2lE", "foo", 3),
    ("ifoo bar<esc>ggE", "foo bar", 2),
    ("ifoo bar<esc>gg3lE", "foo bar", 6),
    ("ifoo bar<esc>gg2E", "foo bar", 6),
    ("ifoo()bar<esc>ggE", "foo()bar", 7),
    ("ifoo()bar<esc>gg2E", "foo()bar", 8),
    ("ifoo()bar<esc>gg3E", "foo()bar", 8),
    ("ifoo bar<cr>baz<esc>gg2E", "foo bar\nbaz", 6),
    ("i foo <esc>ggE", " foo ", 3),
    ("i foo <esc>gg2E", " foo ", 5),
    ("i  foo <esc>ggE", "  foo ", 4),
    ("i  foo <esc>gg2E", "  foo ", 6),
]

# test f
TESTS += [
    ("ifoo bar baz<esc>^fb", "foo bar baz", 4),
    ("ifoo bar baz<esc>^fz", "foo bar baz", 10),
    ("ifoo bar baz<esc>^2fb", "foo bar baz", 8),
    ("ifoo bar baz<esc>^3fb", "foo bar baz", 0),
    ("ifoo bar<cr>baz<esc>ggfb", "foo bar\nbaz", 4),
    ("ifoo bar<cr>baz<esc>ggl2fb", "foo bar\nbaz", 1),
    ("ifoo bar<cr>baz<esc>ggfz", "foo bar\nbaz", 0),
    ("ifoo<cr>bar<esc>gg$fb", "foo\nbar", 2),
    ("ifoo<cr>bar<esc>gg$lfb", "foo\nbar", 3),
]

# test F
TESTS += [
    ("ifoo bar baz<esc>$Fb", "foo bar baz", 8),
    ("ifoo bar baz<esc>$2Fb", "foo bar baz", 4),
    ("ifoo bar baz<esc>$3Fb", "foo bar baz", 10),
    ("ifoo bar<cr>baz<esc>G$Fb", "foo bar\nbaz", 8),
    ("ifoo bar<cr>baz<esc>G$2Fb", "foo bar\nbaz", 10),
    ("ifoo<cr>bar<esc>^Fo", "foo\nbar", 4),
    ("ifoo<cr>bar<esc>^lFb", "foo\nbar", 4),
    ("ifoo<cr>bar<esc>gg$tb", "foo\nbar", 2),
    ("ifoo<cr>bar<esc>gg$ltb", "foo\nbar", 3),
]

# test t
TESTS += [
    ("ifoo bar baz<esc>^tb", "foo bar baz", 3),
    ("ifoo bar baz<esc>^tz", "foo bar baz", 9),
    ("ifoo bar baz<esc>^2tb", "foo bar baz", 7),
    ("ifoo bar baz<esc>^3tb", "foo bar baz", 0),
    ("ifoo bar<cr>baz<esc>ggtb", "foo bar\nbaz", 3),
    ("ifoo bar<cr>baz<esc>ggl2tb", "foo bar\nbaz", 1),
    ("ifoo bar<cr>baz<esc>ggtz", "foo bar\nbaz", 0),
]

# test T
TESTS += [
    ("ibar<esc>Ta", "bar", 2),
    ("ibar<esc>lTa", "bar", 2),
    ("ibar<esc>Tb", "bar", 1),
    ("ibar<esc>lTb", "bar", 1),
    ("ifoo bar baz<esc>$Tb", "foo bar baz", 9),
    ("ifoo bar baz<esc>$2Tb", "foo bar baz", 5),
    ("ifoo bar baz<esc>$3Tb", "foo bar baz", 10),
    ("ifoo bar<cr>baz<esc>G$Tb", "foo bar\nbaz", 9),
    ("ifoo bar<cr>baz<esc>G$2Tb", "foo bar\nbaz", 10),
]

# test ;
TESTS += [
    ("ifoo bar baz<esc>ggfb;", "foo bar baz", 8),
    ("ifoo bar baz<esc>ggfb0;", "foo bar baz", 4),
    ("ifoo bar baz<esc>ggfb02;", "foo bar baz", 8),
    ("ifoo bar baz<esc>gg$Fb$2;", "foo bar baz", 4),
]

# test ,
TESTS += [
    ("ifoo bar baz<esc>ggfb,", "foo bar baz", 4),
    ("ifoo bar baz<esc>ggfb$,", "foo bar baz", 8),
    ("ifoo bar baz<esc>ggfb$2,", "foo bar baz", 4),
    ("ifoo bar baz<esc>gg$Fb^2,", "foo bar baz", 8),
]

# test x
TESTS += [
    ("ibar<esc>x", "ba", 2),
    ("ibar<esc>^x", "ar", 0),
    ("ibar<esc>^2x", "r", 0),
    ("ibar<esc>^lx", "br", 1),
    ("ibar<esc>^l2x", "b", 1),
    ("ibar<esc>^l3x", "b", 1),
    ("ibar<cr>baz<esc>gg3lx", "bar\nbaz", 3),
    ("ibar<esc>xp", "bar", 2),
]

# test X
TESTS += [
    ("ibar<esc>X", "br", 1),
    ("ibar<esc>2X", "r", 0),
    ("ibar<esc>lX", "ba", 2),
    ("ibar<esc>l2X", "b", 1),
    ("ibar<esc>3X", "r", 0),
    ("ibar<cr>baz<esc>GX", "bar\nbaz", 4),
    ("ibar<cr>baz<esc>G2l3X", "bar\nz", 4),
    ("ibar<esc>Xp", "bra", 2),
    ("ibar<esc>2Xp", "rba", 2),
]

# test d
TESTS += [
    ("ifoo<esc>dgg", "", 0),
    ("ifoo bar<esc>0dw", "bar", 0),
    ("ifoo  bar<esc>0dw", "bar", 0),
    ("ifoo: bar<esc>0dw", ": bar", 0),
    ("ifoo: bar<esc>0dW", "bar", 0),
    ("ifoo: bar<esc>0dwp", ":foo bar", 3),
    ("ifoo: bar<esc>0dwP", "foo: bar", 2),
    ("ifoo<esc>dd", "", 0),
    ("ifoo<esc>ddp", "\nfoo", 1),
    ("ifoo<esc>ddP", "foo\n", 0),
    ("ifoo<cr>bar<esc>ggddp", "bar\nfoo", 4),
    ("ifoo<cr>bar<esc>ggddP", "foo\nbar", 0),
    ("ifoo<cr>bar<esc>gg2dd", "", 0),
    ("ifoo<cr>bar<esc>gg3dd", "", 0),
    ("ifoo<cr>bar<cr>baz<esc>ggdd", "bar\nbaz", 0),
    ("ifoo<cr>bar<cr>baz<esc>ggjdd", "foo\nbaz", 4),
    ("ifoo<cr>bar<cr>baz<esc>ggjjdd", "foo\nbar", 4),
    ("ifoo<cr>bar<cr>baz<esc>gg2dd", "baz", 0),
    ("ifoo<cr>bar<cr>baz<esc>ggj2dd", "foo", 0),
    # ("ifoo<cr>bar<cr>baz<esc>ggjj2dd", "foo\nbar\nbaz", 8), # quite silly
    ("ifoo<cr>bar<cr>baz<esc>ggdj", "baz", 0),
    ("ifoo<cr>bar<cr>baz<esc>Gdk", "foo", 0),
    ("ifoo bar<esc>02d2l", "bar", 0),
    ("if<cr>o<cr>o<cr>b<cr>a<cr>r<esc>gg2d2j", "r", 0),
    ("if<cr>o<cr>o<cr>b<cr>a<cr>r<esc>G2d2k", "f", 0),
]

# test c
TESTS += [
    ("ifoo bar<esc>0cw", " bar", 0),
    ("ifoo  bar<esc>0cw", "  bar", 0),
    ("ifoo: bar<esc>0cw", ": bar", 0),
    ("ifoo: bar<esc>0cW", " bar", 0),
    ("ifoo bar<esc>02lce", "fo", 2),
    ("ifoo: bar<esc>0cw<esc>p", ":foo bar", 3),
    ("ifoo: bar<esc>0cw<esc>P", "foo: bar", 2),
    ("ifoo<esc>cc", "", 0),
    ("ifoo<esc>cc<esc>p", "\nfoo", 1),
    ("ifoo<esc>cc<esc>P", "foo\n", 0),
    ("ifoo<cr>bar<esc>ggcc<esc>p", "\nfoo\nbar", 1),
    ("ifoo<cr>bar<esc>ggcc<esc>P", "foo\n\nbar", 0),
    ("ifoo<cr>bar<esc>gg2cc", "", 0),
    ("ifoo<cr>bar<esc>gg3cc", "", 0),
    ("ifoo<cr>bar<cr>baz<esc>ggcc", "\nbar\nbaz", 0),
    ("ifoo<cr>bar<cr>baz<esc>ggjcc", "foo\n\nbaz", 4),
    ("ifoo<cr>bar<cr>baz<esc>ggjjcc", "foo\nbar\n", 8),
    ("ifoo<cr>bar<cr>baz<esc>gg2cc", "\nbaz", 0),
    ("ifoo<cr>bar<cr>baz<esc>ggj2cc", "foo\n", 4),
    # ("ifoo<cr>bar<cr>baz<esc>ggjj2cc", "foo\nbar\nbaz", 8), # quite silly
    ("ifoo<cr>bar<cr>baz<esc>ggcj", "\nbaz", 0),
    ("ifoo<cr>bar<cr>baz<esc>Gck", "foo\n", 4),
]

# test J
TESTS += [
    ("ifoo<cr>bar<esc>ggJ", "foo bar", 3),
    ("ifoo<cr> bar<esc>ggJ", "foo bar", 3),
    ("ifoo <cr>bar<esc>ggJ", "foo bar", 4),
    ("ifoo <cr> bar<esc>ggJ", "foo bar", 4),
    ("ifoo  <cr>bar<esc>ggJ", "foo  bar", 5),
    ("ifoo  <cr> bar<esc>ggJ", "foo  bar", 5),
    ("ifoo<esc>J", "foo", 2),
    ("ifoo<cr>bar<cr>baz<esc>gg2J", "foo bar\nbaz", 3),
    ("ifoo<cr>bar<cr>baz<esc>gg3J", "foo bar baz", 7),
]

# test I
TESTS += [
    ("ibar<esc>Ifoo", "foobar", 3),
    ("ibar<esc>2Ifoo<esc>", "foobar", 2),
]

# test A
TESTS += [
    ("ifoo<esc>^Abar", "foobar", 6),
    ("ifoo<esc>^2Abar<esc>", "foobar", 5),
]

# test C
TESTS += [
    ("ifoo<esc>Cbar", "fobar", 5),
    ("ifoo<esc>2Cbar<esc>", "fobar", 4),
    ("ifoo<esc>C<esc>P", "foo", 1),
]

# test S
TESTS += [
    ("ifoo<esc>S", "", 0),
    ("ifoo<cr>bar<cr>baz<esc>k0S", "foo\n\nbaz", 4),
    ("ifoo<cr>bar<cr>baz<esc>k0lS", "foo\n\nbaz", 4),
]

# test D
TESTS += [
    ("ifoo<esc>D", "fo", 2),
    ("ifoo<esc>lD", "fo", 2),
    ("ifoo<esc>2D", "fo", 2),
    ("ibar<esc>DP", "bar", 2),
    ("ifoo<cr>bar<cr>baz<esc>k$D", "foo\nba\nbaz", 6),
    ("ifoo<cr>bar<cr>baz<esc>k^D", "foo\n\nbaz", 4),
    ("ifoo<cr>bar<cr>baz<esc>k^DD", "foo\n\nbaz", 4),
]

# test o, O
TESTS += [
    ("o", "\n", 1),
    ("O", "\n", 0),
    ("2ofoo<esc>", "\nfoo", 3),
    ("2Ofoo<esc>", "foo\n", 2),
    ("ifoo<esc>o", "foo\n", 4),
    ("ifoo<esc>O", "\nfoo", 0),
    ("ifoo<cr>bar<esc>ko", "foo\n\nbar", 4),
    ("ifoo<cr>bar<esc>kO", "\nfoo\nbar", 0),
]

# test y, yy, Y, p, P
TESTS += [
    ("ifoo<esc>y^", "foo", 0),
    ("ifoo<esc>y^p", "ffooo", 2),
    ("ifoo<esc>y^P", "fofoo", 1),
    ("ifoo<cr>bar<cr>baz<esc>ggyj", "foo\nbar\nbaz", 0),
    ("ifoo<cr>bar<cr>baz<esc>Gk", "foo\nbar\nbaz", 4),
    ("ifoo<cr>bar<cr>baz<esc>Gllk", "foo\nbar\nbaz", 6),
    ("ifoo<esc>^lyy", "foo", 1),
    ("ifoo<esc>^lyyp", "foo\nfoo", 4),
    ("ifoo<cr>bar<cr>baz<esc>ggll2yy", "foo\nbar\nbaz", 2),
    ("ifoo<cr>bar<cr>baz<esc>ggll2yyp", "foo\nfoo\nbar\nbar\nbaz", 4),
    ("ifoo<cr>bar<cr>baz<esc>ggll2yyP", "foo\nbar\nfoo\nbar\nbaz", 0),
    ("ifoo<cr>bar<cr>baz<esc>ggll2yyjP", "foo\nfoo\nbar\nbar\nbaz", 4),
    ("ifoo<esc>^lY", "foo", 1),
    ("ifoo<esc>^lYp", "foo\nfoo", 4),
    ("ifoo<cr>bar<cr>baz<esc>ggll2Y", "foo\nbar\nbaz", 2),
    ("ifoo<cr>bar<cr>baz<esc>ggll2Yp", "foo\nfoo\nbar\nbar\nbaz", 4),
    ("ifoo<cr>bar<cr>baz<esc>ggll2YP", "foo\nbar\nfoo\nbar\nbaz", 0),
    ("ifoo<cr>bar<cr>baz<esc>ggll2YjP", "foo\nfoo\nbar\nbar\nbaz", 4),
]

# test backspace
TESTS += [
    ("ifoo<esc><bs>", "foo", 1),
    ("ifoo<esc>2<bs>", "foo", 0),
    ("ifoo<cr>bar<esc>^<bs>", "foo\nbar", 2),
    ("ifoo<cr>bar<esc>^2<bs>", "foo\nbar", 1),
    ("ifoo<cr>bar<esc>^100<bs>", "foo\nbar", 0),
    ("ifoo bar<esc>d<bs>", "foo br", 5),
    ("ifoo bar<esc>2d<bs>", "foo r", 4),
    ("ifoo bar<esc>2d2<bs>", "for", 2),
]

# test del
TESTS += [
    ("ifoo<esc>l<del>", "foo", 3),
    ("ifoo<esc><del>", "fo", 2),
    ("ifoo<esc>^2<del>", "foo", 0),
    ("ifoo<esc>^1<del>", "foo", 0),
    ("ifoo<esc>^d<del>", "foo", 0),
]


# test ~
TESTS += [
    ("ifoo<esc>^~", "Foo", 1),
    ("ifoo<esc>^2~", "FOo", 2),
    ("ifoo<cr>bar<esc>ggl~", "fOo\nbar", 2),
    ("ifoo<cr>bar<esc>ggl100~", "fOO\nbar", 3),
    ("iðelta<esc>^~", "Ðelta", 1),
]

# test |j
TESTS += [
    ("ifoo<esc>|", "foo", 0),
    ("ifoo<esc>2|", "foo", 1),
    ("ifoo<esc>^100|", "foo", 3),
    ("ibar<esc>d2|", "br", 1),
]

# test gu, gU
TESTS += [
    ("ifoo bar<esc>^gUw", "FOO bar", 0),
    ("ifoo bar<esc>^lgUw", "fOO bar", 1),
    ("ifoo<cr>bar<cr>baz<esc>gggUj", "FOO\nBAR\nbaz", 0),
    ("ifoo<cr>bar<cr>baz<esc>ggjgUj", "foo\nBAR\nBAZ", 4),
    # ("ifoobar<esc>^l2gU2l", "fOOBAr", 1),
    ("ifoo<esc>^gUU", "FOO", 0),
    ("ifoo<esc>^gUgU", "FOO", 0),
    ("ifoo<cr>bar<cr>baz<esc>^gglgUU", "FOO\nbar\nbaz", 0),
    ("ifoo<cr>bar<cr>baz<esc>^gglgUgU", "FOO\nbar\nbaz", 0),
    ("ifoo<cr>bar<cr>baz<esc>^ggl2gUU", "FOO\nBAR\nbaz", 1),
    ("ifoo<cr>bar<cr>baz<esc>^ggl2gUgU", "FOO\nBAR\nbaz", 1),
    ("ifoo<cr>bar<cr>baz<esc>^ggl3gUU", "FOO\nBAR\nBAZ", 1),
    ("ifoo<cr>bar<cr>baz<esc>^ggl3gUgU", "FOO\nBAR\nBAZ", 1),
    ("ifoo<cr>bar<cr>baz<esc>^ggl4gUU", "FOO\nBAR\nBAZ", 1),
    ("ifoo<cr>bar<cr>baz<esc>^ggl4gUgU", "FOO\nBAR\nBAZ", 1),
    ("iFOO BAR<esc>^guw", "foo BAR", 0),
    ("iFOO BAR<esc>^lguw", "Foo BAR", 1),
    ("iFOO<cr>BAR<cr>BAZ<esc>ggguj", "foo\nbar\nBAZ", 0),
    ("iFOO<cr>BAR<cr>BAZ<esc>ggjguj", "FOO\nbar\nbaz", 4),
    # ("iFOOBAR<esc>^l2gu2l", "FoobaR", 1),
    ("iFOO<esc>^guu", "foo", 0),
    ("iFOO<esc>^gugu", "foo", 0),
    ("iFOO<cr>BAR<cr>BAZ<esc>^gglguu", "foo\nBAR\nBAZ", 0),
    ("iFOO<cr>BAR<cr>BAZ<esc>^gglgugu", "foo\nBAR\nBAZ", 0),
    ("iFOO<cr>BAR<cr>BAZ<esc>^ggl2guu", "foo\nbar\nBAZ", 1),
    ("iFOO<cr>BAR<cr>BAZ<esc>^ggl2gugu", "foo\nbar\nBAZ", 1),
    ("iFOO<cr>BAR<cr>BAZ<esc>^ggl3guu", "foo\nbar\nbaz", 1),
    ("iFOO<cr>BAR<cr>BAZ<esc>^ggl3gugu", "foo\nbar\nbaz", 1),
    ("iFOO<cr>BAR<cr>BAZ<esc>^ggl4guu", "foo\nbar\nbaz", 1),
    ("iFOO<cr>BAR<cr>BAZ<esc>^ggl4gugu", "foo\nbar\nbaz", 1),
]


@pytest.mark.parametrize(
    "keys,expected_text,expected_position", TESTS,
)
def test_vim_text_edit(  # pylint: disable=redefined-outer-name
    qtbot: T.Any, keys: str, expected_text: str, expected_position: int
) -> None:
    """Test VimTextEdit behavior.

    :param qtbot: test QApplication
    :param keys: keys to send to the input
    :param expected_text: expected text contents of the edit
    :param expected_position: expected caret position
    """
    parent = QtWidgets.QWidget()
    text_edit = VimTextEdit(parent=parent)
    for key in re.findall("<[^>]+>|.", keys):
        if key.lower() == "<esc>":
            key_num = QtCore.Qt.Key_Escape
            key_text = "\x1B"
        elif key.lower() == "<bs>":
            key_num = QtCore.Qt.Key_Backspace
            key_text = "\x08"
        elif key.lower() == "<del>":
            key_num = QtCore.Qt.Key_Delete
            key_text = "\x7F"
        elif key.lower() == "<cr>":
            key_num = QtCore.Qt.Key_Return
            key_text = "\r"
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
