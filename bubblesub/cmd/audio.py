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

"""Commands related to audio and audio selection."""

import bisect
import typing as T

import bubblesub.api
from bubblesub.api.cmd import CoreCommand
from bubblesub.ass.event import Event


class AudioScrollCommand(CoreCommand):
    """Scrolls the waveform viewport horizontally by its width's percentage."""

    name = 'audio/scroll'

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        direction = 'forward' if self._delta > 0 else 'backward'
        return f'&Scroll waveform {direction} by {self._delta*100}%'

    def __init__(self, api: bubblesub.api.Api, delta: float) -> None:
        """
        Initialize self.

        :param api: core API
        :param delta: factor to shift the view by
        """
        super().__init__(api)
        self._delta = delta

    async def run(self) -> None:
        """Carry out the command."""
        distance = int(self._delta * self.api.media.audio.view_size)
        self.api.media.audio.move_view(distance)


class AudioZoomCommand(CoreCommand):
    """Zooms the waveform viewport in or out by the specified factor."""

    name = 'audio/zoom'

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return '&Zoom waveform %s' % ['in', 'out'][self._delta > 1]

    def __init__(self, api: bubblesub.api.Api, delta: int) -> None:
        """
        Initialize self.

        :param api: core API
        :param delta: factor to zoom the view by
        """
        super().__init__(api)
        self._delta = delta

    async def run(self) -> None:
        """Carry out the command."""
        mouse_x = 0.5
        cur_factor = self.api.media.audio.view_size / self.api.media.audio.size
        new_factor = cur_factor * self._delta
        self.api.media.audio.zoom_view(new_factor, mouse_x)


class AudioSnapSelectionStartToVideoCommand(CoreCommand):
    """Snaps the waveform selection start to nearest video frame."""

    name = 'audio/snap-sel-start-to-video'
    menu_name = '&Snap selection start to video'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.audio.has_selection \
            and self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        self.api.media.audio.select(
            self.api.media.current_pts,
            self.api.media.audio.selection_end
        )


class AudioSnapSelectionEndToVideoCommand(CoreCommand):
    """Snaps the waveform selection end to nearest video frame."""

    name = 'audio/snap-sel-end-to-video'
    menu_name = '&Snap selection end to video'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.audio.has_selection \
            and self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        self.api.media.audio.select(
            self.api.media.audio.selection_start,
            self.api.media.current_pts
        )


class AudioPlaceSelectionAtVideoCommand(CoreCommand):
    """
    Realigns the selection to the current video frame.

    The selection start is placed at the current video frame
    and the selection size is set to the default subtitle duration.
    """

    name = 'audio/place-sel-at-video'
    menu_name = '&Place selection at current video frame'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.audio.has_selection \
            and self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        self.api.media.audio.select(
            self.api.media.current_pts,
            self.api.media.current_pts
            + self.api.opt.general.subs.default_duration
        )


class AudioSnapSelectionStartToPreviousSubtitleCommand(CoreCommand):
    """Snaps the waveform selection start to the subtitle above."""

    name = 'audio/snap-sel-start-to-prev-sub'
    menu_name = '&Snap selection start to previous subtitle'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        if not self.api.media.audio.has_selection:
            return False
        return self._prev_sub is not None

    @property
    def _prev_sub(self) -> T.Optional[Event]:
        if not self.api.subs.has_selection:
            return None
        return self.api.subs.selected_lines[0].prev

    async def run(self) -> None:
        """Carry out the command."""
        assert self._prev_sub is not None
        self.api.media.audio.select(
            self._prev_sub.end,
            self.api.media.audio.selection_end
        )


class AudioSnapSelectionEndToNextSubtitleCommand(CoreCommand):
    """Snaps the waveform selection end to the subtitle below."""

    name = 'audio/snap-sel-end-to-next-sub'
    menu_name = '&Snap selection start to next subtitle'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        if not self.api.media.audio.has_selection:
            return False
        return self._next_sub is not None

    @property
    def _next_sub(self) -> T.Optional[Event]:
        if not self.api.subs.has_selection:
            return None
        return self.api.subs.selected_lines[-1].next

    async def run(self) -> None:
        """Carry out the command."""
        assert self._next_sub is not None
        self.api.media.audio.select(
            self.api.media.audio.selection_start,
            self._next_sub.start
        )


