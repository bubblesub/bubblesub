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

"""Test SubtitlesSelection class."""

import asyncio
import typing as T
from unittest.mock import MagicMock

import pytest

from bubblesub.api.cmd import CommandError
from bubblesub.cmd.common import SubtitlesSelection


@pytest.mark.parametrize(
    "expr,sub_count,sub_selection,current_pts,expected_indexes",
    [
        # basic
        ("none", 3, ..., ..., []),
        ("all", 3, ..., ..., [0, 1, 2]),
        ("selected", 3, [], ..., []),
        ("selected", 3, [0], ..., [0]),
        ("selected", 3, [1, 2], ..., [1, 2]),
        # first/last
        ("first", 3, ..., ..., [0]),
        ("last", 3, ..., ..., [2]),
        ("first", 0, ..., ..., []),
        ("last", 0, ..., ..., []),
        # specific
        ("1", 2, ..., ..., [0]),
        ("2", 2, ..., ..., [1]),
        ("0", 2, ..., ..., []),
        ("3", 2, ..., ..., []),
        # comma
        ("1,2", 2, ..., ..., [0, 1]),
        ("0,3", 2, ..., ..., []),
        # ranges
        ("2..4", 5, ..., ..., [1, 2, 3]),
        ("0..2", 5, ..., ..., [0, 1]),
        ("4..6", 5, ..., ..., [3, 4]),
        ("4..2", 5, ..., ..., [1, 2, 3]),
        # above/below selection
        ("one-above", 3, [1, 2], ..., [0]),
        ("one-above", 3, [], 0, [0]),
        ("one-above", 3, [], 1, [0]),
        ("one-above", 3, [], 100, [1]),
        ("one-above", 3, [], 101, [1]),
        ("one-below", 3, [0, 1], ..., [2]),
        ("one-below", 3, [], 0, [0]),
        ("one-below", 3, [], 1, [1]),
        ("one-below", 3, [], 100, [1]),
        ("one-below", 3, [], 101, [2]),
    ],
)
def test_get_all_indexes(
    expr: str,
    sub_count: int,
    sub_selection: T.Union[T.List[int], T.Any],
    current_pts: T.Union[int, T.Any],
    expected_indexes: T.Union[T.List[int], T.Type[CommandError]],
) -> None:
    """Test that parsing various inputs returns expected subtitle indexes.

    :param expr: input expression to parse
    :param sub_count: how many subtitles to simulate
    :param sub_selection: current subtitle selection indexes to simulate
    :param current_pts: current video PTS to simulate
    :param expected_indexes: expected selection indexes
    """
    api = MagicMock()
    api.playback.current_pts = current_pts
    api.subs.events = [MagicMock() for _ in range(sub_count)]
    for i, event in enumerate(api.subs.events):
        event.index = i
        event.num = i + 1
        event.prev = api.subs.events[i - 1] if i > 0 else None
        event.start = i * 100
        event.end = i * 100 + 50
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
