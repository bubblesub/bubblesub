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

"""Commands related to subtitle manipulation."""

import typing as T
from copy import copy

from PyQt5 import QtWidgets

import bubblesub.ui.util
from bubblesub.api.cmd import BaseCommand
from bubblesub.ass.event import Event
from bubblesub.util import ShiftTarget, VerticalDirection


def _fmt_shift_target(shift_target: ShiftTarget) -> str:
    return {
        ShiftTarget.Start: 'subtitles start',
        ShiftTarget.End: 'subtitles end',
        ShiftTarget.Both: 'subtitles'
    }[shift_target]


class UndoCommand(BaseCommand):
    """Undoes last edit operation."""

    name = 'edit/undo'
    menu_name = '&Undo'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.undo.has_undo

    async def run(self) -> None:
        """Carry out the command."""
        self.api.undo.undo()


class RedoCommand(BaseCommand):
    """Redoes last edit operation."""

    name = 'edit/redo'
    menu_name = '&Redo'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.undo.has_redo

    async def run(self) -> None:
        """Carry out the command."""
        self.api.undo.redo()


class InsertSubtitleCommand(BaseCommand):
    """Inserts one empty subtitle near the current subtitle selection."""

    name = 'edit/insert-sub'

    def __init__(self, api: bubblesub.api.Api, direction: str) -> None:
        """
        Initialize self.

        :param api: core API
        :param direction: whether to insert the subtitle below or above
        """
        super().__init__(api)
        self._direction = VerticalDirection[direction.title()]

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return f'&Insert subtitle ({self._direction.name.lower()})'

    async def run(self) -> None:
        """Carry out the command."""
        if self._direction == VerticalDirection.Above:
            if not self.api.subs.selected_indexes:
                idx = 0
                prev_sub = None
                cur_sub = None
            else:
                idx = self.api.subs.selected_indexes[0]
                prev_sub = self.api.subs.events.get(idx - 1)
                cur_sub = self.api.subs.events[idx]

            if cur_sub:
                end = cur_sub.start
                start = self.api.media.video.align_pts_to_prev_frame(
                    max(0, end - self.api.opt.general.subs.default_duration)
                )
            else:
                start = 0
                end = self.api.media.video.align_pts_to_next_frame(
                    self.api.opt.general.subs.default_duration
                )

            if prev_sub and start < prev_sub.end:
                start = prev_sub.end
            if start > end:
                start = end

        elif self._direction == VerticalDirection.Below:
            if not self.api.subs.selected_indexes:
                idx = 0
                cur_sub = None
                next_sub = self.api.subs.events.get(0)
            else:
                idx = self.api.subs.selected_indexes[-1]
                cur_sub = self.api.subs.events[idx]
                idx += 1
                next_sub = self.api.subs.events.get(idx)

            start = cur_sub.end if cur_sub else 0
            end = start + self.api.opt.general.subs.default_duration
            end = self.api.media.video.align_pts_to_next_frame(end)
            if next_sub and end > next_sub.start:
                end = next_sub.start
            if end < start:
                end = start

        else:
            raise AssertionError

        with self.api.undo.capture():
            self.api.subs.events.insert_one(
                idx, start=start, end=end, style='Default'
            )
            self.api.subs.selected_indexes = [idx]


class MoveSubtitlesCommand(BaseCommand):
    """Moves the selected subtitles above or below."""

    name = 'edit/move-subs'

    def __init__(self, api: bubblesub.api.Api, direction: str) -> None:
        """
        Initialize self.

        :param api: core API
        :param direction: whether to move the subtitles below or above
        """
        super().__init__(api)
        self._direction = VerticalDirection[direction.title()]

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return f'&Move selected subtitles {self._direction.name.lower()}'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        if not self.api.subs.selected_indexes:
            return False
        if self._direction == VerticalDirection.Above:
            return self.api.subs.selected_indexes[0] > 0
        elif self._direction == VerticalDirection.Below:
            return (
                self.api.subs.selected_indexes[-1]
                < len(self.api.subs.events) - 1
            )
        else:
            raise AssertionError

    async def run(self) -> None:
        """Carry out the command."""
        with self.api.undo.capture():
            indexes: T.List[int] = []

            if self._direction == VerticalDirection.Above:
                for start_idx, count in bubblesub.util.make_ranges(
                        self.api.subs.selected_indexes
                ):
                    self.api.subs.events.insert(
                        start_idx - 1,
                        [
                            copy(self.api.subs.events[idx])
                            for idx in range(start_idx, start_idx + count)
                        ]
                    )
                    self.api.subs.events.remove(start_idx + count, count)
                    indexes += [start_idx + i - 1 for i in range(count)]

            elif self._direction == VerticalDirection.Below:
                for start_idx, count in bubblesub.util.make_ranges(
                        self.api.subs.selected_indexes,
                        reverse=True
                ):
                    self.api.subs.events.insert(
                        start_idx + count + 1,
                        [
                            copy(self.api.subs.events[idx])
                            for idx in range(start_idx, start_idx + count)
                        ]
                    )
                    self.api.subs.events.remove(start_idx, count)
                    indexes += [start_idx + i + 1 for i in range(count)]

            else:
                raise AssertionError

            self.api.subs.selected_indexes = indexes


