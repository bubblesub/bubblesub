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
from bubblesub.api.cmd import CoreCommand
from bubblesub.ass.event import Event


class EditUndoCommand(CoreCommand):
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


class EditRedoCommand(CoreCommand):
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


class EditInsertAboveCommand(CoreCommand):
    """Inserts one empty subtitle above the current subtitle selection."""

    name = 'edit/insert-above'
    menu_name = '&Insert subtitle (above)'

    async def run(self) -> None:
        """Carry out the command."""
        if not self.api.subs.selected_indexes:
            idx = 0
            prev_sub = None
            cur_sub = None
        else:
            idx = self.api.subs.selected_indexes[0]
            prev_sub = self.api.subs.lines.get(idx - 1)
            cur_sub = self.api.subs.lines[idx]

        end = (
            cur_sub.start
            if cur_sub else
            self.api.opt.general.subs.default_duration
        )
        start = end - self.api.opt.general.subs.default_duration
        if start < 0:
            start = 0
        if prev_sub and start < prev_sub.end:
            start = prev_sub.end
        if start > end:
            start = end

        with self.api.undo.capture():
            self.api.subs.lines.insert_one(
                idx, start=start, end=end, style='Default'
            )
            self.api.subs.selected_indexes = [idx]


class EditInsertBelowCommand(CoreCommand):
    """Inserts one empty subtitle below the current subtitle selection."""

    name = 'edit/insert-below'
    menu_name = '&Insert subtitle (below)'

    async def run(self) -> None:
        """Carry out the command."""
        if not self.api.subs.selected_indexes:
            idx = 0
            cur_sub = None
            next_sub = self.api.subs.lines.get(0)
        else:
            idx = self.api.subs.selected_indexes[-1]
            cur_sub = self.api.subs.lines[idx]
            idx += 1
            next_sub = self.api.subs.lines.get(idx)

        start = cur_sub.end if cur_sub else 0
        end = start + self.api.opt.general.subs.default_duration
        if next_sub and end > next_sub.start:
            end = next_sub.start
        if end < start:
            end = start

        with self.api.undo.capture():
            self.api.subs.lines.insert_one(
                idx, start=start, end=end, style='Default'
            )
            self.api.subs.selected_indexes = [idx]


class EditMoveUpCommand(CoreCommand):
    """Moves the selected subtitles up."""

    name = 'edit/move-up'
    menu_name = '&Move selected subtitles up'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        if not self.api.subs.selected_indexes:
            return False
        return self.api.subs.selected_indexes[0] > 0

    async def run(self) -> None:
        """Carry out the command."""
        with self.api.undo.capture():
            indexes: T.List[int] = []

            for start_idx, count in bubblesub.util.make_ranges(
                    self.api.subs.selected_indexes
            ):
                self.api.subs.lines.insert(
                    start_idx - 1,
                    [
                        copy(self.api.subs.lines[idx])
                        for idx in range(start_idx, start_idx + count)
                    ]
                )
                self.api.subs.lines.remove(start_idx + count, count)
                indexes += [start_idx + i - 1 for i in range(count)]

            self.api.subs.selected_indexes = indexes


class EditMoveDownCommand(CoreCommand):
    """Moves the selected subtitles down."""

    name = 'edit/move-down'
    menu_name = '&Move selected subtitles down'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        if not self.api.subs.selected_indexes:
            return False
        return (
            self.api.subs.selected_indexes[-1]
            < len(self.api.subs.lines) - 1
        )

    async def run(self) -> None:
        """Carry out the command."""
        with self.api.undo.capture():
            indexes: T.List[int] = []

            for start_idx, count in bubblesub.util.make_ranges(
                    self.api.subs.selected_indexes,
                    reverse=True
            ):
                self.api.subs.lines.insert(
                    start_idx + count + 1,
                    [
                        copy(self.api.subs.lines[idx])
                        for idx in range(start_idx, start_idx + count)
                    ]
                )
                self.api.subs.lines.remove(start_idx, count)
                indexes += [start_idx + i + 1 for i in range(count)]

            self.api.subs.selected_indexes = indexes


