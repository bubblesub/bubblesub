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
from bubblesub.api.cmd import CommandCanceled
from bubblesub.api.cmd import CommandUnavailable
from bubblesub.ass.event import Event
from bubblesub.cmd.common import EventSelection
from bubblesub.cmd.common import AbsolutePts
from bubblesub.cmd.common import RelativePts
from bubblesub.util import make_ranges


class UndoCommand(BaseCommand):
    names = ['undo']
    help_text = 'Undoes last edit operation.'

    @property
    def is_enabled(self) -> bool:
        return self.api.undo.has_undo

    async def run(self) -> None:
        self.api.undo.undo()


class RedoCommand(BaseCommand):
    names = ['redo']
    help_text = 'Redoes last edit operation.'

    @property
    def is_enabled(self) -> bool:
        return self.api.undo.has_redo

    async def run(self) -> None:
        self.api.undo.redo()


class SubtitleInsertCommand(BaseCommand):
    names = ['sub-insert']
    help_text = 'Inserts one empty subtitle.'

    @property
    def is_enabled(self) -> bool:
        return self.args.origin.makes_sense

    async def run(self) -> None:
        indexes = await self.args.origin.get_indexes()
        if self.args.dir == 'before':
            idx, start, end = self._insert_before(indexes)
        elif self.args.dir == 'after':
            idx, start, end = self._insert_after(indexes)
        else:
            raise AssertionError

        if not self.args.no_align:
            start = self.api.media.video.align_pts_to_near_frame(start)
            end = self.api.media.video.align_pts_to_near_frame(end)

        with self.api.undo.capture():
            self.api.subs.events.insert_one(
                idx, start=start, end=end, style='Default'
            )
            self.api.subs.selected_indexes = [idx]

    def _insert_before(self, indexes: T.List[int]) -> T.Tuple[int, int, int]:
        if indexes:
            idx = indexes[0]
            cur_sub = self.api.subs.events[idx]
            prev_sub = cur_sub.prev
        else:
            idx = 0
            cur_sub = self.api.subs.events.get(0)
            prev_sub = None

        end = cur_sub.start if cur_sub else 0
        start = end - self.api.opt.general.subs.default_duration
        if prev_sub and start < prev_sub.end:
            start = min(prev_sub.end, end)
        return idx, start, end

    def _insert_after(self, indexes: T.List[int]) -> T.Tuple[int, int, int]:
        if indexes:
            idx = indexes[-1]
            cur_sub = self.api.subs.events[idx]
            next_sub = cur_sub.next
            idx += 1
        else:
            idx = 0
            cur_sub = None
            next_sub = self.api.subs.events.get(0)

        start = cur_sub.end if cur_sub else 0
        end = start + self.api.opt.general.subs.default_duration
        if next_sub and end > next_sub.start:
            end = max(next_sub.start, start)
        return idx, start, end

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-o', '--origin',
            help='where to insert the subtitle',
            type=lambda value: EventSelection(api, value),
            default='selected',
        )

        parser.add_argument(
            '--no-align',
            help='don\'t realign subtitle to video frames',
            action='store_true'
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--before',
            dest='dir',
            action='store_const',
            const='before',
            help='insert before origin'
        )
        group.add_argument(
            '--after',
            dest='dir',
            action='store_const',
            const='after',
            help='insert after origin'
        )


