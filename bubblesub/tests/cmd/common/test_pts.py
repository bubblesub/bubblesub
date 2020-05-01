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

"""Test Pts class."""

import asyncio
import typing as T
from unittest.mock import Mock

import pytest

from bubblesub.api.cmd import CommandError
from bubblesub.cmd.common import Pts


def _assert_pts_value(
    pts: Pts,
    expected_value: T.Union[int, T.Type[CommandError]],
    origin: T.Optional[int] = None,
) -> None:
    actual_value: T.Union[int, T.Type[CommandError]] = 0
    try:
        actual_value = asyncio.get_event_loop().run_until_complete(
            pts.get(origin=origin)
        )
    except CommandError as ex:
        actual_value = type(ex)

    assert actual_value == expected_value


def _mock_subs_api(sub_times, sub_selection) -> Mock:
    events = []
    for start, end in sub_times:
        events.append(Mock(start=start, end=end))
    for i, event in enumerate(events):
        event.prev = events[i - 1] if i > 0 else None
        event.next = events[i + 1] if i + 1 < len(events) else None

    def _mock_get(idx):
        try:
            return events[idx]
        except IndexError:
            return None

    def _mock_getitem(cls, idx):
        return events[idx]

    def _mock_len(cls):
        return len(events)

    subs_api = Mock()
    subs_api.events.get = _mock_get
    subs_api.events.__getitem__ = _mock_getitem
    subs_api.events.__len__ = _mock_len
    subs_api.selected_events = [events[idx] for idx in sub_selection]
    return subs_api


@pytest.mark.parametrize(
    "expr,origin,expected_value",
    [
        ("", None, CommandError),
        ("", 25, CommandError),
        ("+", None, CommandError),
        ("+", 25, CommandError),
        ("0ms+", None, CommandError),
        ("0ms+", 25, CommandError),
        ("0ms++", None, CommandError),
        ("0ms++", 25, CommandError),
        ("500ms", None, 500),
        ("500ms", 25, 500),
        ("+500ms", None, 500),
        ("+500ms", 25, 525),
        ("-500ms", None, -500),
        ("-500ms", 25, -475),
        ("0ms+500ms", None, 500),
        ("0ms+500ms", 25, 500),
        ("25ms+500ms", None, 525),
        ("25ms+500ms", 25, 525),
        ("500ms-25ms", None, 475),
        ("500ms-25ms", 25, 475),
        ("500", None, CommandError),
        ("500", 0, CommandError),
        ("ms", None, CommandError),
        ("ms", 0, CommandError),
        ("cfcf", None, CommandError),
        ("cfcf", 0, CommandError),
        ("0 ms", None, 0),
        ("0ms + 0ms", None, 0),
        ("0ms  +  0ms", None, 0),
        ("  0ms  +  0ms  ", None, 0),
        ("1s", None, 1000),
        ("+1s", None, 1000),
        ("+1 s", 1, 1001),
        ("+1.5 s", None, 1500),
        ("2m", None, 120_000),
        ("2 m", None, 120_000),
        ("2.5 m", None, 150_000),
        ("2m3s", None, 123_000),
        ("2 m 3 s", None, 123_000),
        ("2.5 m 3.5 s", None, 153_500),
        ("1", None, CommandError),
        ("01", None, CommandError),
        (":01", None, CommandError),
        ("1:23", None, 83000),
        ("12:34", None, 754_000),
        ("1:23:45", None, 5_025_000),
        ("12:34:56", None, 45_296_000),
        ("12:34:56.1", None, 45_296_100),
        ("12:34:56.1234", None, 45_296_123),
        ("000:01", None, CommandError),
    ],
)
def test_basic_arithmetic(
    expr: str,
    origin: T.Optional[int],
    expected_value: T.Union[int, T.Type[CommandError]],
) -> None:
    """Test time arithemtic.

    :param expr: input expression to parse
    :param origin: optional origin to parse against
    :param expected_value: expected PTS
    """
    api = Mock()
    pts = Pts(api, expr)

    _assert_pts_value(pts, expected_value, origin)


