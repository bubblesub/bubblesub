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
import enum
import operator
import typing as T

import bubblesub.api
from bubblesub.api.cmd import BaseCommand
from bubblesub.ass.event import Event


class SelectionMode(enum.IntEnum):
    """Spectrogram selection origin."""

    Start = 1
    End = 2
    Both = 3

    def __str__(self) -> str:
        """
        Human readable representation.

        :return: human readable representation
        """
        if self == SelectionMode.Start:
            return 'selection start'
        elif self == SelectionMode.End:
            return 'selection end'
        elif self == SelectionMode.Both:
            return 'selection'
        return super().__str__(self)


class Direction(enum.IntEnum):
    """Direction for commands."""

    Left = 1
    Prev = 1
    Previous = 1

    Right = 2
    Next = 2


class ScrollSpectrogramCommand(BaseCommand):
    """Scrolls the spectrogram horizontally by its width's percentage."""

    name = 'audio/scroll'

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        direction = 'forward' if self._delta > 0 else 'backward'
        return f'&Scroll spectrogram {direction} by {self._delta*100}%'

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


class ZoomSpectrogramCommand(BaseCommand):
    """Zooms the spectrogram in or out by the specified factor."""

    name = 'audio/zoom'

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return '&Zoom spectrogram %s' % ['in', 'out'][self._delta > 1]

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


class SnapSpectrogramSelectionToVideoCommand(BaseCommand):
    """Snaps the spectrogram selection to nearest video frame."""

    name = 'audio/snap-sel-to-video'

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return f'&Snap {self._selection_mode!s} to video'

    def __init__(self, api: bubblesub.api.Api, selection_mode: str) -> None:
        """
        Initialize self.

        :param api: core API
        :param selection_mode: what part of selection to snap
        """
        super().__init__(api)
        self._selection_mode = SelectionMode[selection_mode.title()]

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.audio.has_selection \
            and self.api.media.is_loaded

    async def run(self) -> None:
        """Carry out the command."""
        old_end = self.api.media.audio.selection_end
        old_start = self.api.media.audio.selection_start
        target = self.api.media.current_pts
        if self._selection_mode == SelectionMode.Start:
            self.api.media.audio.select(target, old_end)
        elif self._selection_mode == SelectionMode.End:
            self.api.media.audio.select(old_start, target)
        elif self._selection_mode == SelectionMode.Both:
            self.api.media.audio.select(target, target)
        else:
            raise AssertionError


class PlaceSpectrogramSelectionAtVideoCommand(BaseCommand):
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
            self.api.media.video.align_pts_to_next_frame(
                self.api.media.current_pts
                + self.api.opt.general.subs.default_duration
            )
        )