class SubtitlesMoveCommand(BaseCommand):
    names = ['sub-move']
    help_text = 'Moves given subtitles around.'

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        with self.api.undo.capture():
            indexes = await self.args.target.get_indexes()

            if self.args.method == 'above':
                sub_copies = list(self._move_above(indexes))
            elif self.args.method == 'below':
                sub_copies = list(self._move_below(indexes))
            elif self.args.method == 'gui':
                base_idx = await self.api.gui.exec(self._show_dialog, indexes)
                sub_copies = list(self._move_to(indexes, base_idx))
            else:
                raise AssertionError

            self.api.subs.selected_indexes = [sub.index for sub in sub_copies]

    def _move_above(self, indexes: T.List[int]) -> T.Iterable[Event]:
        if indexes[0] == 0:
            raise CommandUnavailable
        for idx, count in make_ranges(indexes):
            chunk = list(map(copy, self.api.subs.events[idx:idx + count]))
            self.api.subs.events.insert(idx - 1, chunk)
            self.api.subs.events.remove(idx + count, count)
            yield from chunk

    def _move_below(self, indexes: T.List[int]) -> T.Iterable[Event]:
        if indexes[-1] + 1 == len(self.api.subs.events):
            raise CommandUnavailable
        for idx, count in make_ranges(indexes, reverse=True):
            chunk = list(map(copy, self.api.subs.events[idx:idx + count]))
            self.api.subs.events.insert(idx + count + 1, chunk)
            self.api.subs.events.remove(idx, count)
            yield from chunk

    def _move_to(
            self,
            indexes: T.List[int],
            base_idx: int
    ) -> T.Iterable[Event]:
        sub_copies: T.List[Event] = []

        for idx, count in make_ranges(indexes, reverse=True):
            chunk = list(map(
                copy, self.api.subs.events[idx:idx + count]
            ))
            chunk.reverse()
            sub_copies += chunk
            self.api.subs.events.remove(idx, count)

        sub_copies.reverse()
        self.api.subs.events.insert(base_idx, sub_copies)
        return sub_copies

    async def _show_dialog(
            self,
            main_window: QtWidgets.QMainWindow,
            indexes: T.List[int]
    ) -> int:
        dialog = QtWidgets.QInputDialog(main_window)
        dialog.setLabelText('Line number to move subtitles to:')
        dialog.setIntMinimum(1)
        dialog.setIntMaximum(len(self.api.subs.events))
        if indexes:
            dialog.setIntValue(indexes[0] + 1)
        dialog.setInputMode(QtWidgets.QInputDialog.IntInput)
        if not dialog.exec_():
            raise CommandCanceled
        return T.cast(int, dialog.intValue()) - 1

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to move',
            type=lambda value: EventSelection(api, value),
            default='selected'
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--above',
            dest='method',
            action='store_const',
            const='above',
            help='move subtitles up'
        )
        group.add_argument(
            '--below',
            dest='method',
            action='store_const',
            const='below',
            help='move subtitles down'
        )
        group.add_argument(
            '--gui',
            dest='method',
            action='store_const',
            const='gui',
            help='prompt user for placement position with a GUI dialog'
        )


class SubtitlesCloneCommand(BaseCommand):
    names = ['sub-clone', 'sub-duplicate']
    help_text = (
        'Duplicates given subtitles. Duplicated subtitles '
        'are interleaved with the source subtitles.'
    )

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
            default='selected'
        )


class SubtitlesDeleteCommand(BaseCommand):
    names = ['sub-delete']
    help_text = 'Deletes given subtitles.'

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
            for start_idx, count in make_ranges(indexes, reverse=True):
                self.api.subs.events.remove(start_idx, count)

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to delete',
            type=lambda value: EventSelection(api, value),
            default='selected'
        )


class SubtitlesSetCommand(BaseCommand):
    names = ['sub-set']
    help_text = 'Updates given subtitles parameters.'

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        with self.api.undo.capture():
            for sub in await self.args.target.get_subtitles():
                params = {
                    'text': sub.text,
                    'note': sub.note,
                    'actor': sub.actor,
                    'style': sub.style,
                }

                sub.begin_update()

                if self.args.text:
                    sub.text = self.args.text.format(**params)

                if self.args.note:
                    sub.note = self.args.note.format(**params)

                if self.args.actor:
                    sub.actor = self.args.actor.format(**params)

                if self.args.style:
                    sub.style = self.args.style.format(**params)

                if self.args.comment:
                    sub.is_comment = True

                if self.args.no_comment:
                    sub.is_comment = False

                sub.end_update()

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to change',
            type=lambda value: EventSelection(api, value),
            default='selected'
        )

        parser.add_argument('--text', help='new subtitles text')
        parser.add_argument('--note', help='new subtitles note')
        parser.add_argument('--actor', help='new subtitles actor')
        parser.add_argument('--style', help='new subtitles style')
        parser.add_argument(
            '--comment',
            action='store_true',
            help='mark subtitles as a comment'
        )
        parser.add_argument(
            '--no-comment',
            action='store_true',
            help='mark subtitles as a non-comment'
        )