class EditMoveToCommand(CoreCommand):
    """
    Moves the selected subtitles to the specified position.

    Asks for the position interactively.
    """

    name = 'edit/move-to'
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
        async def run_dialog(
                api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow
        ) -> T.Optional[int]:
            dialog = QtWidgets.QInputDialog(main_window)
            dialog.setLabelText('Line number to move selected subtitles to:')
            dialog.setIntMinimum(1)
            dialog.setIntMaximum(len(api.subs.lines))
            if api.subs.has_selection:
                dialog.setIntValue(api.subs.selected_indexes[0] + 1)
            dialog.setInputMode(QtWidgets.QInputDialog.IntInput)
            if dialog.exec_():
                return T.cast(int, dialog.intValue()) - 1
            return None

        base_idx = await self.api.gui.exec(run_dialog)
        if base_idx is None:
            return

        with self.api.undo.capture():
            sub_copies: T.List[Event] = []

            for start_idx, count in bubblesub.util.make_ranges(
                    self.api.subs.selected_indexes,
                    reverse=True
            ):
                sub_copies += list(reversed([
                    copy(self.api.subs.lines[idx])
                    for idx in range(start_idx, start_idx + count)
                ]))
                self.api.subs.lines.remove(start_idx, count)

            sub_copies.reverse()
            self.api.subs.lines.insert(base_idx, sub_copies)


class EditDuplicateCommand(CoreCommand):
    """
    Duplicates the selected subtitles.

    The newly created subtitles are interleaved with the current selection.
    """

    name = 'edit/duplicate'
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
                self.api.subs.lines.insert(
                    idx + 1, [copy(self.api.subs.lines[idx])]
                )
                new_selection.append(
                    idx
                    + len(self.api.subs.selected_indexes)
                    - len(new_selection)
                )

            self.api.subs.selected_indexes = new_selection
        self.api.gui.end_update()


class EditDeleteCommand(CoreCommand):
    """Deletes the selected subtitles."""

    name = 'edit/delete'
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
                self.api.subs.lines.remove(start_idx, count)

            self.api.subs.selected_indexes = []


class EditSwapTextAndNotesCommand(CoreCommand):
    """Swaps subtitle text with their notes in the selected subtitles."""

    name = 'edit/swap-text-and-notes'
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
            for sub in self.api.subs.selected_lines:
                sub.begin_update()
                sub.text, sub.note = sub.note, sub.text
                sub.end_update()


class EditSplitSubAtVideoCommand(CoreCommand):
    """Splits the selected subtitle into two at the current video frame."""

    name = 'edit/split-sub-at-video'
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
        sub = self.api.subs.lines[idx]
        split_pos = self.api.media.current_pts
        if split_pos < sub.start or split_pos > sub.end:
            return
        self.api.gui.begin_update()
        with self.api.undo.capture():
            self.api.subs.lines.insert(idx + 1, [copy(sub)])
            self.api.subs.lines[idx].end = split_pos
            self.api.subs.lines[idx + 1].start = split_pos
            self.api.subs.selected_indexes = [idx, idx + 1]
        self.api.gui.end_update()


class EditJoinSubsKeepFirstCommand(CoreCommand):
    """
    Joins the selected subtitles together.

    Keeps only the first subtitle's properties.
    """

    name = 'edit/join-subs/keep-first'
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
                < len(self.api.subs.lines)
            )
        return False

    async def run(self) -> None:
        """Carry out the command."""
        idx = self.api.subs.selected_indexes[0]
        with self.api.undo.capture():
            if len(self.api.subs.selected_indexes) == 1:
                self.api.subs.selected_indexes = [idx, idx + 1]
            last_idx = self.api.subs.selected_indexes[-1]
            self.api.subs.lines[idx].end = self.api.subs.lines[last_idx].end
            for i in reversed(self.api.subs.selected_indexes[1:]):
                self.api.subs.lines.remove(i, 1)
            self.api.subs.selected_indexes = [idx]


class EditJoinSubsConcatenateCommand(CoreCommand):
    """
    Joins the selected subtitles together.

    Keeps the first subtitle's properties and concatenates the text and notes
    of the consecutive subtitles.
    """

    name = 'edit/join-subs/concatenate'
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
                < len(self.api.subs.lines)
            )
        return False

    async def run(self) -> None:
        """Carry out the command."""
        with self.api.undo.capture():
            idx = self.api.subs.selected_indexes[0]
            if len(self.api.subs.selected_indexes) == 1:
                self.api.subs.selected_indexes = [idx, idx + 1]
            last_idx = self.api.subs.selected_indexes[-1]

            sub = self.api.subs.lines[idx]
            sub.begin_update()
            sub.end = self.api.subs.lines[last_idx].end

            new_text = ''
            new_note = ''
            for i in reversed(self.api.subs.selected_indexes[1:]):
                new_text = self.api.subs.lines[i].text + new_text
                new_note = self.api.subs.lines[i].note + new_note
                self.api.subs.lines.remove(i, 1)

            sub.text += new_text
            sub.note += new_note
            sub.end_update()

            self.api.subs.selected_indexes = [idx]


