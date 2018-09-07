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

import argparse
import typing as T
from copy import copy

from PyQt5 import QtWidgets

import bubblesub.ui.util
from bubblesub.api.cmd import BaseCommand
from bubblesub.ass.event import Event
from bubblesub.cmd.common import EventSelection
from bubblesub.cmd.common import RelativePts
from bubblesub.util import ShiftTarget, VerticalDirection


def _fmt_shift_target(shift_target: ShiftTarget) -> str:
    return {
        ShiftTarget.Start: 'subtitles start',
        ShiftTarget.End: 'subtitles end',
        ShiftTarget.Both: 'subtitles'
    }[shift_target]


class UndoCommand(BaseCommand):
    names = ['undo']
    menu_name = '&Undo'
    help_text = 'Undoes last edit operation.'

    @property
    def is_enabled(self) -> bool:
        return self.api.undo.has_undo

    async def run(self) -> None:
        self.api.undo.undo()


class RedoCommand(BaseCommand):
    names = ['redo']
    menu_name = '&Redo'
    help_text = 'Redoes last edit operation.'

    @property
    def is_enabled(self) -> bool:
        return self.api.undo.has_redo

    async def run(self) -> None:
        self.api.undo.redo()


class InsertSubtitleCommand(BaseCommand):
    names = ['edit/insert-sub']
    help_text = (
        'Inserts one empty subtitle near the current subtitle selection.'
    )

    @property
    def menu_name(self) -> str:
        return f'&Insert subtitle ({self.args.direction.name.lower()})'

    async def run(self) -> None:
        if self.args.direction == VerticalDirection.Above:
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

        elif self.args.direction == VerticalDirection.Below:
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

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-d', '--direction',
            help='how to insert the subtitle',
            type=VerticalDirection.from_string,
            choices=list(VerticalDirection),
            required=True
        )


class MoveSubtitlesCommand(BaseCommand):
    names = ['edit/move-subs']
    help_text = 'Moves the selected subtitles above or below.'

    @property
    def menu_name(self) -> str:
        return f'&Move selected subtitles {self.args.direction.name.lower()}'

    @property
    def is_enabled(self) -> bool:
        if not self.api.subs.selected_indexes:
            return False

        if self.args.direction == VerticalDirection.Above:
            return self.api.subs.selected_indexes[0] > 0

        if self.args.direction == VerticalDirection.Below:
            return (
                self.api.subs.selected_indexes[-1]
                < len(self.api.subs.events) - 1
            )

        raise AssertionError

    async def run(self) -> None:
        with self.api.undo.capture():
            indexes: T.List[int] = []

            if self.args.direction == VerticalDirection.Above:
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

            elif self.args.direction == VerticalDirection.Below:
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

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-d', '--direction',
            help='how to move the subtitles',
            type=VerticalDirection.from_string,
            choices=list(VerticalDirection),
            required=True
        )


class MoveSubtitlesToCommand(BaseCommand):
    names = ['edit/move-subs-to']
    menu_name = '&Move selected subtitles to...'
    help_text = (
        'Moves the selected subtitles to the specified position. '
        'Asks for the position interactively.'
    )

    @property
    def is_enabled(self) -> bool:
        return len(self.api.subs.selected_indexes) > 0

    async def run(self) -> None:
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


class SubtitlesCloneCommand(BaseCommand):
    names = ['sub-clone', 'sub-duplicate']
    help_text = (
        'Duplicates given subtitles. Duplicated subtitles '
        'are interleaved with the source subtitles.'
    )

    @property
    def menu_name(self):
        return f'&Duplicate {self.args.target.description}'

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        with self.api.undo.capture(), self.api.gui.throttle_updates():
            sub_copies: T.List[Event] = []

            for idx in reversed(await self.args.target.get_indexes()):
                sub_copy = copy(self.api.subs.events[idx])
                self.api.subs.events.insert(idx + 1, [sub_copy])
                sub_copies.append(sub_copy)

            self.api.subs.selected_indexes = [sub.index for sub in sub_copies]

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to clone',
            type=lambda value: EventSelection(api, value),
            nargs='?',
            default='selected'
        )


class SubtitlesDeleteCommand(BaseCommand):
    names = ['sub-delete']
    help_text = 'Deletes given subtitles.'

    @property
    def menu_name(self):
        return f'&Delete {self.args.target.description}'

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        with self.api.undo.capture():
            indexes = await self.args.target.get_indexes()
            new_selection = (
                set(self.api.subs.selected_events) -
                set(self.api.subs.events[idx] for idx in indexes)
            )

            self.api.subs.selected_indexes = [
                sub.index for sub in new_selection
            ]
            for start_idx, count in bubblesub.util.make_ranges(
                    indexes,
                    reverse=True
            ):
                self.api.subs.events.remove(start_idx, count)

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            'target',
            help='subtitles to delete',
            type=lambda value: EventSelection(api, value),
            nargs='?',
            default='selected'
        )