class SubtitlesSplitCommand(BaseCommand):
    names = ['sub-split']
    help_text = 'Splits given subtitles at specified time.'

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        split_pos = await self.args.position.get(
            align_to_near_frame=not self.args.no_align
        )

        with self.api.undo.capture(), self.api.gui.throttle_updates():
            for sub in reversed(await self.args.target.get_subtitles()):
                if split_pos < sub.start or split_pos > sub.end:
                    continue
                idx = sub.index
                self.api.subs.events.insert(idx + 1, [copy(sub)])
                self.api.subs.events[idx].end = split_pos
                self.api.subs.events[idx + 1].start = split_pos
                self.api.subs.selected_indexes = [idx, idx + 1]

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to split',
            type=lambda value: EventSelection(api, value),
            default='selected'
        )

        parser.add_argument(
            '--no-align',
            help='don\'t align split position to video frames',
            action='store_true'
        )

        parser.add_argument(
            '-p', '--position',
            help='position to split the subtitles at',
            type=lambda value: AbsolutePts(api, value),
        )


class JoinSubtitlesKeepFirstCommand(BaseCommand):
    names = ['edit/join-subs-keep-first']
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


class SubtitlesShiftCommand(BaseCommand):
    names = ['sub-shift']
    help_text = 'Shifts given subtitles.'

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        events = await self.args.target.get_subtitles()
        delta = await self._get_delta(events, main_window)

        with self.api.undo.capture():
            for event in events:
                start = event.start
                end = event.end

                if self.args.method in {'start', 'both'}:
                    start = await delta.apply(
                        start, align_to_near_frame=not self.args.no_align
                    )

                if self.args.method in {'end', 'both'}:
                    end = await delta.apply(
                        end, align_to_near_frame=not self.args.no_align
                    )

                event.begin_update()
                event.start = start
                event.end = end
                event.end_update()

    async def _get_delta(
            self,
            events: T.List[Event],
            main_window: QtWidgets.QMainWindow
    ) -> RelativePts:
        if self.args.delta:
            return self.args.delta
        if self.args.gui:
            ret = bubblesub.ui.util.time_jump_dialog(
                main_window,
                absolute_label='Time to move to:',
                relative_label='Time to add:',
                relative_checked=True
            )
            if ret is None:
                raise CommandCanceled

            delta, is_relative = ret
            if not is_relative and events:
                delta -= events[0].start

            return RelativePts(self.api, str(delta) + 'ms')
        raise AssertionError

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to shift',
            type=lambda value: EventSelection(api, value),
            default='selected'
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '-g', '--gui',
            action='store_true',
            help='prompt user for shift amount with a GUI dialog'
        )
        group.add_argument(
            '-d', '--delta',
            help='amount to shift the subtitles',
            type=lambda value: RelativePts(api, value),
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
            help='shift subtitles start',
            default='both'
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
            SubtitleInsertCommand,
            SubtitlesMoveCommand,
            SubtitlesCloneCommand,
            SubtitlesDeleteCommand,
            SubtitlesSetCommand,
            SubtitlesSplitCommand,
            JoinSubtitlesKeepFirstCommand,
            JoinSubtitlesConcatenateCommand,
            SubtitlesShiftCommand,
    ]:
        cmd_api.register_core_command(T.cast(T.Type[BaseCommand], cls))
