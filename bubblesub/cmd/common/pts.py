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

"""Presentation timestamp, usable as an argument to commands."""

import bisect
import re
import typing as T

from PyQt5 import QtWidgets

import bubblesub.api
from bubblesub.api.cmd import CommandCanceled
from bubblesub.api.cmd import CommandError

MS_REGEX = re.compile(r'(?P<delta>[+-]?\d+)( milliseconds|ms)$')
FRAME_REGEX = re.compile(r'^(?P<delta>[+-]?\d+)( frames?|f)$')
KEYFRAME_REGEX = re.compile(r'^(?P<delta>[+-]?\d+)( keyframes?|kf)$')


def _plural_desc(term: str, count: int) -> str:
    if count == -1:
        return f'to previous {term}'
    if count == 1:
        return f'to next {term}'
    if count < 0:
        return f'by {-count} {term}s back'
    if count > 0:
        return f'by {count} {term}s ahead'
    return f'zero {term}s'


def _bisect(source: T.List[int], origin: int, delta: int) -> int:
    if delta > 0:
        # find leftmost value greater than origin
        idx = bisect.bisect_right(source, origin)
        idx += delta - 1
    elif delta < 0:
        # find rightmost value less than origin
        idx = bisect.bisect_left(source, origin)
        idx += delta
    else:
        raise AssertionError

    idx = max(0, min(idx, len(source)))
    return source[idx]


def _apply_frame(api: bubblesub.api.Api, origin: int, delta: int) -> int:
    if not api.media.video.timecodes:
        raise CommandError('timecode information is not available')

    return _bisect(api.media.video.timecodes, origin, delta)


def _apply_keyframe(api: bubblesub.api.Api, origin: int, delta: int) -> int:
    if not api.media.video.keyframes:
        raise CommandError('keyframe information is not available')

    possible_pts = [
        api.media.video.timecodes[i]
        for i in api.media.video.keyframes
    ]

    return _bisect(possible_pts, origin, delta)


class RelativePts:
    def __init__(self, api: bubblesub.api.Api, value: str) -> None:
        self.api = api
        self.value = (
            value
            .replace('previous', 'prev')
            .replace('subtitle', 'sub')
        )

    @property
    def description(self) -> str:
        match = MS_REGEX.match(self.value)
        if match:
            delta = int(match.group('delta'))
            return _plural_desc('millisecond', delta)

        match = KEYFRAME_REGEX.match(self.value)
        if match:
            delta = int(match.group('delta'))
            return _plural_desc('keyframe', delta)

        if self.value == 'prev-keyframe':
            return _plural_desc('keyframe', -1)

        if self.value == 'next-keyframe':
            return _plural_desc('keyframe', 1)

        match = FRAME_REGEX.match(self.value)
        if match:
            delta = int(match.group('delta'))
            return _plural_desc('frame', delta)

        if self.value == 'prev-frame':
            return _plural_desc('frame', -1)

        if self.value == 'next-frame':
            return _plural_desc('frame', 1)

        if self.value == 'current-frame':
            return 'to current frame'

        if self.value == 'prev-sub-start':
            return 'to previous subtitle start'

        if self.value == 'prev-sub-end':
            return 'to previous subtitle end'

        if self.value == 'next-sub-start':
            return 'to next subtitle start'

        if self.value == 'next-sub-end':
            return 'to next subtitle end'

        if self.value == 'default-sub-duration':
            return 'by default subtitle duration'

        if self.value == 'ask':
            return 'interactively'

        raise ValueError(f'unknown relative pts: "{self.value}"')

    async def apply(self, origin: int) -> int:
        match = MS_REGEX.match(self.value)
        if match:
            delta = int(match.group('delta'))
            return origin + delta

        match = KEYFRAME_REGEX.match(self.value)
        if match:
            delta = int(match.group('delta'))
            return _apply_keyframe(self.api, origin, delta)

        if self.value == 'prev-keyframe':
            return _apply_keyframe(self.api, origin, -1)

        if self.value == 'next-keyframe':
            return _apply_keyframe(self.api, origin, 1)

        match = FRAME_REGEX.match(self.value)
        if match:
            delta = int(match.group('delta'))
            return _apply_frame(self.api, origin, delta)

        if self.value == 'prev-frame':
            return _apply_frame(self.api, origin, -1)

        if self.value == 'next-frame':
            return _apply_frame(self.api, origin, 1)

        if self.value == 'current-frame':
            return self.api.media.video.align_pts_to_near_frame(
                self.api.media.current_pts
            )

        if self.value in {'prev-sub-start', 'prev-sub-end'}:
            sub = self.api.subs.selected_events[0].prev
            if sub is None:
                return 0
            if self.value == 'prev-sub-start':
                return sub.start
            if self.value == 'prev-sub-end':
                return sub.end
            raise AssertionError

        if self.value in {'next-sub-start', 'next-sub-end'}:
            sub = self.api.subs.selected_events[-1].next
            if sub is None:
                return self.api.media.max_pts
            if self.value == 'next-sub-start':
                return sub.start
            if self.value == 'next-sub-end':
                return sub.end
            raise AssertionError

        if self.value == 'default-sub-duration':
            return origin + self.api.opt.general.subs.default_duration

        if self.value == 'ask':
            value = await self.api.gui.exec(
                lambda main_window: self._show_dialog(main_window, origin)
            )
            if value is None:
                raise CommandCanceled
            return value

        raise ValueError(f'unknown relative pts: "{self.value}"')

    async def _show_dialog(
            self,
            main_window: QtWidgets.QMainWindow,
            origin: int
    ) -> T.Optional[int]:
        ret = bubblesub.ui.util.time_jump_dialog(
            main_window,
            absolute_label='Time to jump to:',
            relative_label='Time to jump by:',
            relative_checked=False,
            value=self.api.media.current_pts
        )

        if ret is None:
            return None
        value, is_relative = ret

        if is_relative:
            return origin + value
        return value
