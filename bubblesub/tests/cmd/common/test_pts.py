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

import asyncio
import typing as T
from unittest.mock import MagicMock

import pytest

from bubblesub.api.cmd import CommandError
from bubblesub.cmd.common import Pts

CURRENT_FRAME = 123


@pytest.mark.parametrize(
    'expr,origin,expected_value',
    [
        ('', None, CommandError),
        ('', 25, CommandError),
        ('+', None, CommandError),
        ('+', 25, CommandError),
        ('0ms+', None, CommandError),
        ('0ms+', 25, CommandError),
        ('500ms', None, 500),
        ('500ms', 25, 500),
        ('+500ms', None, 500),
        ('+500ms', 25, 525),
        ('-500ms', None, -500),
        ('-500ms', 25, -475),
        ('0ms+500ms', None, 500),
        ('0ms+500ms', 25, 500),
        ('25ms+500ms', None, 525),
        ('25ms+500ms', 25, 525),
        ('500ms-25ms', None, 475),
        ('500ms-25ms', 25, 475),
        ('500', None, CommandError),
        ('500', 0, CommandError),
        ('ms', None, CommandError),
        ('ms', 0, CommandError),
        ('cf', None, CURRENT_FRAME),
        ('cf', 0, CURRENT_FRAME),
        ('cfcf', None, CommandError),
        ('cfcf', 0, CommandError),
    ]
)
def test_pts(
        expr: str,
        origin: T.Optional[int],
        expected_value: T.Optional[int]
) -> None:
    # arrange
    api = MagicMock()
    api.media.current_pts = CURRENT_FRAME
    pts = Pts(api, expr)

    # act
    try:
        value = asyncio.get_event_loop().run_until_complete(
            pts.get(origin=origin)
        )
    except CommandError as ex:
        value = type(ex)

    # assert
    assert value == expected_value
