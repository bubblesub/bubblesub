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
import operator
import typing as T

import bubblesub.api
from bubblesub.api.cmd import BaseCommand
from bubblesub.ass.event import Event
from bubblesub.util import VerticalDirection, ShiftTarget


def _fmt_shift_target(shift_target: ShiftTarget) -> str:
    return {
        ShiftTarget.Start: 'selection start',
        ShiftTarget.End: 'selection end',
        ShiftTarget.Both: 'selection'
    }[shift_target]


class ScrollSpectrogramCommand(BaseCommand):
    """Scrolls the spectrogram horizontally by its width's percentage."""

    name = 'audio/scroll-spectrogram'

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

    name = 'audio/zoom-spectrogram'

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


class SnapSpectrogramSelectionToCurrentVideoFrameCommand(BaseCommand):
    """Snaps the spectrogram selection to the current video frame."""

    name = 'audio/snap-sel-to-current-video-frame'

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return (
            '&Snap '
            f'{_fmt_shift_target(self._shift_target)} to current video frame'
        )

    def __init__(self, api: bubblesub.api.Api, shift_target: str) -> None:
        """
        Initialize self.

        :param api: core API
        :param shift_target: how to snap the selection
        """
        super().__init__(api)
        self._shift_target = ShiftTarget[shift_target.title()]

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
        if self._shift_target == ShiftTarget.Start:
            self.api.media.audio.select(target, old_end)
        elif self._shift_target == ShiftTarget.End:
            self.api.media.audio.select(old_start, target)
        elif self._shift_target == ShiftTarget.Both:
            self.api.media.audio.select(target, target)
        else:
            raise AssertionError


class PlaceSpectrogramSelectionAtCurrentVideoFrameCommand(BaseCommand):
    """
    Realigns the selection to the current video frame.

    The selection start is placed at the current video frame
    and the selection size is set to the default subtitle duration.
    """

    name = 'audio/place-sel-at-current-video-frame'
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


