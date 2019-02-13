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

import mock
import pytest

from bubblesub.api.video import VideoApi


def _test_align_pts_to_frame(
    origin: int,
    expected: int,
    align_func: T.Callable[[VideoApi], T.Callable[[int], int]],
) -> None:
    log_api = mock.MagicMock()
    playback_api = mock.MagicMock()
    subs_api = mock.MagicMock()

    with mock.patch(
        VideoApi.__module__ + "." + VideoApi.__name__ + ".timecodes",
        new_callable=mock.PropertyMock,
    ) as video_api_mock:
        video_api_mock.return_value = [0, 10, 20]

        video_api = VideoApi(log_api, playback_api, subs_api)
        actual = align_func(video_api)(origin)
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
    _test_align_pts_to_frame(
        origin, expected, lambda video_api: video_api.align_pts_to_prev_frame
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
    _test_align_pts_to_frame(
        origin, expected, lambda video_api: video_api.align_pts_to_next_frame
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
    _test_align_pts_to_frame(
        origin, expected, lambda video_api: video_api.align_pts_to_near_frame
    )