class MoveSubtitlesToCommand(BaseCommand):
    """
    Moves the selected subtitles to the specified position.

    Asks for the position interactively.
    """

    name = 'edit/move-subs-to'
    menu_name = '&Move selected subtitles to...'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return len(self.api.subs.selected_indexes) > 0

    async def run(self) -> None:
        """Carry out the command."""
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        base_idx = self._show_dialog(main_window)
        if base_idx is None:
            return

        with self.api.undo.capture():
            sub_copies: T.List[Event] = []

            for start_idx, count in bubblesub.util.make_ranges(
                    self.api.subs.selected_indexes,
                    reverse=True
            ):
                sub_copies += list(reversed([
                    copy(self.api.subs.events[idx])
                    for idx in range(start_idx, start_idx + count)
                ]))
                self.api.subs.events.remove(start_idx, count)

            sub_copies.reverse()
            self.api.subs.events.insert(base_idx, sub_copies)

    def _show_dialog(
            self,
            main_window: QtWidgets.QMainWindow
    ) -> T.Optional[int]:
        dialog = QtWidgets.QInputDialog(main_window)
        dialog.setLabelText('Line number to move selected subtitles to:')
        dialog.setIntMinimum(1)
        dialog.setIntMaximum(len(self.api.subs.events))
        if self.api.subs.has_selection:
            dialog.setIntValue(self.api.subs.selected_indexes[0] + 1)
        dialog.setInputMode(QtWidgets.QInputDialog.IntInput)
        if dialog.exec_():
            return T.cast(int, dialog.intValue()) - 1
        return None


class DuplicateSubtitlesCommand(BaseCommand):
    """
    Duplicates the selected subtitles.

    The newly created subtitles are interleaved with the current selection.
    """

    name = 'edit/duplicate-subs'
    menu_name = '&Duplicate selected subtitles'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        self.api.gui.begin_update()
        with self.api.undo.capture():
            new_selection: T.List[int] = []

            for idx in reversed(self.api.subs.selected_indexes):
                self.api.subs.events.insert(
                    idx + 1, [copy(self.api.subs.events[idx])]
                )
                new_selection.append(
                    idx
                    + len(self.api.subs.selected_indexes)
                    - len(new_selection)
                )

            self.api.subs.selected_indexes = new_selection
        self.api.gui.end_update()


class DeleteSubtitlesCommand(BaseCommand):
    """Deletes the selected subtitles."""

    name = 'edit/delete-subs'
    menu_name = '&Delete selected subtitles'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        with self.api.undo.capture():
            for start_idx, count in bubblesub.util.make_ranges(
                    self.api.subs.selected_indexes,
                    reverse=True
            ):
                self.api.subs.events.remove(start_idx, count)

            self.api.subs.selected_indexes = []


class SwapSubtitlesTextAndNotesCommand(BaseCommand):
    """Swaps subtitle text with their notes in the selected subtitles."""

    name = 'edit/swap-subs-text-and-notes'
    menu_name = '&Swap notes with subtitle text'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        with self.api.undo.capture():
            for sub in self.api.subs.selected_events:
                sub.begin_update()
                sub.text, sub.note = sub.note, sub.text
                sub.end_update()


