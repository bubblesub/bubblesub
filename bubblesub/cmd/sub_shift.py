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

import argparse
import typing as T

from PyQt5 import QtWidgets

import bubblesub.ui.util
from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.api.cmd import CommandCanceled
from bubblesub.api.cmd import CommandError
from bubblesub.api.cmd import CommandUnavailable
from bubblesub.ass.event import Event
from bubblesub.cmd.common import Pts
from bubblesub.cmd.common import SubtitlesSelection


class SubtitlesShiftCommand(BaseCommand):
    names = ['sub-shift']
    help_text = 'Shifts given subtitles.'

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable('nothing to update')

        delta = await self._get_delta(subs, main_window)

        with self.api.undo.capture():
            for sub in subs:
                start = sub.start
                end = sub.end

                if delta:
                    start = await delta.get(
                        origin=start,
                        align_to_near_frame=not self.args.no_align
                    )
                    end = await delta.get(
                        origin=end,
                        align_to_near_frame=not self.args.no_align
                    )
                else:
                    if self.args.start:
                        start = await self.args.start.get(
                            origin=start,
                            align_to_near_frame=not self.args.no_align
                        )
                    if self.args.end:
                        end = await self.args.end.get(
                            origin=end,
                            align_to_near_frame=not self.args.no_align
                        )

                sub.begin_update()
                sub.start = start
                sub.end = end
                sub.end_update()

    async def _get_delta(
            self,
            subs: T.List[Event],
            main_window: QtWidgets.QMainWindow
    ) -> T.Optional[Pts]:
        if self.args.start or self.args.end:
            if self.args.gui:
                raise CommandError(
                    '--start/--end cannot be combined with --gui'
                )
            return None

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
            if not is_relative and subs:
                delta -= subs[0].start

            return Pts(self.api, '+' + str(delta) + 'ms')

        raise CommandError('expected --gui or --start/--end')

    @staticmethod
    def _decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to shift',
            type=lambda value: SubtitlesSelection(api, value),
            default='selected',
        )
        parser.add_argument(
            '-g', '--gui',
            action='store_true',
            help='prompt user for shift amount with a GUI dialog',
        )
        parser.add_argument(
            '-s', '--start',
            help='amount to shift the start of the subtitles by',
            type=lambda value: Pts(api, value),
        )
        parser.add_argument(
            '-e', '--end',
            help='amount to shift the end of the subtitles by',
            type=lambda value: Pts(api, value),
        )
        parser.add_argument(
            '--no-align',
            help='don\'t realign subtitles to video frames',
            action='store_true',
        )


COMMANDS = [SubtitlesShiftCommand]
