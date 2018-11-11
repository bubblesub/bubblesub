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
from bubblesub.cmd.common import SubtitlesSelection


@pytest.mark.parametrize(
    'expr,sub_count,sub_selection,expected_indexes',
    [
        # basic
        ('none', 3, ..., []),
        ('all', 3, ..., [0, 1, 2]),
        ('selected', 3, [], []),
        ('selected', 3, [0], [0]),
        ('selected', 3, [1, 2], [1, 2]),
        # first/last
        ('first', 3, ..., [0]),
        ('last', 3, ..., [2]),
        ('first', 0, ..., []),
        ('last', 0, ..., []),
        # specific
        ('1', 2, ..., [0]),
        ('2', 2, ..., [1]),
        ('0', 2, ..., []),
        ('3', 2, ..., []),
        # comma
        ('1,2', 2, ..., [0, 1]),
        ('0,3', 2, ..., []),
        # ranges
        ('2..4', 5, ..., [1, 2, 3]),
        ('0..2', 5, ..., [0, 1]),
        ('4..6', 5, ..., [3, 4]),
        ('4..2', 5, ..., [1, 2, 3]),
        # above/below selection
        ('one-above', 3, [1, 2], [0]),
        ('one-below', 3, [0, 1], [2]),
        ('one-above', 3, [], [2]),
        ('one-below', 3, [], [0]),
    ],
)
def test_get_all_indexes(
    expr: str,
    sub_count: int,
    sub_selection: T.Union[T.List[int], T.Any],
    expected_indexes: T.Union[T.List[int], T.Type[CommandError]],
) -> None:
    api = MagicMock()
    api.subs.events = [MagicMock() for _ in range(sub_count)]
    for i, event in enumerate(api.subs.events):
        event.prev = api.subs.events[i - 1] if i > 0 else None
        try:
            event.next = api.subs.events[i + 1]
        except LookupError:
            event.next = None
    if sub_selection is not Ellipsis:
        api.subs.selected_indexes = sub_selection
        api.subs.selected_events = [
            api.subs.events[idx] for idx in sub_selection
        ]
    else:
        api.subs.selected_indexes = []
        api.subs.selected_events = []

    sub_selection = SubtitlesSelection(api, expr)

    actual_indexes: T.Union[T.List[int], T.Type[CommandError]] = []
    try:
        actual_indexes = asyncio.get_event_loop().run_until_complete(
            sub_selection.get_all_indexes()
        )
    except CommandError as ex:
        actual_indexes = type(ex)

    assert actual_indexes == expected_indexes
