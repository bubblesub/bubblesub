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

"""Tests for bubblesub.api.video module."""

from collections.abc import Callable
from pathlib import Path
from typing import Union
from unittest.mock import Mock, PropertyMock, patch

import numpy as np
import pytest

from bubblesub.api.video import VideoStream


def _test_align_pts_to_frame(
    origin: int,
    expected: int,
    align_func: Callable[[VideoStream], Callable[[int], int]],
) -> None:
    """Test aligning PTS to frames using a few mocked frames.

    :param origin: source PTS
    :param expected: expected PTS
    :param align_func: the function to test
    """
    threading_api = Mock()
    log_api = Mock()
    subs_api = Mock()

    with patch(
        VideoStream.__module__ + "." + VideoStream.__name__ + ".timecodes",
        new_callable=PropertyMock,
        return_value=[0, 10, 20],
    ):
        stream = VideoStream(threading_api, log_api, subs_api, Path("dummy"))
        actual = align_func(stream)(origin)
        assert actual == expected


@pytest.mark.parametrize(
    "origin,expected",
    [
        (-1000, -1000),
        (-1, -1),
        (0, 0),
        (1, 0),
        (9, 0),
        (10, 10),
        (11, 10),
        (19, 10),
        (20, 20),
        (21, 20),
        (1000, 20),
    ],
)
def test_align_pts_to_prev_frame(origin: int, expected: int) -> None:
    """Test aligning PTS to the previous frame.

    :param origin: source PTS
    :param expected: expected PTS
    """
    _test_align_pts_to_frame(
        origin, expected, lambda stream: stream.align_pts_to_prev_frame
    )


@pytest.mark.parametrize(
    "origin,expected",
    [
        (-1000, 0),
        (-1, 0),
        (0, 0),
        (1, 10),
        (9, 10),
        (10, 10),
        (11, 20),
        (19, 20),
        (20, 20),
        (21, 21),
        (1000, 1000),
    ],
)
def test_align_pts_to_next_frame(origin: int, expected: int) -> None:
    """Test aligning PTS to the next frame.

    :param origin: source PTS
    :param expected: expected PTS
    """
    _test_align_pts_to_frame(
        origin, expected, lambda stream: stream.align_pts_to_next_frame
    )


@pytest.mark.parametrize(
    "origin,expected",
    [
        (-1000, 0),
        (-1, 0),
        (0, 0),
        (1, 0),
        (5, 0),
        (6, 10),
        (9, 10),
        (10, 10),
        (11, 10),
        (15, 10),
        (16, 20),
        (19, 20),
        (20, 20),
        (21, 20),
        (1000, 20),
    ],
)
def test_align_pts_to_near_frame(origin: int, expected: int) -> None:
    """Test aligning PTS to the nearest frame.

    :param origin: source PTS
    :param expected: expected PTS
    """
    _test_align_pts_to_frame(
        origin, expected, lambda stream: stream.align_pts_to_near_frame
    )


@pytest.mark.parametrize(
    "timecodes,pts,expected",
    [
        # no timecodes
        ([], -1, -1),
        ([], 0, -1),
        ([], 2.2, -1),
        ([], np.array([0], dtype=int), np.array([-1], dtype=int)),
        ([], np.array([0.0], dtype=float), np.array([-1], dtype=int)),
        # integers
        ([0, 10, 20], -1, 0),
        ([0, 10, 20], 0, 0),
        ([0, 10, 20], 1, 0),
        ([0, 10, 20], 9, 0),
        ([0, 10, 20], 10, 1),
        ([0, 10, 20], 11, 1),
        ([0, 10, 20], 19, 1),
        ([0, 10, 20], 20, 2),
        ([0, 10, 20], 21, 2),
        # floating points
        ([0, 10, 20], 0.1, 0),
        ([0, 10, 20], 9.9, 0),
        ([0, 10, 20], 10 - 1e-5, 0),
        ([0, 10, 20], 10.0, 1),
        ([0, 10, 20], 50.0, 2),
        # numpy arrays
        (
            [0, 10, 20],
            np.array([-1, 0, 1, 9, 10, 19, 20, 21], dtype=int),
            np.array([0, 0, 0, 0, 1, 1, 2, 2], dtype=int),
        ),
        (
            [0, 10, 20],
            np.array([0.1, 9.9, 10 - 1e5, 10.0, 50.0], dtype=float),
            np.array([0, 0, 0, 1, 2], dtype=int),
        ),
    ],
)
def test_frame_idx_from_pts(
    timecodes: list[int],
    pts: Union[float, int, np.ndarray],
    expected: Union[int, np.ndarray],
) -> None:
    """Test getting frame index from PTS.

    :param timecodes: frame timecodes to emulate
    :param pts: source PTS
    :param expected: expected frame index
    """
    threading_api = Mock()
    log_api = Mock()
    subs_api = Mock()

    with patch(
        VideoStream.__module__ + "." + VideoStream.__name__ + ".timecodes",
        new_callable=PropertyMock,
        return_value=timecodes,
    ):
        stream = VideoStream(threading_api, log_api, subs_api, Path("dummy"))
        if isinstance(pts, np.ndarray):
            np.testing.assert_array_equal(
                stream.frame_idx_from_pts(pts), expected
            )
        else:
            assert stream.frame_idx_from_pts(pts) == expected