class SwapSubtitlesTextAndNotesCommand(BaseCommand):
    names = ['edit/swap-subs-text-and-notes']
    menu_name = '&Swap notes with subtitle text'
    help_text = (
        'Swaps subtitle text with their notes in the selected subtitles.'
    )

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection

    async def run(self) -> None:
        with self.api.undo.capture():
            for sub in self.api.subs.selected_events:
                sub.begin_update()
                sub.text, sub.note = sub.note, sub.text
                sub.end_update()


class SplitSubtitleAtCurrentVideoFrameCommand(BaseCommand):
    names = ['edit/split-sub-at-current-video-frame']
    menu_name = '&Split selected subtitle at video frame'
    help_text = (
        'Splits the selected subtitle into two at the current video frame.'
    )

    @property
    def is_enabled(self) -> bool:
        return len(self.api.subs.selected_indexes) == 1

    async def run(self) -> None:
        idx = self.api.subs.selected_indexes[0]
        sub = self.api.subs.events[idx]
        split_pos = self.api.media.current_pts
        if split_pos < sub.start or split_pos > sub.end:
            return
        with self.api.undo.capture(), self.api.gui.throttle_updates():
            self.api.subs.events.insert(idx + 1, [copy(sub)])
            self.api.subs.events[idx].end = split_pos
            self.api.subs.events[idx + 1].start = split_pos
            self.api.subs.selected_indexes = [idx, idx + 1]


class JoinSubtitlesKeepFirstCommand(BaseCommand):
    names = ['edit/join-subs-keep-first']
    menu_name = '&Join subtitles (keep first)'
    help_text = (
        'Joins the selected subtitles together. '
        'Keeps only the first subtitle\'s properties.'
    )

    @property
    def is_enabled(self) -> bool:
        if len(self.api.subs.selected_indexes) > 1:
            return True
        if len(self.api.subs.selected_indexes) == 1:
            return (
                self.api.subs.selected_indexes[0] + 1
                < len(self.api.subs.events)
            )
        return False

    async def run(self) -> None:
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
    names = ['edit/join-subs-concatenate']
    menu_name = '&Join subtitles (concatenate)'
    help_text = (
        'Joins the selected subtitles together. Keeps the first subtitle\'s '
        'properties and concatenates the text and notes of the consecutive '
        'subtitles.'
    )

    @property
    def is_enabled(self) -> bool:
        if len(self.api.subs.selected_indexes) > 1:
            return True
        if len(self.api.subs.selected_indexes) == 1:
            return (
                self.api.subs.selected_indexes[0] + 1
                < len(self.api.subs.events)
            )
        return False

    async def run(self) -> None:
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
    names = ['edit/shift-subs-with-gui']
    menu_name = '&Shift times...'
    help_text = (
        'Shifts the subtitle boundaries by the specified distance. '
        'Prompts user for details with a GUI dialog.'
    )

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection

    async def run(self) -> None:
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


class SubtitlesShiftCommand(BaseCommand):
    names = ['sub-shift']
    help_text = 'Shifts given subtitles.'

    @property
    def menu_name(self) -> str:
        if self.args.method == 'start':
            target = self.args.target.description + ' start'
        elif self.args.method == 'end':
            target = self.args.target.description + ' end'
        else:
            target = self.args.target.description
        return f'&Shift {target} {self.args.delta.description}'

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        with self.api.undo.capture():
            for event in await self.args.target.get_subtitles():
                start = event.start
                end = event.end

                if self.args.method in {'start', 'both'}:
                    start = await self.args.delta.apply(start)
                    if not self.args.no_align:
                        start = self.api.media.video.align_pts_to_near_frame(
                            start
                        )

                if self.args.method in {'end', 'both'}:
                    end = await self.args.delta.apply(end)
                    if not self.args.no_align:
                        end = self.api.media.video.align_pts_to_near_frame(end)

                event.start = start
                event.end = end

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to shift',
            type=lambda value: EventSelection(api, value),
            nargs='?',
            default='selected'
        )
        parser.add_argument(
            '-d', '--delta',
            help='amount to shift the subtitles',
            type=lambda value: RelativePts(api, value),
            required=True,
        )
        parser.add_argument(
            '--no-align',
            help='don\'t realign subtitles to video frames',
            action='store_true'
        )

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '--start',
            action='store_const',
            dest='method',
            const='start',
            help='shift subtitles start'
        )
        group.add_argument(
            '--end',
            action='store_const',
            dest='method',
            const='end',
            help='shift subtitles end'
        )
        group.add_argument(
            '--both',
            action='store_const',
            dest='method',
            const='both',
            help='shift whole subtitles'
        )


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
            SubtitlesCloneCommand,
            SubtitlesDeleteCommand,
            SwapSubtitlesTextAndNotesCommand,
            SplitSubtitleAtCurrentVideoFrameCommand,
            JoinSubtitlesKeepFirstCommand,
            JoinSubtitlesConcatenateCommand,
            SubtitlesShiftCommand,
            ShiftSubtitlesWithGuiCommand,
    ]:
        cmd_api.register_core_command(T.cast(T.Type[BaseCommand], cls))
