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

import bubblesub.ui.util
from bubblesub.api import Api
from bubblesub.api.cmd import CommandCanceled
from bubblesub.api.cmd import CommandError

MS_REGEX = re.compile(r'(?P<delta>[+-]?\d+)( milliseconds| ?ms)$')
FRAME_REGEX = re.compile(r'^(?P<delta>[+-]?\d+)( frames?| ?f)$')
KEYFRAME_REGEX = re.compile(r'^(?P<delta>[+-]?\d+)( keyframes?| ?kf)$')
SUB_BOUNDARY_REGEX = re.compile(
    r'^(?P<origin>prev|previous|next|cur|current)'
    r'-sub-'
    r'(?P<boundary>start|end)$'
)


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


def _apply_frame(api: Api, origin: int, delta: int) -> int:
    if not api.media.video.timecodes:
        raise CommandError('timecode information is not available')

    return _bisect(api.media.video.timecodes, origin, delta)


def _apply_keyframe(api: Api, origin: int, delta: int) -> int:
    if not api.media.video.keyframes:
        raise CommandError('keyframe information is not available')

    possible_pts = [
        api.media.video.timecodes[i]
        for i in api.media.video.keyframes
    ]

    return _bisect(possible_pts, origin, delta)


class AbsolutePts:
    def __init__(self, api: Api, value: str) -> None:
        self.api = api
        self.value = (
            value
            .replace('previous', 'prev')
            .replace('subtitle', 'sub')
            .replace('current', 'cur')
        )

    async def get(self, align_to_near_frame: bool = False) -> int:
        ret = await self._get()
        if align_to_near_frame:
            ret = self.api.media.video.align_pts_to_near_frame(ret)
        return ret

    async def _get(self) -> int:
        if self.value == 'cur-frame':
            return self.api.media.current_pts

        if self.value == 'ask':
            return await self.api.gui.exec(self._show_abs_dialog)

        raise ValueError(f'unknown relative pts: "{self.value}"')

    async def _show_abs_dialog(
            self, main_window: QtWidgets.QMainWindow
    ) -> int:
        ret = bubblesub.ui.util.time_jump_dialog(
            main_window,
            relative_checked=False,
            value=self.api.media.current_pts,
            show_radio=False,
        )
        if ret is None:
            raise CommandCanceled
        value, _is_relative = ret
        return value


class RelativePts(AbsolutePts):
    async def apply(
            self, origin: int,
            align_to_near_frame: bool = False
    ) -> int:
        try:
            ret = await self._apply(origin)
        except ValueError:
            ret = await super().get()
        if align_to_near_frame:
            ret = self.api.media.video.align_pts_to_near_frame(ret)
        return ret

    async def _apply(self, origin: int) -> int:
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

        match = SUB_BOUNDARY_REGEX.match(self.value)
        if match:
            if match.group('origin') in {'prev', 'previous'}:
                sub = self.api.subs.selected_events[0].prev
            elif match.group('origin') == 'next':
                sub = self.api.subs.selected_events[-1].next
            elif match.group('origin') in {'cur', 'current'}:
                sub = self.api.subs.selected_events[0]
            else:
                raise AssertionError

            if sub is None:
                return 0

            if match.group('boundary') == 'start':
                return sub.start
            if match.group('boundary') == 'end':
                return sub.end
            raise AssertionError

        if self.value == 'default-sub-duration':
            return origin + self.api.opt.general.subs.default_duration

        if self.value == 'ask':
            return await self.api.gui.exec(
                lambda main_window: self._show_rel_dialog(main_window, origin)
            )

        raise ValueError(f'unknown relative pts: "{self.value}"')

    async def _show_rel_dialog(
            self,
            main_window: QtWidgets.QMainWindow,
            origin: int
    ) -> T.Optional[int]:
        ret = bubblesub.ui.util.time_jump_dialog(
            main_window,
            relative_checked=False,
            value=self.api.media.current_pts
        )
        if ret is None:
            raise CommandCanceled

        value, is_relative = ret
        if is_relative:
            return origin + value
        return value
