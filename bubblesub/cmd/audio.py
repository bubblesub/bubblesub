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

import argparse
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
    name = 'audio/scroll-spectrogram'
    help_text = (
        'Scrolls the spectrogram horizontally by its width\'s percentage.'
    )

    @property
    def menu_name(self) -> str:
        direction = 'forward' if self.args.delta > 0 else 'backward'
        return f'&Scroll spectrogram {direction} by {self.args.delta*100}%'

    async def run(self) -> None:
        distance = int(self.args.delta * self.api.media.audio.view_size)
        self.api.media.audio.move_view(distance)

    @staticmethod
    def _decorate_parser(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-d', '--delta',
            help='factor to shift the view by',
            type=float,
            required=True
        )


class ZoomSpectrogramCommand(BaseCommand):
    name = 'audio/zoom-spectrogram'
    help_text = 'Zooms the spectrogram in or out by the specified factor.'

    @property
    def menu_name(self) -> str:
        return '&Zoom spectrogram %s' % ['in', 'out'][self.args.delta > 1]

    async def run(self) -> None:
        mouse_x = 0.5
        cur_factor = self.api.media.audio.view_size / self.api.media.audio.size
        new_factor = cur_factor * self.args.delta
        self.api.media.audio.zoom_view(new_factor, mouse_x)

    @staticmethod
    def _decorate_parser(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-d', '--delta',
            help='factor to zoom the view by',
            type=float,
            required=True
        )


class SnapSpectrogramSelectionToCurrentVideoFrameCommand(BaseCommand):
    name = 'audio/snap-sel-to-current-video-frame'
    help_text = 'Snaps the spectrogram selection to the current video frame.'

    @property
    def menu_name(self) -> str:
        return (
            '&Snap '
            f'{_fmt_shift_target(self.args.target)} '
            'to current video frame'
        )

    @property
    def is_enabled(self) -> bool:
        return self.api.media.audio.has_selection \
            and self.api.media.is_loaded

    async def run(self) -> None:
        old_end = self.api.media.audio.selection_end
        old_start = self.api.media.audio.selection_start
        target = self.api.media.current_pts
        if self.args.target == ShiftTarget.Start:
            self.api.media.audio.select(target, old_end)
        elif self.args.target == ShiftTarget.End:
            self.api.media.audio.select(old_start, target)
        elif self.args.target == ShiftTarget.Both:
            self.api.media.audio.select(target, target)
        else:
            raise AssertionError

    @staticmethod
    def _decorate_parser(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-t', '--target',
            help='how to snap the selection',
            type=ShiftTarget.from_string,
            choices=list(ShiftTarget),
            required=True
        )


class PlaceSpectrogramSelectionAtCurrentVideoFrameCommand(BaseCommand):
    name = 'audio/place-sel-at-current-video-frame'
    menu_name = '&Place selection at current video frame'
    help_text = (
        'Realigns the selection to the current video frame. '
        'The selection start is placed at the current video frame '
        'and the selection size is set to the default subtitle duration.'
    )

    @property
    def is_enabled(self) -> bool:
        return self.api.media.audio.has_selection \
            and self.api.subs.has_selection

    async def run(self) -> None:
        self.api.media.audio.select(
            self.api.media.current_pts,
            self.api.media.video.align_pts_to_next_frame(
                self.api.media.current_pts
                + self.api.opt.general.subs.default_duration
            )
        )


class SnapSpectrogramSelectionToNearSubtitleCommand(BaseCommand):
    name = 'audio/snap-sel-to-near-sub'
    help_text = 'Snaps the spectrogram selection to the nearest subtitle.'

    @property
    def menu_name(self) -> str:
        return (
            f'&Snap '
            f'{_fmt_shift_target(self.args.target)} to subtitle '
            f'{self.args.direction.name.lower()}'
        )

    @property
    def is_enabled(self) -> bool:
        if not self.api.media.audio.has_selection:
            return False
        return self._nearest_sub is not None

    @property
    def _nearest_sub(self) -> T.Optional[Event]:
        if not self.api.subs.has_selection:
            return None
        if self.args.direction == VerticalDirection.Above:
            return self.api.subs.selected_events[0].prev
        elif self.args.direction == VerticalDirection.Below:
            return self.api.subs.selected_events[-1].next
        else:
            raise AssertionError

    async def run(self) -> None:
        assert self._nearest_sub is not None
        if self.args.target == ShiftTarget.Start:
            self.api.media.audio.select(
                self._nearest_sub.end,
                self.api.media.audio.selection_end
            )
        elif self.args.target == ShiftTarget.End:
            self.api.media.audio.select(
                self.api.media.audio.selection_start,
                self._nearest_sub.start
            )
        elif self.args.target == ShiftTarget.Both:
            if self.args.direction == VerticalDirection.Above:
                self.api.media.audio.select(
                    self._nearest_sub.end,
                    self._nearest_sub.end
                )
            elif self.args.direction == VerticalDirection.Below:
                self.api.media.audio.select(
                    self._nearest_sub.start,
                    self._nearest_sub.start
                )
            else:
                raise AssertionError
        else:
            raise AssertionError

    @staticmethod
    def _decorate_parser(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-t', '--target',
            help='how to snap the selection',
            type=ShiftTarget.from_string,
            choices=list(ShiftTarget),
            required=True
        )
        parser.add_argument(
            '-d', '--direction',
            help='direction to snap into',
            type=VerticalDirection.from_string,
            choices=list(VerticalDirection),
            required=True
        )


