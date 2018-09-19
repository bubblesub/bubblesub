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

"""Presentation timestamp, usable as an argument to commands."""

import bisect
import typing as T
from dataclasses import dataclass

import regex
from PyQt5 import QtWidgets

import bubblesub.ui.util
from bubblesub.api import Api
from bubblesub.api.cmd import CommandCanceled
from bubblesub.api.cmd import CommandError
from bubblesub.api.cmd import CommandUnavailable
from bubblesub.ass.event import Event


def _bisect(source: T.List[int], origin: int, delta: int) -> int:
    if delta >= 0:
        # find leftmost value greater than origin
        idx = bisect.bisect_right(source, origin)
        idx += delta - 1
    elif delta < 0:
        # find rightmost value less than origin
        idx = bisect.bisect_left(source, origin)
        idx += delta

    idx = max(0, min(idx, len(source) - 1))
    return source[idx]


OPERATORS = {'add': r'\+', 'sub': '-'}
TERMINALS = {
    'rel_sub': r'(?P<direction>[cpn])s\.(?P<boundary>[se])',
    'rel_frame': '(?P<direction>[cpn])f',
    'rel_keyframe': '(?P<direction>[cpn])kf',
    'spectrogram': r'a\.(?P<boundary>[se])',
    'num_sub': r's(?P<number>\d+)\.(?P<boundary>[se])',
    'num_frame': r'(?P<number>\d+)f',
    'num_keyframe': r'(?P<number>\d+)kf',
    'num_ms': r'(?P<number>\d+)ms',
    'ask': 'ask',
    'default_sub_duration': 'dsd',
}

TOKENS = {}
TOKENS.update(OPERATORS)
TOKENS.update(TERMINALS)


class _ResetValue(Exception):
    def __init__(self, value: int) -> None:
        super().__init__()
        self.value = value


@dataclass
class _Token:
    name: str
    match: T.Match[str]

    @property
    def text(self) -> str:
        return self.match.group(0)


def _sub_boundary(subtitle: Event, token: _Token) -> int:
    boundary = token.match.group('boundary')
    if boundary == 's':
        return subtitle.start
    if boundary == 'e':
        return subtitle.end
    raise AssertionError(f'unknown boundary: "{boundary}"')