class SplitSubtitleAtCurrentVideoFrameCommand(BaseCommand):
    """Splits the selected subtitle into two at the current video frame."""

    name = 'edit/split-sub-at-current-video-frame'
    menu_name = '&Split selected subtitle at video frame'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return len(self.api.subs.selected_indexes) == 1

    async def run(self) -> None:
        """Carry out the command."""
        idx = self.api.subs.selected_indexes[0]
        sub = self.api.subs.events[idx]
        split_pos = self.api.media.current_pts
        if split_pos < sub.start or split_pos > sub.end:
            return
        self.api.gui.begin_update()
        with self.api.undo.capture():
            self.api.subs.events.insert(idx + 1, [copy(sub)])
            self.api.subs.events[idx].end = split_pos
            self.api.subs.events[idx + 1].start = split_pos
            self.api.subs.selected_indexes = [idx, idx + 1]
        self.api.gui.end_update()


class JoinSubtitlesKeepFirstCommand(BaseCommand):
    """
    Joins the selected subtitles together.

    Keeps only the first subtitle's properties.
    """

    name = 'edit/join-subs-keep-first'
    menu_name = '&Join subtitles (keep first)'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        if len(self.api.subs.selected_indexes) > 1:
            return True
        if len(self.api.subs.selected_indexes) == 1:
            return (
                self.api.subs.selected_indexes[0] + 1
                < len(self.api.subs.events)
            )
        return False

    async def run(self) -> None:
        """Carry out the command."""
        idx = self.api.subs.selected_indexes[0]
        with self.api.undo.capture():
            if len(self.api.subs.selected_indexes) == 1:
                self.api.subs.selected_indexes = [idx, idx + 1]
            last_idx = self.api.subs.selected_indexes[-1]
            self.api.subs.events[idx].end = self.api.subs.events[last_idx].end
            for i in reversed(self.api.subs.selected_indexes[1:]):
                self.api.subs.events.remove(i, 1)
            self.api.subs.selected_indexes = [idx]


class JoinSubtitlesConcatenateCommand(BaseCommand):
    """
    Joins the selected subtitles together.

    Keeps the first subtitle's properties and concatenates the text and notes
    of the consecutive subtitles.
    """

    name = 'edit/join-subs-concatenate'
    menu_name = '&Join subtitles (concatenate)'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        if len(self.api.subs.selected_indexes) > 1:
            return True
        if len(self.api.subs.selected_indexes) == 1:
            return (
                self.api.subs.selected_indexes[0] + 1
                < len(self.api.subs.events)
            )
        return False

    async def run(self) -> None:
        """Carry out the command."""
        with self.api.undo.capture():
            idx = self.api.subs.selected_indexes[0]
            if len(self.api.subs.selected_indexes) == 1:
                self.api.subs.selected_indexes = [idx, idx + 1]
            last_idx = self.api.subs.selected_indexes[-1]

            sub = self.api.subs.events[idx]
            sub.begin_update()
            sub.end = self.api.subs.events[last_idx].end

            new_text = ''
            new_note = ''
            for i in reversed(self.api.subs.selected_indexes[1:]):
                new_text = self.api.subs.events[i].text + new_text
                new_note = self.api.subs.events[i].note + new_note
                self.api.subs.events.remove(i, 1)

            sub.text += new_text
            sub.note += new_note
            sub.end_update()

            self.api.subs.selected_indexes = [idx]


class ShiftSubtitlesWithGuiCommand(BaseCommand):
    """
    Shifts the subtitle boundaries by the specified distance.

    Prompts user for details with a GUI dialog.
    """

    name = 'edit/shift-subs-with-gui'
    menu_name = '&Shift times...'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        ret = bubblesub.ui.util.time_jump_dialog(
            main_window,
            absolute_label='Time to move to:',
            relative_label='Time to add:',
            relative_checked=True
        )

        if ret is None:
            return

        delta, is_relative = ret

        if not is_relative:
            delta -= self.api.subs.selected_events[0].start

        with self.api.undo.capture():
            for sub in self.api.subs.selected_events:
                sub.begin_update()
                sub.start += delta
                sub.end += delta
                sub.end_update()


