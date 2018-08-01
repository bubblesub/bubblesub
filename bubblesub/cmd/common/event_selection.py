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

"""Common utilities shared between commands."""

import re
import typing as T

from PyQt5 import QtWidgets

import bubblesub.api
from bubblesub.ass.event import Event


class EventSelection:
    def __init__(self, api: bubblesub.api.Api, target: str) -> None:
        self.api = api
        self.target = target

    @property
    def description(self) -> str:
        if self.target == 'all':
            return 'all subtitles'

        if self.target == 'none':
            return 'no subtitles'

        if self.target == 'one-above':
            return 'subtitle above'

        if self.target == 'one-below':
            return 'subtitle below'

        if self.target == 'first':
            return 'first subtitle'

        if self.target == 'last':
            return 'last subtitle'

        if self.target == 'ask-number':
            return 'subtitle by number'

        if self.target == 'ask-time':
            return 'subtitle by time'

        if self.target == 'selected':
            return 'selected subtitles'

        match = re.match(r'(\d+)', self.target)
        if match:
            return 'subtitle #' + match.group(1)

        raise ValueError(f'Unknown selection target: "{self.target}"')

    @property
    def makes_sense(self) -> bool:
        if self.target in {'all', 'none'}:
            return True

        if self.target in {
                'one-below', 'one-above',
                'first', 'last',
                'ask-time', 'ask-number'
        }:
            return len(self.api.subs.events) > 0

        if self.target == 'selected':
            return self.api.subs.has_selection

        match = re.match(r'(\d+)', self.target)
        if match:
            idx = int(match.group(1)) - 1
            return idx in range(len(self.api.subs.events))

        return False

    async def get_all_indexes(self):
        if self.target == 'all':
            return list(range(len(self.api.subs.events)))

        if self.target == 'none':
            return []

        if self.target == 'one-above':
            if not self.api.subs.selected_indexes:
                return [len(self.api.subs.events) - 1]
            return [max(0, self.api.subs.selected_indexes[0] - 1)]

        if self.target == 'one-below':
            if not self.api.subs.selected_indexes:
                return [0]
            return [min(
                self.api.subs.selected_indexes[-1] + 1,
                len(self.api.subs.events) - 1
            )]

        if self.target == 'selected':
            return self.api.subs.selected_indexes

        if self.target == 'first':
            return [0]

        if self.target == 'last':
            return [len(self.api.subs.events) - 1]

        if self.target == 'ask-number':
            if not len(self.api.subs.events):
                return []
            value = await self.api.gui.exec(self._show_number_dialog)
            return [] if value is None else [value - 1]

        if self.target == 'ask-time':
            if not len(self.api.subs.events):
                return []
            value = await self.api.gui.exec(self._show_time_dialog)
            return [] if value is None else [value - 1]

        match = re.match(r'(\d+)', self.target)
        if match:
            return [int(match.group(0)) - 1]

        raise ValueError(f'Unknown selection target: "{self.target}"')

    async def get_indexes(self):
        return [
            idx
            for idx in await self.get_all_indexes()
            if idx in range(0, len(self.api.subs.events))
        ]

    async def get_subtitles(self) -> T.List[Event]:
        return [self.api.subs.events[idx] for idx in await self.get_indexes()]

    async def _show_number_dialog(
            self,
            main_window: QtWidgets.QMainWindow
    ) -> T.Optional[int]:
        dialog = QtWidgets.QInputDialog(main_window)
        dialog.setLabelText('Line number to jump to:')
        dialog.setIntMinimum(1)
        dialog.setIntMaximum(len(self.api.subs.events))
        if self.api.subs.has_selection:
            dialog.setIntValue(self.api.subs.selected_indexes[0] + 1)
        dialog.setInputMode(QtWidgets.QInputDialog.IntInput)
        if dialog.exec_():
            return T.cast(int, dialog.intValue())
        return None

    async def _show_time_dialog(
            self,
            main_window: QtWidgets.QMainWindow
    ) -> T.Optional[int]:
        ret = bubblesub.ui.util.time_jump_dialog(
            main_window,
            value=(
                self.api.subs.selected_events[0].start
                if self.api.subs.has_selection else
                0
            ),
            absolute_label='Time to jump to:',
            relative_checked=False,
            show_radio=False
        )
        if ret is None:
            return None

        target_pts, _is_relative = ret
        best_distance = None
        best_idx = None
        for i, sub in enumerate(self.api.subs.events):
            center = (sub.start + sub.end) / 2
            distance = abs(target_pts - center)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_idx = i
        if best_idx is None:
            return None

        return best_idx
