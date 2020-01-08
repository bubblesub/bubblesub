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

"""Subtitles selection, usable as an argument to commands."""

import itertools
import typing as T
from math import inf

import regex
from PyQt5 import QtWidgets

from bubblesub.api import Api
from bubblesub.api.cmd import CommandCanceled
from bubblesub.fmt.ass.event import AssEvent
from bubblesub.ui.util import async_dialog_exec, time_jump_dialog
from bubblesub.util import first

IDX_REGEX = regex.compile(
    r"^(?P<token>\d+)(?:(?P<token>\.\.\.?|,)(?P<token>\d+))*$"
)


def _split_by_delim(
    source: T.List[T.Any], delim: str
) -> T.Iterable[T.List[T.Any]]:
    return (
        list(chunk)
        for is_delim, chunk in itertools.groupby(
            source, lambda item: item == delim
        )
        if not is_delim
    )


def _match_indexes(target: str) -> T.Optional[T.List[int]]:
    match = IDX_REGEX.match(target)
    if not match:
        return None

    ret: T.List[int] = []

    for group in _split_by_delim(match.captures("token"), ","):
        if len(group) == 1:
            idx = int(group[0]) - 1
            if idx != -1:
                ret.append(idx)
        elif len(group) == 3:
            low = int(group[0]) - 1
            high = int(group[2]) - 1
            if low > high:
                low, high = high, low
            ret += list(range(low, high + 1))
        else:
            raise AssertionError

    return ret


def _filter_indexes(api: Api, indexes: T.List[int]) -> T.Iterable[int]:
    valid_indexes = range(len(api.subs.events))
    for idx in indexes:
        if idx in valid_indexes:
            yield idx


class SubtitlesSelection:
    def __init__(self, api: Api, target: str) -> None:
        self.api = api
        self.target = target

    @property
    def makes_sense(self) -> bool:
        if self.target in {"all", "none"}:
            return True

        if self.target in {
            "one-below",
            "one-above",
            "first",
            "last",
            "ask-time",
            "ask-number",
        }:
            return bool(self.api.subs.events)

        if self.target == "selected":
            return self.api.subs.has_selection

        indexes = _match_indexes(self.target)
        if indexes is not None:
            indexes = list(_filter_indexes(self.api, indexes))
            return bool(indexes)

        raise ValueError(f'unknown selection target: "{self.target}"')

    async def get_all_indexes(self) -> T.List[int]:
        func = {
            "all": self._get_all,
            "none": self._get_none,
            "one-above": self._get_one_above,
            "one-below": self._get_one_below,
            "selected": self._get_selected,
            "first": self._get_first,
            "last": self._get_last,
            "ask-number": self._get_ask_number,
            "ask-time": self._get_ask_time,
        }.get(self.target)

        if func is not None:
            return await func()

        indexes = _match_indexes(self.target)
        if indexes is not None:
            return list(_filter_indexes(self.api, indexes))

        raise ValueError(f'unknown selection target: "{self.target}"')

    async def get_indexes(self) -> T.List[int]:
        return [
            idx
            for idx in await self.get_all_indexes()
            if idx in range(len(self.api.subs.events))
        ]

    async def get_subtitles(self) -> T.List[AssEvent]:
        return [self.api.subs.events[idx] for idx in await self.get_indexes()]

    async def _get_all(self) -> T.List[int]:
        return list(range(len(self.api.subs.events)))

    async def _get_none(self) -> T.List[int]:
        return []

    async def _get_one_above(self) -> T.List[int]:
        if self.api.subs.selected_indexes:
            return [max(0, self.api.subs.selected_indexes[0] - 1)]
        target_sub = first(
            sub
            for sub in sorted(
                self.api.subs.events, key=lambda sub: sub.start, reverse=True
            )
            if sub.start <= self.api.playback.current_pts
        )
        if target_sub:
            return [target_sub.index]
        return [len(self.api.subs.events) - 1]

    async def _get_one_below(self) -> T.List[int]:
        if self.api.subs.selected_indexes:
            return [
                min(
                    self.api.subs.selected_indexes[-1] + 1,
                    len(self.api.subs.events) - 1,
                )
            ]
        target_sub = first(
            sub
            for sub in sorted(self.api.subs.events, key=lambda sub: sub.start)
            if sub.start >= self.api.playback.current_pts
        )
        if target_sub:
            return [target_sub.index]
        return [0]

    async def _get_selected(self) -> T.List[int]:
        return self.api.subs.selected_indexes

    async def _get_first(self) -> T.List[int]:
        return [0] if self.api.subs.events else []

    async def _get_last(self) -> T.List[int]:
        length = len(self.api.subs.events)
        return [length - 1] if length else []

    async def _get_ask_number(self) -> T.List[int]:
        if not self.api.subs.events:
            return []
        value = await self.api.gui.exec(self._show_number_dialog)
        if value is None:
            raise CommandCanceled
        return [value - 1]

    async def _get_ask_time(self) -> T.List[int]:
        if not self.api.subs.events:
            return []
        value = await self.api.gui.exec(self._show_time_dialog)
        if value is None:
            raise CommandCanceled
        return [value - 1]

    async def _show_number_dialog(
        self, main_window: QtWidgets.QMainWindow
    ) -> T.Optional[int]:
        dialog = QtWidgets.QInputDialog(main_window)
        dialog.setLabelText("Line number to jump to:")
        dialog.setIntMinimum(1)
        dialog.setIntMaximum(len(self.api.subs.events))
        if self.api.subs.has_selection:
            dialog.setIntValue(self.api.subs.selected_indexes[0] + 1)
        dialog.setInputMode(QtWidgets.QInputDialog.IntInput)
        if await async_dialog_exec(dialog):
            return dialog.intValue()
        return None

    async def _show_time_dialog(
        self, main_window: QtWidgets.QMainWindow
    ) -> T.Optional[int]:
        ret = await time_jump_dialog(
            main_window,
            value=(
                self.api.subs.selected_events[0].start
                if self.api.subs.has_selection
                else 0
            ),
            relative_checked=False,
            show_radio=False,
        )
        if ret is None:
            return None

        target_pts, _is_relative = ret
        best_distance = inf
        best_idx = None
        for i, sub in enumerate(self.api.subs.events):
            center = (sub.start + sub.end) / 2
            distance = abs(target_pts - center)
            if distance < best_distance:
                best_distance = distance
                best_idx = i
        if best_idx is None:
            return None

        return best_idx