class SnapSubtitlesToCurrentVideoFrameCommand(BaseCommand):
    """Snaps selected subtitles to the current video frame."""

    name = 'edit/snap-subs-to-current-video-frame'

    def __init__(self, api: bubblesub.api.Api, shift_target: str) -> None:
        """
        Initialize self.

        :param api: core API
        :param shift_target: how to snap the subtitles
        """
        super().__init__(api)
        self._shift_target = ShiftTarget[shift_target.title()]

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return (
            f'&Snap {_fmt_shift_target(self._shift_target)} '
            'to current video frame'
        )

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        with self.api.undo.capture():
            for sub in self.api.subs.selected_events:
                if self._shift_target == ShiftTarget.Start:
                    sub.start = self.api.media.current_pts
                elif self._shift_target == ShiftTarget.End:
                    sub.end = self.api.media.current_pts
                elif self._shift_target == ShiftTarget.Both:
                    sub.start = self.api.media.current_pts
                    sub.end = self.api.media.current_pts
                else:
                    raise AssertionError


class PlaceSubtitlesAtCurrentVideoFrameCommand(BaseCommand):
    """
    Realigns the selected subtitles to the current video frame.

    The subtitles start time is placed at the current video frame
    and the subtitles duration is set to the default subtitle duration.
    """

    name = 'edit/place-subs-at-current-video-frame'
    menu_name = '&Place subtitles at current video frame'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        with self.api.undo.capture():
            for sub in self.api.subs.selected_events:
                sub.start = self.api.media.current_pts
                sub.end = self.api.media.video.align_pts_to_next_frame(
                    sub.start
                    + self.api.opt.general.subs.default_duration
                )


class SnapSubtitlesToNearSubtitleCommand(BaseCommand):
    """Snaps the selected subtitles times to the nearest subtitle."""

    name = 'edit/snap-subs-to-near-sub'

    def __init__(
            self,
            api: bubblesub.api.Api,
            shift_target: str,
            snap_direction: str
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param shift_target: how to snap the subtitles
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
            f'{self._direction.name.lower()} '
        )

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
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
        with self.api.undo.capture():
            for sub in self.api.subs.selected_events:
                if self._shift_target == ShiftTarget.Start:
                    sub.start = self._nearest_sub.end
                elif self._shift_target == ShiftTarget.End:
                    sub.end = self._nearest_sub.start
                elif self._shift_target == ShiftTarget.Both:
                    if self._direction == VerticalDirection.Above:
                        sub.start = self._nearest_sub.end
                        sub.end = self._nearest_sub.end
                    elif self._direction == VerticalDirection.Below:
                        sub.start = self._nearest_sub.start
                        sub.end = self._nearest_sub.start
                    else:
                        raise AssertionError
                else:
                    raise AssertionError


class ShiftSubtitlesCommand(BaseCommand):
    """Shifts selected subtitles times by the specified distance."""

    name = 'edit/shift-subs'

    def __init__(
            self,
            api: bubblesub.api.Api,
            shift_target: str,
            delta: int
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param shift_target: how to shift the subtitles
        :param delta: milliseconds to shift the subtitles by
        """
        super().__init__(api)
        self._shift_target = ShiftTarget[shift_target.title()]
        self._delta = delta

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return (
            '&Shift '
            f'{_fmt_shift_target(self._shift_target)} '
            f'({self._delta:+} ms)'
        )

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        with self.api.undo.capture():
            for sub in self.api.subs.selected_events:
                if self._shift_target == ShiftTarget.Start:
                    sub.start = max(0, sub.start + self._delta)
                elif self._shift_target == ShiftTarget.End:
                    sub.end = max(0, sub.end + self._delta)
                elif self._shift_target == ShiftTarget.Both:
                    sub.start = max(0, sub.start + self._delta)
                    sub.end = max(0, sub.end + self._delta)
                else:
                    raise AssertionError


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    """
    Register commands in this file into the command API.

    :param cmd_api: command API
    """
    for cls in [
            UndoCommand,
            RedoCommand,
            InsertSubtitleCommand,
            MoveSubtitlesCommand,
            MoveSubtitlesToCommand,
            DuplicateSubtitlesCommand,
            DeleteSubtitlesCommand,
            SwapSubtitlesTextAndNotesCommand,
            SplitSubtitleAtCurrentVideoFrameCommand,
            JoinSubtitlesKeepFirstCommand,
            JoinSubtitlesConcatenateCommand,
            ShiftSubtitlesWithGuiCommand,
            SnapSubtitlesToCurrentVideoFrameCommand,
            PlaceSubtitlesAtCurrentVideoFrameCommand,
            SnapSubtitlesToNearSubtitleCommand,
            ShiftSubtitlesCommand,
    ]:
        cmd_api.register_core_command(T.cast(T.Type[BaseCommand], cls))
