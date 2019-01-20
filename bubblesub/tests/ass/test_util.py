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

import pytest

from bubblesub.ass.util import iter_words_ass_line


@pytest.mark.parametrize(
    "ass_text,expected",
    [
        ("test", ["test"]),
        ("one two", ["one", "two"]),
        ("one\\Ntwo", ["one", "two"]),
        ("one\\ntwo", ["one", "two"]),
        ("one\\htwo", ["one", "two"]),
        ("\\None two", ["one", "two"]),
        ("\\none two", ["one", "two"]),
        ("\\hone two", ["one", "two"]),
        ("1st", ["1st"]),
        ("1st 2nd", ["1st", "2nd"]),
    ],
)
def test_iter_words_ass_line(ass_text, expected):
    actual = [match.group(0) for match in iter_words_ass_line(ass_text)]
    assert actual == expected