class SnapSpectrogramSelectionToKeyframeCommand(BaseCommand):
    """Snaps the spectrogram selection to the nearest keyframe."""

    name = 'audio/snap-sel-to-keyframe'

    def __init__(
            self,
            api: bubblesub.api.Api,
            selection_mode: str,
            snap_direction: str
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param selection_mode: what part of selection to snap
        :param snap_direction: direction to stap into
        """
        super().__init__(api)
        self._selection_mode = SelectionMode[selection_mode.title()]
        self._direction = Direction[snap_direction.title()]

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return (
            self.api.media.audio.has_selection
            and bool(self.api.media.video.keyframes)
        )

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        ret = f'&Snap {self._selection_mode!s} to '
        ret += {
            Direction.Previous: 'previous ',
            Direction.Next: 'next ',
        }[self._direction]
        ret += 'keyframe'

        return ret

    async def run(self) -> None:
        """Carry out the command."""
        origin = self._get_origin()
        new_start, new_end = self._get_new_pos(origin)
        self.api.media.audio.select(new_start, new_end)

    def _get_possible_pts(self) -> T.Iterable[int]:
        return [
            self.api.media.video.timecodes[i]
            for i in self.api.media.video.keyframes
        ]

    def _get_origin(self) -> int:
        possible_pts = self._get_possible_pts()

        if self._direction == Direction.Previous:
            possible_pts.reverse()
            func = operator.__lt__
            not_found_pts = 0
        elif self._direction == Direction.Next:
            func = operator.__gt__
            not_found_pts = self.api.media.max_pts
        else:
            raise AssertionError

        if self._selection_mode == SelectionMode.End:
            current_origin = self.api.media.audio.selection_end
        elif self._selection_mode in {SelectionMode.Start, SelectionMode.Both}:
            current_origin = self.api.media.audio.selection_start
        else:
            raise AssertionError

        for pts in possible_pts:
            if func(pts, current_origin):
                return pts
        return not_found_pts

    def _get_new_pos(self, origin: int) -> T.Tuple[int, int]:
        old_start = self.api.media.audio.selection_start
        old_end = self.api.media.audio.selection_end
        if self._selection_mode == SelectionMode.Start:
            return origin, old_end
        elif self._selection_mode == SelectionMode.End:
            return old_start, origin
        elif self._selection_mode == SelectionMode.Both:
            return origin, origin
        raise AssertionError


class SnapSpectrogramSelectionStartToPreviousSubtitleCommand(BaseCommand):
    """Snaps the spectrogram selection start to the subtitle above."""

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
        return self.api.subs.selected_events[0].prev

    async def run(self) -> None:
        """Carry out the command."""
        assert self._prev_sub is not None
        self.api.media.audio.select(
            self._prev_sub.end,
            self.api.media.audio.selection_end
        )


class SnapSpectrogramSelectionEndToNextSubtitleCommand(BaseCommand):
    """Snaps the spectrogram selection end to the subtitle below."""

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
        return self.api.subs.selected_events[-1].next

    async def run(self) -> None:
        """Carry out the command."""
        assert self._next_sub is not None
        self.api.media.audio.select(
            self.api.media.audio.selection_start,
            self._next_sub.start
        )


class ShiftSpectrogramSelectionCommand(BaseCommand):
    """Shifts the spectrogram selection by the specified distance."""

    name = 'audio/shift-sel'

    def __init__(
            self,
            api: bubblesub.api.Api,
            selection_mode: str,
            delta: int,
            frames: bool = True
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param selection_mode: what part of selection to shift
        :param delta: amount to shift the selection by
        :param frames: if true, shift by frames; otherwise by milliseconds
        """
        super().__init__(api)
        self._selection_mode = SelectionMode[selection_mode.title()]
        self._delta = delta
        self._frames = frames

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        unit = 'frames' if self._frames else 'ms'
        return f'&Shift {self._selection_mode!s} ({self._delta:+} {unit})'

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
        old_start = self.api.media.audio.selection_start
        old_end = self.api.media.audio.selection_end

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

            new_start = self.api.media.video.timecodes[idx1]
            new_end = self.api.media.video.timecodes[idx2]

            if self._selection_mode == SelectionMode.Start:
                self.api.media.audio.select(new_start, old_end)
            elif self._selection_mode == SelectionMode.End:
                self.api.media.audio.select(old_start, new_end)
            elif self._selection_mode == SelectionMode.Both:
                self.api.media.audio.select(new_start, new_end)
            else:
                raise AssertionError

        else:
            if self._selection_mode == SelectionMode.Start:
                self.api.media.audio.select(
                    min(old_end, old_start + self._delta), old_end
                )
            elif self._selection_mode == SelectionMode.End:
                self.api.media.audio.select(
                    old_start, max(old_start, old_end + self._delta)
                )
            elif self._selection_mode == SelectionMode.Both:
                self.api.media.audio.select(
                    old_start + self._delta, old_end + self._delta
                )
            else:
                raise AssertionError


class CommitSpectrogramSelectionCommand(BaseCommand):
    """
    Commits the spectrogram selection into the current subtitle.

    The selected subtitle start and end times is synced to the current
    spectrogram selection boundaries.
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
            for sub in self.api.subs.selected_events:
                sub.begin_update()
                sub.start = self.api.media.audio.selection_start
                sub.end = self.api.media.audio.selection_end
                sub.end_update()


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    """
    Register commands in this file into the command API.

    :param cmd_api: command API
    """
    for cls in [
            ScrollSpectrogramCommand,
            ZoomSpectrogramCommand,
            SnapSpectrogramSelectionToKeyframeCommand,
            SnapSpectrogramSelectionToVideoCommand,
            PlaceSpectrogramSelectionAtVideoCommand,
            SnapSpectrogramSelectionStartToPreviousSubtitleCommand,
            SnapSpectrogramSelectionEndToNextSubtitleCommand,
            ShiftSpectrogramSelectionCommand,
            CommitSpectrogramSelectionCommand,
    ]:
        cmd_api.register_core_command(T.cast(T.Type[BaseCommand], cls))