class SnapSpectrogramSelectionToNearSubtitleCommand(BaseCommand):
    """Snaps the spectrogram selection to the nearest subtitle."""

    name = 'audio/snap-sel-to-near-sub'

    def __init__(
            self,
            api: bubblesub.api.Api,
            shift_target: str,
            snap_direction: str
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param shift_target: how to snap the selection
        :param snap_direction: direction to snap into
        """
        super().__init__(api)
        self._shift_target = ShiftTarget[shift_target.title()]
        self._direction = VerticalDirection[snap_direction.title()]

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return (
            f'&Snap '
            f'{_fmt_shift_target(self._shift_target)} to subtitle '
            f'{self._direction.name.lower()}'
        )

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        if not self.api.media.audio.has_selection:
            return False
        return self._nearest_sub is not None

    @property
    def _nearest_sub(self) -> T.Optional[Event]:
        if not self.api.subs.has_selection:
            return None
        if self._direction == VerticalDirection.Above:
            return self.api.subs.selected_events[0].prev
        elif self._direction == VerticalDirection.Below:
            return self.api.subs.selected_events[-1].next
        else:
            raise AssertionError

    async def run(self) -> None:
        """Carry out the command."""
        assert self._nearest_sub is not None
        if self._shift_target == ShiftTarget.Start:
            self.api.media.audio.select(
                self._nearest_sub.end,
                self.api.media.audio.selection_end
            )
        elif self._shift_target == ShiftTarget.End:
            self.api.media.audio.select(
                self.api.media.audio.selection_start,
                self._nearest_sub.start
            )
        elif self._shift_target == ShiftTarget.Both:
            if self._direction == VerticalDirection.Above:
                self.api.media.audio.select(
                    self._nearest_sub.end,
                    self._nearest_sub.end
                )
            elif self._direction == VerticalDirection.Below:
                self.api.media.audio.select(
                    self._nearest_sub.start,
                    self._nearest_sub.start
                )
            else:
                raise AssertionError
        else:
            raise AssertionError


class SnapSpectrogramSelectionToNearKeyframeCommand(BaseCommand):
    """Snaps the spectrogram selection to the nearest keyframe."""

    name = 'audio/snap-sel-to-near-keyframe'

    def __init__(
            self,
            api: bubblesub.api.Api,
            shift_target: str,
            snap_direction: str
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param shift_target: how to snap the selection
        :param snap_direction: direction to snap into
        """
        super().__init__(api)
        self._shift_target = ShiftTarget[shift_target.title()]
        self._direction = VerticalDirection[snap_direction.title()]

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
        return (
            '&Snap '
            f'{_fmt_shift_target(self._shift_target)} to keyframe '
            f'{self._direction.name.lower()}'
        )

    async def run(self) -> None:
        """Carry out the command."""
        origin = self._get_origin()
        new_start, new_end = self._get_new_pos(origin)
        self.api.media.audio.select(new_start, new_end)

    def _get_possible_pts(self) -> T.List[int]:
        return [
            self.api.media.video.timecodes[i]
            for i in self.api.media.video.keyframes
        ]

    def _get_origin(self) -> int:
        possible_pts = self._get_possible_pts()

        if self._direction == VerticalDirection.Above:
            possible_pts.reverse()
            func = operator.__lt__
            not_found_pts = 0
        elif self._direction == VerticalDirection.Below:
            func = operator.__gt__
            not_found_pts = self.api.media.max_pts
        else:
            raise AssertionError

        if self._shift_target == ShiftTarget.End:
            current_origin = self.api.media.audio.selection_end
        elif self._shift_target in {ShiftTarget.Start, ShiftTarget.Both}:
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
        if self._shift_target == ShiftTarget.Start:
            return origin, old_end
        elif self._shift_target == ShiftTarget.End:
            return old_start, origin
        elif self._shift_target == ShiftTarget.Both:
            return origin, origin
        raise AssertionError


class ShiftSpectrogramSelectionCommand(BaseCommand):
    """Shifts the spectrogram selection by the specified distance."""

    name = 'audio/shift-sel'

    def __init__(
            self,
            api: bubblesub.api.Api,
            shift_target: str,
            delta: int,
            frames: bool = True
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param shift_target: how to shift the selection
        :param delta: amount to shift the selection by
        :param frames: if true, shift by frames; otherwise by milliseconds
        """
        super().__init__(api)
        self._shift_target = ShiftTarget[shift_target.title()]
        self._delta = delta
        self._frames = frames

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        unit = 'frames' if self._frames else 'ms'
        return (
            '&Shift '
            f'{_fmt_shift_target(self._shift_target)} '
            f'({self._delta:+} {unit})'
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

            if self._shift_target == ShiftTarget.Start:
                self.api.media.audio.select(new_start, old_end)
            elif self._shift_target == ShiftTarget.End:
                self.api.media.audio.select(old_start, new_end)
            elif self._shift_target == ShiftTarget.Both:
                self.api.media.audio.select(new_start, new_end)
            else:
                raise AssertionError

        else:
            if self._shift_target == ShiftTarget.Start:
                self.api.media.audio.select(
                    min(old_end, old_start + self._delta), old_end
                )
            elif self._shift_target == ShiftTarget.End:
                self.api.media.audio.select(
                    old_start, max(old_start, old_end + self._delta)
                )
            elif self._shift_target == ShiftTarget.Both:
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
            SnapSpectrogramSelectionToNearSubtitleCommand,
            SnapSpectrogramSelectionToNearKeyframeCommand,
            SnapSpectrogramSelectionToCurrentVideoFrameCommand,
            PlaceSpectrogramSelectionAtCurrentVideoFrameCommand,
            ShiftSpectrogramSelectionCommand,
            CommitSpectrogramSelectionCommand,
    ]:
        cmd_api.register_core_command(T.cast(T.Type[BaseCommand], cls))