@pytest.mark.parametrize(
    "expr,sub_times,sub_selection,expected_value",
    [
        ("fs.s", [(1, 2), (3, 4), (5, 6)], [1], 1),
        ("fs.e", [(1, 2), (3, 4), (5, 6)], [1], 2),
        ("ls.s", [(1, 2), (3, 4), (5, 6)], [1], 5),
        ("ls.e", [(1, 2), (3, 4), (5, 6)], [1], 6),
        ("cs.s", [(1, 2), (3, 4), (5, 6)], [1], 3),
        ("cs.e", [(1, 2), (3, 4), (5, 6)], [1], 4),
        ("ps.s", [(1, 2), (3, 4), (5, 6)], [1], 1),
        ("ps.e", [(1, 2), (3, 4), (5, 6)], [1], 2),
        ("ns.s", [(1, 2), (3, 4), (5, 6)], [1], 5),
        ("ns.e", [(1, 2), (3, 4), (5, 6)], [1], 6),
        ("ps.s", [(1, 2), (3, 4), (5, 6)], [0], 0),
        ("ps.e", [(1, 2), (3, 4), (5, 6)], [0], 0),
        ("ns.s", [(1, 2), (3, 4), (5, 6)], [2], 0),
        ("ns.e", [(1, 2), (3, 4), (5, 6)], [2], 0),
        ("s1.s", [(1, 2), (3, 4), (5, 6)], [], 1),
        ("s1.e", [(1, 2), (3, 4), (5, 6)], [], 2),
        ("s2.s", [(1, 2), (3, 4), (5, 6)], [], 3),
        ("s2.e", [(1, 2), (3, 4), (5, 6)], [], 4),
        ("s3.s", [(1, 2), (3, 4), (5, 6)], [], 5),
        ("s3.e", [(1, 2), (3, 4), (5, 6)], [], 6),
        ("s1.s", [], [], 0),
        ("s1.e", [], [], 0),
        ("s3.s", [(1, 2)], [], 1),
        ("s3.e", [(1, 2)], [], 2),
        ("s0.s", [(1, 2)], [], 1),
        ("s0.e", [(1, 2)], [], 2),
    ],
)
def test_subtitles(
    expr: str,
    sub_times: T.List[T.Tuple[int, int]],
    sub_selection: T.List[int],
    expected_value: int,
) -> None:
    """Test first, last, current, previous, next and selected subtitle
    boundaries.

    :param expr: input expression to parse
    :param sub_times: subtitle PTS to simulate
    :param sub_selection: current subtitle selection indexes to simulate
    :param expected_value: expected PTS
    """
    api = Mock()
    api.subs = _mock_subs_api(sub_times, sub_selection)

    pts = Pts(api, expr)

    _assert_pts_value(pts, expected_value)