class Pts:
    def __init__(self, api: Api, value: str) -> None:
        self._api = api
        self.value = value

    async def get(
            self,
            origin: T.Optional[int] = None,
            align_to_near_frame: bool = False
    ) -> int:
        ret = await self._get(origin)
        if align_to_near_frame:
            ret = self._api.media.video.align_pts_to_near_frame(ret)
        return ret

    async def _get(self, value: T.Optional[int]) -> int:
        # simple LL(1) parser / evaulator
        tokens = list(self._tokenize())
        if not tokens:
            raise CommandError('empty value')

        first_terminal = True
        while tokens:
            token = tokens.pop(0)

            if token.name in TERMINALS.keys():
                if not first_terminal:
                    raise CommandError('expected operator')
                value = await self._eval_operator(
                    left=value, right=token, operator=None
                )
                first_terminal = False

            elif token.name in OPERATORS.keys():
                if not tokens:
                    raise CommandError('missing operand')

                operator = token.text
                adjacent_token = tokens.pop(0)

                if adjacent_token.name in TERMINALS.keys():
                    value = await self._eval_operator(
                        left=value, right=adjacent_token, operator=operator
                    )

                elif adjacent_token.name in OPERATORS.keys():
                    raise CommandError(
                        'operator must be followed by an operand'
                    )

                else:
                    raise AssertionError(f'unknown token: "{token.text}"')

            else:
                raise AssertionError(f'unknown token: "{token.text}"')

        assert value is not None
        return value

    def _tokenize(self) -> T.Iterable[_Token]:
        pos = 0
        while pos < len(self.value):
            if self.value[pos].isspace():
                pos += 1
            for name, rgx in TOKENS.items():
                match = regex.match(rgx, self.value, pos=pos)
                if match and match.start() == pos:
                    yield _Token(name=name, match=match)
                    pos = match.end()
                    break
            else:
                raise CommandError(f'syntax error near "{self.value[pos:]}"')

    async def _eval_operator(
            self,
            left: T.Optional[int],
            right: _Token,
            operator: T.Optional[str],
    ) -> int:
        try:
            right_val = await self._eval_terminal(
                right, origin=left, operator=operator
            )
        except _ResetValue as ex:
            return ex.value
        if operator is None:
            return right_val
        if operator == '+':
            return (left or 0) + right_val
        if operator == '-':
            return (left or 0) - right_val
        raise AssertionError(f'unknown operator: "{operator}"')

    async def _eval_terminal(
            self,
            token: _Token,
            origin: T.Optional[int],
            operator: T.Optional[str],
    ) -> int:
        func = getattr(self, '_eval_terminal_' + token.name, None)
        if not func:
            raise AssertionError(f'unknown token: "{token.name}"')
        return await func(token, origin, operator)

    async def _eval_terminal_num_ms(
            self,
            token: _Token,
            _origin: T.Optional[int],
            _operator: T.Optional[str],
    ) -> int:
        return int(token.match.group('number'))

    async def _eval_terminal_num_frame(
            self,
            token: _Token,
            origin: T.Optional[int],
            operator: T.Optional[str],
    ) -> int:
        delta = int(token.match.group('number'))
        if operator is None:
            return self._apply_frame(0, delta)
        origin = origin or 0
        if operator == '-':
            delta *= -1
        elif operator != '+':
            raise AssertionError(f'unknown operator: "{operator}"')
        raise _ResetValue(self._apply_frame(origin, delta))

    async def _eval_terminal_num_keyframe(
            self,
            token: _Token,
            origin: T.Optional[int],
            operator: T.Optional[str],
    ) -> int:
        delta = int(token.match.group('number'))
        if operator is None:
            return self._apply_keyframe(0, delta)
        origin = origin or 0
        if operator == '-':
            delta *= -1
        elif operator != '+':
            raise AssertionError(f'unknown operator: "{operator}"')
        raise _ResetValue(self._apply_keyframe(origin, delta))

    async def _eval_terminal_default_sub_duration(
            self,
            _token: _Token,
            _origin: T.Optional[int],
            _operator: T.Optional[str],
    ) -> int:
        return self._api.opt.general.subs.default_duration

    async def _eval_terminal_rel_frame(
            self,
            token: _Token,
            _origin: T.Optional[int],
            _operator: T.Optional[str],
    ) -> int:
        direction = token.match.group('direction')
        if direction == 'p':
            return self._apply_frame(self._api.media.current_pts, -1)
        if direction == 'c':
            return self._api.media.current_pts
        if direction == 'n':
            return self._apply_frame(self._api.media.current_pts, 1)
        raise AssertionError(f'unknown direction: "{direction}"')

    async def _eval_terminal_rel_keyframe(
            self,
            token: _Token,
            _origin: T.Optional[int],
            _operator: T.Optional[str],
    ) -> int:
        direction = token.match.group('direction')
        if direction == 'p':
            return self._apply_keyframe(self._api.media.current_pts, -1)
        if direction == 'c':
            return self._apply_keyframe(self._api.media.current_pts, 0)
        if direction == 'n':
            return self._apply_keyframe(self._api.media.current_pts, 1)
        raise AssertionError(f'unknown direction: "{direction}"')

    async def _eval_terminal_rel_sub(
            self,
            token: _Token,
            _origin: T.Optional[int],
            _operator: T.Optional[str],
    ) -> int:
        direction = token.match.group('direction')
        try:
            if direction == 'p':
                sub = self._api.subs.selected_events[0].prev
            elif direction == 'c':
                sub = self._api.subs.selected_events[0]
            elif direction == 'n':
                sub = self._api.subs.selected_events[-1].next
            else:
                raise AssertionError(f'unknown direction: "{direction}"')
            if not sub:
                raise LookupError
        except LookupError:
            return 0
        return _sub_boundary(sub, token)

    async def _eval_terminal_num_sub(
            self,
            token: _Token,
            _origin: T.Optional[int],
            _operator: T.Optional[str],
    ) -> int:
        idx = int(token.match.group('number')) - 1
        try:
            sub = self._api.subs.events[idx]
        except LookupError:
            return 0
        return _sub_boundary(sub, token)

    async def _eval_terminal_spectrogram(
            self,
            token: _Token,
            _origin: T.Optional[int],
            _operator: T.Optional[str],
    ) -> int:
        boundary = token.match.group('boundary')
        if not self._api.media.audio.has_selection:
            raise CommandUnavailable
        if boundary == 's':
            return self._api.media.audio.selection_start
        if boundary == 'e':
            return self._api.media.audio.selection_end
        raise AssertionError(f'unknown boundary: "{boundary}"')

    async def _eval_terminal_ask(
            self,
            _token: _Token,
            origin: T.Optional[int],
            _operator: T.Optional[str],
    ) -> int:
        return await self._api.gui.exec(self._show_dialog, origin=origin)

    async def _show_dialog(
            self,
            main_window: QtWidgets.QMainWindow,
            origin: T.Optional[int],
    ) -> T.Optional[int]:
        ret = bubblesub.ui.util.time_jump_dialog(
            main_window,
            relative_checked=False,
            show_radio=origin is not None,
            value=self._api.media.current_pts
        )
        if ret is None:
            raise CommandCanceled

        value, is_relative = ret
        if is_relative:
            assert origin is not None
            return origin + value
        return value

    def _apply_frame(self, origin: int, delta: int) -> int:
        if not self._api.media.video.timecodes:
            raise CommandError('timecode information is not available')

        return _bisect(self._api.media.video.timecodes, origin, delta)

    def _apply_keyframe(self, origin: int, delta: int) -> int:
        if not self._api.media.video.keyframes:
            raise CommandError('keyframe information is not available')

        possible_pts = [
            self._api.media.video.timecodes[i]
            for i in self._api.media.video.keyframes
        ]
        return _bisect(possible_pts, origin, delta)
