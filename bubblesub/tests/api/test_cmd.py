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

import typing as T

import pytest

from bubblesub.api.cmd import split_invocation


@pytest.mark.parametrize(
    "invocation,expected",
    [
        ("derp", [["derp"]]),
        (" derp  ", [["derp"]]),
        ("herp;derp", [["herp"], ["derp"]]),
        ("herp derp", [["herp", "derp"]]),
        ('herp "derp"', [["herp", "derp"]]),
        ('"herp derp"', [["herp derp"]]),
        ('"herp";"derp"', [["herp"], ["derp"]]),
        ('"herp;derp"', [["herp;derp"]]),
        ('"herp\'derp"', [["herp'derp"]]),
        ('"herp"\'"\'"derp"', [['herp"derp']]),
        ('"herp" "derp"', [["herp", "derp"]]),
        ('"herp""derp"', [["herpderp"]]),
        ('"herp""derp', [["herpderp"]]),
    ],
)
def test_split_invocation(
    invocation: str, expected: T.List[T.List[str]]
) -> None:
    actual = split_invocation(invocation)
    assert actual == expected