class AudioShiftSelectionStartCommand(CoreCommand):
    """Shifts the waveform selection start by the specified distance."""

    name = 'audio/shift-sel-start'

    def __init__(
            self,
            api: bubblesub.api.Api,
            delta: int,
            frames: bool = True
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param delta: amount to shift the selection by
        :param frames: if true, shift by frames; otherwise by milliseconds
        """
        super().__init__(api)
        self._delta = delta
        self._frames = frames

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return '&Shift selection start ({:+} {})'.format(
            self._delta,
            'frames' if self._frames else 'ms'
        )

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.audio.has_selection and bool(
            not self._frames or self.api.media.video.timecodes
        )

    async def run(self) -> None:
        """Carry out the command."""
        if self._frames:
            idx = bisect.bisect_left(
                self.api.media.video.timecodes,
                self.api.media.audio.selection_start
            )
            idx += self._delta
            idx = max(0, min(idx, len(self.api.media.video.timecodes) - 1))
            self.api.media.audio.select(
                self.api.media.video.timecodes[idx],
                self.api.media.audio.selection_end
            )
        else:
            self.api.media.audio.select(
                min(
                    self.api.media.audio.selection_end,
                    self.api.media.audio.selection_start + self._delta
                ),
                self.api.media.audio.selection_end
            )


class AudioShiftSelectionEndCommand(CoreCommand):
    """Shifts the waveform selection end by the specified distance."""

    name = 'audio/shift-sel-end'

    def __init__(
            self,
            api: bubblesub.api.Api,
            delta: int,
            frames: bool = True
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param delta: amount to shift the selection
        :param frames: if true, shift by frames; otherwise by milliseconds
        """
        super().__init__(api)
        self._delta = delta
        self._frames = frames

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return '&Shift selection end ({:+} {})'.format(
            self._delta, 'frames' if self._frames else 'ms'
        )

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.audio.has_selection and bool(
            not self._frames or self.api.media.video.timecodes
        )

    async def run(self) -> None:
        """Carry out the command."""
        if self._frames:
            idx = bisect.bisect_left(
                self.api.media.video.timecodes,
                self.api.media.audio.selection_end
            )
            idx += self._delta
            idx = max(0, min(idx, len(self.api.media.video.timecodes) - 1))
            self.api.media.audio.select(
                self.api.media.audio.selection_start,
                self.api.media.video.timecodes[idx]
            )
        else:
            self.api.media.audio.select(
                self.api.media.audio.selection_start,
                max(
                    self.api.media.audio.selection_start,
                    self.api.media.audio.selection_end + self._delta
                )
            )


class AudioShiftSelectionCommand(CoreCommand):
    """Shifts the waveform selection start/end by the specified distance."""

    name = 'audio/shift-sel'

    def __init__(
            self,
            api: bubblesub.api.Api,
            delta: int,
            frames: bool = True
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param delta: amount to shift the selection
        :param frames: if true, shift by frames; otherwise by milliseconds
        """
        super().__init__(api)
        self._delta = delta
        self._frames = frames

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return '&Shift selection ({:+} {})'.format(
            self._delta, 'frames' if self._frames else 'ms'
        )

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.audio.has_selection and bool(
            not self._frames or self.api.media.video.timecodes
        )

    async def run(self) -> None:
        """Carry out the command."""
        if self._frames:
            idx1 = bisect.bisect_left(
                self.api.media.video.timecodes,
                self.api.media.audio.selection_start
            )
            idx2 = bisect.bisect_left(
                self.api.media.video.timecodes,
                self.api.media.audio.selection_end
            )
            idx1 += self._delta
            idx2 += self._delta
            idx1 = max(0, min(idx1, len(self.api.media.video.timecodes) - 1))
            idx2 = max(0, min(idx2, len(self.api.media.video.timecodes) - 1))
            self.api.media.audio.select(
                self.api.media.video.timecodes[idx1],
                self.api.media.video.timecodes[idx2]
            )
        else:
            self.api.media.audio.select(
                self.api.media.audio.selection_start + self._delta,
                self.api.media.audio.selection_end + self._delta
            )


class AudioCommitSelectionCommand(CoreCommand):
    """
    Commits the waveform selection into the current subtitle.

    The selected subtitle start and end times is synced to the current
    waveform selection boundaries.
    """

    name = 'audio/commit-sel'
    menu_name = '&Commit selection to subtitle'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.subs.has_selection \
            and self.api.media.audio.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        with self.api.undo.capture():
            for sub in self.api.subs.selected_lines:
                sub.begin_update()
                sub.start = self.api.media.audio.selection_start
                sub.end = self.api.media.audio.selection_end
                sub.end_update()