class SnapSpectrogramSelectionToNearKeyframeCommand(BaseCommand):
    name = 'audio/snap-sel-to-near-keyframe'
    help_text = 'Snaps the spectrogram selection to the nearest keyframe.'

    @property
    def is_enabled(self) -> bool:
        return (
            self.api.media.audio.has_selection
            and bool(self.api.media.video.keyframes)
        )

    @property
    def menu_name(self) -> str:
        return (
            '&Snap '
            f'{_fmt_shift_target(self.args.target)} to keyframe '
            f'{self.args.direction.name.lower()}'
        )

    async def run(self) -> None:
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

        if self.args.direction == VerticalDirection.Above:
            possible_pts.reverse()
            func = operator.__lt__
            not_found_pts = 0
        elif self.args.direction == VerticalDirection.Below:
            func = operator.__gt__
            not_found_pts = self.api.media.max_pts
        else:
            raise AssertionError

        if self.args.target == ShiftTarget.End:
            current_origin = self.api.media.audio.selection_end
        elif self.args.target in {ShiftTarget.Start, ShiftTarget.Both}:
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
        if self.args.target == ShiftTarget.Start:
            return origin, old_end
        elif self.args.target == ShiftTarget.End:
            return old_start, origin
        elif self.args.target == ShiftTarget.Both:
            return origin, origin
        raise AssertionError

    @staticmethod
    def _decorate_parser(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-t', '--target',
            help='how to snap the selection',
            type=ShiftTarget.from_string,
            choices=list(ShiftTarget),
            required=True
        )
        parser.add_argument(
            '-d', '--direction',
            help='direction to snap into',
            type=VerticalDirection.from_string,
            choices=list(VerticalDirection),
            required=True
        )


class ShiftSpectrogramSelectionCommand(BaseCommand):
    name = 'audio/shift-sel'
    help_text = 'Shifts the spectrogram selection by the specified distance.'

    @property
    def menu_name(self) -> str:
        unit = 'frames' if self.args.frames else 'ms'
        return (
            '&Shift '
            f'{_fmt_shift_target(self.args.target)} '
            f'({self.args.delta:+} {unit})'
        )

    @property
    def is_enabled(self) -> bool:
        return self.api.media.audio.has_selection and bool(
            not self.args.frames or self.api.media.video.timecodes
        )

    async def run(self) -> None:
        old_start = self.api.media.audio.selection_start
        old_end = self.api.media.audio.selection_end

        if self.args.frames:
            idx1 = bisect.bisect_left(
                self.api.media.video.timecodes,
                self.api.media.audio.selection_start
            )
            idx2 = bisect.bisect_left(
                self.api.media.video.timecodes,
                self.api.media.audio.selection_end
            )
            idx1 += self.args.delta
            idx2 += self.args.delta
            idx1 = max(0, min(idx1, len(self.api.media.video.timecodes) - 1))
            idx2 = max(0, min(idx2, len(self.api.media.video.timecodes) - 1))

            new_start = self.api.media.video.timecodes[idx1]
            new_end = self.api.media.video.timecodes[idx2]

            if self.args.target == ShiftTarget.Start:
                self.api.media.audio.select(new_start, old_end)
            elif self.args.target == ShiftTarget.End:
                self.api.media.audio.select(old_start, new_end)
            elif self.args.target == ShiftTarget.Both:
                self.api.media.audio.select(new_start, new_end)
            else:
                raise AssertionError

        else:
            if self.args.target == ShiftTarget.Start:
                self.api.media.audio.select(
                    min(old_end, old_start + self.args.delta), old_end
                )
            elif self.args.target == ShiftTarget.End:
                self.api.media.audio.select(
                    old_start, max(old_start, old_end + self.args.delta)
                )
            elif self.args.target == ShiftTarget.Both:
                self.api.media.audio.select(
                    old_start + self.args.delta, old_end + self.args.delta
                )
            else:
                raise AssertionError

    @staticmethod
    def _decorate_parser(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-t', '--target',
            help='how to shift the selection',
            type=ShiftTarget.from_string,
            choices=list(ShiftTarget),
            required=True
        )
        parser.add_argument(
            '-d', '--delta',
            help='amount to shift the selection by',
            type=int,
            required=True
        )
        parser.add_argument(
            '-f', '--frames',
            help='if true, shift by frames; otherwise by milliseconds',
            action='store_true'
        )


class CommitSpectrogramSelectionCommand(BaseCommand):
    name = 'audio/commit-sel'
    menu_name = '&Commit selection to subtitle'
    help_text = (
        'Commits the spectrogram selection into the current subtitle. '
        'The selected subtitle start and end times is synced to the '
        'current spectrogram selection boundaries.'
    )

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection \
            and self.api.media.audio.has_selection

    async def run(self) -> None:
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
