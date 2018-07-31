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

import bubblesub.api
from bubblesub.ass.event import Event


class EventSelection:
    def __init__(self, api: bubblesub.api.Api, target: str) -> None:
        self.api = api
        self.target = target

    def get_description(self) -> T.List[int]:
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

        if self.target == 'selected':
            return 'selected subtitles'

        match = re.match(r'(\d+)', self.target)
        if match:
            return 'subtitle #' + match.group(1)

        raise ValueError(f'Unknown selection target: "{self.target}"')

    def get_all_indexes(self):
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

        match = re.match(r'(\d+)', self.target)
        if match:
            return [int(match.group(0)) - 1]

        raise ValueError(f'Unknown selection target: "{self.target}"')

    def get_indexes(self):
        return [
            idx
            for idx in self.get_all_indexes()
            if idx in range(0, len(self.api.subs.events))
        ]

    def get_subtitles(self) -> T.List[Event]:
        return [self.api.subs.events[idx] for idx in self.get_indexes()]

    def any(self) -> bool:
        return len(self.get_indexes()) > 0