class EditShiftSubsWithGuiCommand(CoreCommand):
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
        async def _run_dialog(
                _api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow,
                **kwargs: T.Any
        ) -> T.Optional[T.Tuple[int, bool]]:
            return bubblesub.ui.util.time_jump_dialog(main_window, **kwargs)

        ret = await self.api.gui.exec(
            _run_dialog,
            absolute_label='Time to move to:',
            relative_label='Time to add:',
            relative_checked=True
        )

        if ret is not None:
            delta, is_relative = ret

            if not is_relative:
                delta -= self.api.subs.selected_lines[0].start

            with self.api.undo.capture():
                for sub in self.api.subs.selected_lines:
                    sub.begin_update()
                    sub.start += delta
                    sub.end += delta
                    sub.end_update()


class EditSnapSubsStartToVideoCommand(CoreCommand):
    """Snaps selected subtitles' start to the current video frame."""

    name = 'edit/snap-subs-start-to-video'
    menu_name = '&Snap subtitles start to video'

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
            for sub in self.api.subs.selected_lines:
                sub.start = self.api.media.current_pts


class EditSnapSubsEndToVideoCommand(CoreCommand):
    """Snaps selected subtitles' end to the current video frame."""

    name = 'edit/snap-subs-end-to-video'
    menu_name = '&Snap subtitles end to video'

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
            for sub in self.api.subs.selected_lines:
                sub.end = self.api.media.current_pts


class EditSnapSubsToVideoCommand(CoreCommand):
    """
    Realigns the selected subtitles to the current video frame.

    The subtitles start time is placed at the current video frame
    and the subtitles duration is set to the default subtitle duration.
    """

    name = 'edit/snap-subs-to-video'
    menu_name = '&Snap subtitles to video'

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
            for sub in self.api.subs.selected_lines:
                sub.start = self.api.media.current_pts
                sub.end = (
                    self.api.media.current_pts
                    + self.api.opt.general.subs.default_duration
                )


class EditSnapSubsStartToPreviousSubtitleCommand(CoreCommand):
    """Snaps the selected subtitles start times to the subtitle above."""

    name = 'edit/snap-subs-start-to-prev-sub'
    menu_name = '&Snap subtitles start to previous subtitle'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self._prev_sub is not None

    @property
    def _prev_sub(self) -> T.Optional[Event]:
        if not self.api.subs.has_selection:
            return None
        return self.api.subs.selected_lines[0].prev

    async def run(self) -> None:
        """Carry out the command."""
        assert self._prev_sub is not None
        with self.api.undo.capture():
            for sub in self.api.subs.selected_lines:
                sub.start = self._prev_sub.end


class EditSnapSubsEndToNextSubtitleCommand(CoreCommand):
    """Snaps the selected subtitles end times to the subtitle below."""

    name = 'edit/snap-subs-end-to-next-sub'
    menu_name = '&Snap subtitles end to next subtitle'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self._next_sub is not None

    @property
    def _next_sub(self) -> T.Optional[Event]:
        if not self.api.subs.has_selection:
            return None
        return self.api.subs.selected_lines[-1].next

    async def run(self) -> None:
        """Carry out the command."""
        assert self._next_sub is not None
        with self.api.undo.capture():
            for sub in self.api.subs.selected_lines:
                sub.end = self._next_sub.start


class EditShiftSubsStartCommand(CoreCommand):
    """Shifts selected subtitles start times by the specified distance."""

    name = 'edit/shift-subs-start'

    def __init__(self, api: bubblesub.api.Api, delta: int) -> None:
        """
        Initialize self.

        :param api: core API
        :param delta: milliseconds to shift the subtitles by
        """
        super().__init__(api)
        self._delta = delta

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return '&Shift subtitles start ({:+})'.format(self._delta)

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
            for sub in self.api.subs.selected_lines:
                sub.start = max(0, sub.start + self._delta)


class EditShiftSubsEndCommand(CoreCommand):
    """Shifts selected subtitles end times by the specified distance."""

    name = 'edit/shift-subs-end'

    def __init__(self, api: bubblesub.api.Api, delta: int) -> None:
        """
        Initialize self.

        :param api: core API
        :param delta: milliseconds to shift the subtitles by
        """
        super().__init__(api)
        self._delta = delta

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return '&Shift subtitles end ({:+})'.format(self._delta)

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
            for sub in self.api.subs.selected_lines:
                sub.end = max(0, sub.end + self._delta)


class EditShiftSubsCommand(CoreCommand):
    """Shifts selected subtitles by the specified distance."""

    name = 'edit/shift-subs'

    def __init__(self, api: bubblesub.api.Api, delta: int) -> None:
        """
        Initialize self.

        :param api: core API
        :param delta: milliseconds to shift the subtitles by
        """
        super().__init__(api)
        self._delta = delta

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return '&Shift subtitles end ({:+})'.format(self._delta)

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
            for sub in self.api.subs.selected_lines:
                sub.start = max(0, sub.start + self._delta)
                sub.end = max(0, sub.end + self._delta)