@pytest.mark.parametrize(
    "expr,frame_times,cur_frame_idx,keyframe_indexes,expected_value",
    [
        ("ff", [10, 20, 30], 1, [], 10),
        ("lf", [10, 20, 30], 1, [], 30),
        ("cf", [10, 20, 30], 1, [], 20),
        ("pf", [10, 20, 30], 1, [], 10),
        ("nf", [10, 20, 30], 1, [], 30),
        ("cf", [], ..., [], 0),
        ("pf", [], ..., [], CommandError),
        ("nf", [], ..., [], CommandError),
        ("1f", [10, 20, 30], ..., [], 10),
        ("2f", [10, 20, 30], ..., [], 20),
        ("3f", [10, 20, 30], ..., [], 30),
        ("0f", [10, 20, 30], ..., [], 10),
        ("5f", [10, 20, 30], ..., [], 30),
        ("1f", [], ..., [], CommandError),
        ("5ms+1f", [10, 20, 30], ..., [], 10),
        ("9ms+1f", [10, 20, 30], ..., [], 10),
        ("10ms+1f", [10, 20, 30], ..., [], 20),
        ("11ms+1f", [10, 20, 30], ..., [], 20),
        ("30ms+1f", [10, 20, 30], ..., [], 30),
        ("31ms+1f", [10, 20, 30], ..., [], 30),
        ("9ms-1f", [10, 20, 30], ..., [], 10),
        ("10ms-1f", [10, 20, 30], ..., [], 10),
        ("11ms-1f", [10, 20, 30], ..., [], 10),
        ("19ms-1f", [10, 20, 30], ..., [], 10),
        ("20ms-1f", [10, 20, 30], ..., [], 10),
        ("21ms-1f", [10, 20, 30], ..., [], 20),
        ("31ms-1f", [10, 20, 30], ..., [], 30),
        ("1f+1f", [10, 20, 30], ..., [], 20),
        ("1f+1ms", [10, 20, 30], ..., [], 11),
        ("1f+1ms+1f", [10, 20, 30], ..., [], 20),
        ("fkf", [10, 20, 30, 40], 1, [0, 1, 3], 10),
        ("lkf", [10, 20, 30, 40], 1, [0, 1, 3], 40),
        ("ckf", [10, 20, 30, 40], 1, [0, 1, 3], 20),
        ("ckf", [10, 20, 30, 40], 2, [0, 1, 3], 20),
        ("pkf", [10, 20, 30, 40], 1, [0, 1, 3], 10),
        ("nkf", [10, 20, 30, 40], 1, [0, 1, 2], 30),
        ("nkf", [10, 20, 30, 40], 1, [0, 1, 3], 40),
        ("ckf", [], ..., [], CommandError),
        ("pkf", [], ..., [], CommandError),
        ("nkf", [], ..., [], CommandError),
        ("1kf", [10, 20, 30], ..., [0, 2], 10),
        ("2kf", [10, 20, 30], ..., [0, 2], 30),
        ("0kf", [10, 20, 30], ..., [0, 2], 10),
        ("3kf", [10, 20, 30], ..., [0, 2], 30),
        ("1kf", [], ..., [], CommandError),
        ("5ms+1kf", [10, 20, 30], ..., [0, 2], 10),
        ("9ms+1kf", [10, 20, 30], ..., [0, 2], 10),
        ("10ms+1kf", [10, 20, 30], ..., [0, 1], 20),
        ("10ms+1kf", [10, 20, 30], ..., [0, 2], 30),
        ("11ms+1kf", [10, 20, 30], ..., [0, 1], 20),
        ("11ms+1kf", [10, 20, 30], ..., [0, 2], 30),
        ("31ms+1kf", [10, 20, 30], ..., [0, 1], 20),
        ("31ms+1kf", [10, 20, 30], ..., [0, 2], 30),
        ("9ms-1kf", [10, 20, 30], ..., [0, 1, 2], 10),
        ("10ms-1kf", [10, 20, 30], ..., [0, 1, 2], 10),
        ("11ms-1kf", [10, 20, 30], ..., [0, 1, 2], 10),
        ("19ms-1kf", [10, 20, 30], ..., [0, 1, 2], 10),
        ("20ms-1kf", [10, 20, 30], ..., [0, 1, 2], 10),
        ("21ms-1kf", [10, 20, 30], ..., [0, 1, 2], 20),
        ("31ms-1kf", [10, 20, 30], ..., [0, 1, 2], 30),
    ],
)
def test_frames(
    expr: str,
    frame_times: T.List[int],
    cur_frame_idx: T.Any,
    keyframe_indexes: T.List[int],
    expected_value: T.Union[int, T.Type[CommandError]],
) -> None:
    """Test frame and keyframe arithmetic.

    :param expr: input expression to parse
    :param frame_times: frame PTS to simulate
    :param cur_frame_idx: current video frame index to simulate
    :param keyframe_indexes: which frames are keyframes to simulate
    :param expected_value: expected PTS
    """
    api = Mock()
    api.video.current_stream.timecodes = frame_times
    api.video.current_stream.keyframes = keyframe_indexes
    if cur_frame_idx is Ellipsis:
        api.playback.current_pts = 0
    else:
        api.playback.current_pts = frame_times[cur_frame_idx]
    pts = Pts(api, expr)

    _assert_pts_value(pts, expected_value)


@pytest.mark.parametrize(
    "expr,selection,expected_value", [("a.s", (1, 2), 1), ("a.e", (1, 2), 2)]
)
def test_audio_selection(
    expr: str,
    selection: T.Tuple[int, int],
    expected_value: T.Union[int, T.Type[CommandError]],
) -> None:
    """Test audio selection magic strings.

    :param expr: input expression to parse
    :param selection: audio selection to simulate
    :param expected_value: expected PTS
    """
    api = Mock()
    api.audio.view.selection_start = selection[0]
    api.audio.view.selection_end = selection[1]
    pts = Pts(api, expr)
    _assert_pts_value(pts, expected_value)


@pytest.mark.parametrize(
    "expr,view,expected_value", [("av.s", (1, 2), 1), ("av.e", (1, 2), 2)]
)
def test_audio_view(
    expr: str, view: T.Tuple[int, int], expected_value: int
) -> None:
    """Test spectrogram viewport magic strings.

    :param expr: input expression to parse
    :param view: audio view to simulate
    :param expected_value: expected PTS
    """
    api = Mock()
    api.audio.view.view_start = view[0]
    api.audio.view.view_end = view[1]
    pts = Pts(api, expr)
    _assert_pts_value(pts, expected_value)


def test_default_subtitle_duration() -> None:
    """Test default subtitle duration magic string."""
    api = Mock()
    api.cfg.opt = {"subs": {"default_duration": 123}}
    pts = Pts(api, "dsd")

    _assert_pts_value(pts, 123)


def test_min_max() -> None:
    """Test min and max possible PTS magic strings."""
    api = Mock()
    api.playback.max_pts = 999

    min_pts = Pts(api, "min")
    max_pts = Pts(api, "max")

    _assert_pts_value(min_pts, 0)
    _assert_pts_value(max_pts, 999)
