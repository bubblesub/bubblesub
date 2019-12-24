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
import enum
import typing as T

import parsimonious
from dataclasses import dataclass

from bubblesub.api import Api
from bubblesub.api.cmd import CommandCanceled, CommandError
from bubblesub.fmt.ass.event import AssEvent
from bubblesub.ui.util import time_jump_dialog

GRAMMAR = r"""
line =
    unary_operation /
    binary_operation /
    operand

right_hand = binary_operation / operand
unary_operation = operator _ right_hand
binary_operation = operand _ operator _ right_hand

operand =
    time /
    frame /
    keyframe /
    subtitle /
    audio_selection /
    audio_view /
    rel_frame /
    rel_keyframe /
    rel_subtitle /
    min / max /
    dialog /
    default_duration

time             = milliseconds / seconds / minutes / colon_time
milliseconds     = integer _ 'ms'
seconds          = decimal _ 's'
minutes          = decimal _ 'm' (_ decimal _ 's')?
colon_time       = ~'((?P<h>\\d?\\d):)?(?P<m>\\d?\\d):(?P<s>\\d\\d)(\\.(?P<ms>\\d+))?'
frame            = integer _ 'f'
keyframe         = integer _ 'kf'
subtitle         = 's' integer (start / end)
audio_selection  = 'a' (start / end)
audio_view       = 'av' (start / end)
rel_frame        = rel 'f'
rel_keyframe     = rel 'kf'
rel_subtitle     = rel 's' (start / end)
default_duration = 'dsd' / 'default_duration'
min              = 'min'
max              = 'max'
dialog           = 'ask'

_                = ~'\\s*'
decimal           = ~'\\d+(\\.\\d+)?'
integer           = ~'\\d+'
operator         = '+' / '-'
rel              = 'c' / 'p' / 'n' / 'l' / 'f'
start            = '.start' / '.s'
end              = '.end' / '.e'
"""


class _AsyncNodeVisitor:
    """Port of parsimonious node visitor that works with asyncio"""

    grammar = None

    async def visit(self, node: T.Any) -> T.Any:
        method = getattr(self, "visit_" + node.expr_name, self.generic_visit)
        return await method(node, [await self.visit(n) for n in node])

    async def generic_visit(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        raise NotImplementedError(
            "No visitor method was defined for this expression: %s"
            % node.expr.as_rule()
        )

    async def parse(self, text: str, pos: int = 0) -> T.Any:
        return await self._parse_or_match(text, pos, "parse")

    async def match(self, text: str, pos: int = 0) -> T.Any:
        return await self._parse_or_match(text, pos, "match")

    async def _parse_or_match(
        self, text: str, pos: int, method_name: str
    ) -> T.Any:
        if not self.grammar:
            raise RuntimeError(
                "The {cls}.{method}() shortcut won't work because {cls} was "
                "never associated with a specific "
                "grammar. Fill out its "
                "`grammar` attribute, and try again.".format(
                    cls=self.__class__.__name__, method=method_name
                )
            )
        return await self.visit(
            getattr(self.grammar, method_name)(text, pos=pos)
        )


class _Token(enum.IntEnum):
    previous = enum.auto()
    next = enum.auto()
    current = enum.auto()
    first = enum.auto()
    last = enum.auto()

    start = enum.auto()
    end = enum.auto()

    @staticmethod
    def start_end(obj: T.Any, token: "_Token") -> T.Any:
        if token == _Token.start:
            return obj.start
        if token == _Token.end:
            return obj.end
        raise NotImplementedError(f'unknown boundary: "{token}"')

    @staticmethod
    def prev_next(obj: T.Any, token: "_Token") -> T.Any:
        if token == _Token.previous:
            return obj.prev
        if token == _Token.current:
            return obj
        if token == _Token.next:
            return obj.next
        raise NotImplementedError(f'unknown direction: "{token}"')

    @staticmethod
    def delta_from_direction(token: "_Token") -> int:
        mapping = {_Token.previous: -1, _Token.current: 0, _Token.next: 1}
        try:
            return mapping[token]
        except LookupError:
            raise NotImplementedError(f'unknown direction: "{token}"')


class _TimeUnit(enum.IntEnum):
    ms = 0
    frame = 1
    keyframe = 2


@dataclass
class _Time:
    value: int = 0
    unit: _TimeUnit = _TimeUnit.ms

    @staticmethod
    def add(time1: "_Time", time2: "_Time", api: Api) -> "_Time":
        return _Time.mod(
            time1, time2, api, lambda value1, value2: value1 + value2
        )

    @staticmethod
    def sub(time1: "_Time", time2: "_Time", api: Api) -> "_Time":
        return _Time.mod(
            time1, time2, api, lambda value1, value2: value1 - value2
        )

    @staticmethod
    def mod(
        time1: "_Time",
        time2: "_Time",
        api: Api,
        func: T.Callable[[int, int], int],
    ) -> "_Time":
        """Performs time arithmetic.

        Tries to preserve frame numbers between math operations if possible.
        Resolves basic frame arithmetic into actual frame times.

        :param time1: lefthand time
        :param time2: righthand time
        :param api: core API
        :param func: what to do with the time values
        :return: resulting time
        """
        if time1.unit == time2.unit:
            return _Time(func(time1.value, time2.value), time1.unit)
        if time2.unit == _TimeUnit.ms:
            return _Time(func(time1.unpack(api), time2.value))
        if time2.unit == _TimeUnit.frame:
            return _Time(
                _apply_frame(api, time1.unpack(api), func(0, time2.value))
            )
        if time2.unit == _TimeUnit.keyframe:
            return _Time(
                _apply_keyframe(api, time1.unpack(api), func(0, time2.value))
            )
        raise NotImplementedError(f"unknown time unit: {time2.unit}")

    def unpack(self, api: Api) -> int:
        """Resolves frame indexes into pts.

        :param api: core API
        :return: resolved pts
        """
        current_stream = api.video.current_stream
        if self.unit == _TimeUnit.frame:
            if not current_stream or not current_stream.timecodes:
                raise CommandError("timecode information is not available")
            idx = max(1, min(self.value, len(current_stream.timecodes))) - 1
            return current_stream.timecodes[idx]
        if self.unit == _TimeUnit.keyframe:
            if not current_stream or not current_stream.timecodes:
                raise CommandError("keyframe information is not available")
            idx = max(1, min(self.value, len(current_stream.keyframes))) - 1
            return current_stream.timecodes[current_stream.keyframes[idx]]
        if self.unit == _TimeUnit.ms:
            return self.value
        raise NotImplementedError(f"unknown unit: {self.unit}")


def _flatten(items: T.Any) -> T.List[T.Any]:
    if isinstance(items, (list, tuple)):
        return [
            item
            for sublist in items
            for item in _flatten(sublist)
            if item is not None
        ]
    return [items]


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


def _apply_frame(api: Api, origin: int, delta: int) -> int:
    if not api.video.current_stream or not api.video.current_stream.timecodes:
        raise CommandError("timecode information is not available")
    return _bisect(api.video.current_stream.timecodes, origin, delta)


def _apply_keyframe(api: Api, origin: int, delta: int) -> int:
    if not api.video.current_stream or not api.video.current_stream.keyframes:
        raise CommandError("keyframe information is not available")
    possible_pts = [
        api.video.current_stream.timecodes[i]
        for i in api.video.current_stream.keyframes
    ]
    return _bisect(possible_pts, origin, delta)


class _PtsNodeVisitor(_AsyncNodeVisitor):
    unwrapped_exceptions = (CommandError,)
    grammar = parsimonious.Grammar(GRAMMAR)

    def __init__(self, api: Api, origin: T.Optional[int]) -> None:
        self._api = api
        self._origin = origin

    # --- grammar features ---

    async def generic_visit(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        if not node.expr_name and not node.children:
            return node.text
        return _flatten(visited)

    async def visit_unary_operation(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        operator, time = _flatten(visited)
        if self._origin is not None:
            return await self.visit_binary_operation(
                node, [_Time(self._origin), operator, time]
            )
        if operator == "-":
            time.value *= -1
        return time

    async def visit_binary_operation(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        time1, operator, time2 = _flatten(visited)
        try:
            func = {"+": _Time.add, "-": _Time.sub}[operator]
        except LookupError:
            raise NotImplementedError(f"unknown operator: {operator}")
        return func(time1, time2, self._api)

    async def visit_line(self, node: T.Any, visited: T.List[T.Any]) -> T.Any:
        return _flatten(visited)[0].unpack(self._api)

    # --- basic tokens ---

    async def visit_integer(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        return int(node.text)

    async def visit_decimal(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        return float(node.text)

    async def visit_rel(self, node: T.Any, visited: T.List[T.Any]) -> T.Any:
        try:
            return {
                "c": _Token.current,
                "p": _Token.previous,
                "n": _Token.next,
                "f": _Token.first,
                "l": _Token.last,
            }[node.text]
        except LookupError:
            raise NotImplementedError(f"unknown relation: {node.text}")

    async def visit_start(self, node: T.Any, visited: T.List[T.Any]) -> T.Any:
        return _Token.start

    async def visit_end(self, node: T.Any, visited: T.List[T.Any]) -> T.Any:
        return _Token.end

    # --- times ---

    async def visit_milliseconds(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        return _Time(_flatten(visited)[0])

    async def visit_seconds(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        return _Time(int(_flatten(visited)[0] * 1000))

    async def visit_minutes(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        visited = _flatten(visited)
        minutes = visited[0]
        seconds = visited[2] if len(visited) >= 3 and visited[2] else 0
        seconds += minutes * 60
        return _Time(int(seconds * 1000))

    async def visit_colon_time(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        value = float("0." + (node.match.group("ms") or "0"))
        value += int(node.match.group("s") or "0")
        value += int(node.match.group("m") or "0") * 60
        value += int(node.match.group("h") or "0") * 3600
        return _Time(int(value * 1000))

    async def visit_subtitle(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        _, num, boundary = _flatten(visited)
        idx = max(1, min(num, len(self._api.subs.events))) - 1
        sub = self._api.subs.events.get(idx)
        return _Time(_Token.start_end(sub, boundary) if sub else 0)

    async def visit_frame(self, node: T.Any, visited: T.List[T.Any]) -> T.Any:
        num, _ = _flatten(visited)
        return _Time(num, _TimeUnit.frame)

    async def visit_keyframe(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        num, _ = _flatten(visited)
        return _Time(num, _TimeUnit.keyframe)

    async def visit_rel_subtitle(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        direction, _, boundary = _flatten(visited)
        sub: T.Optional[AssEvent]
        try:
            if direction == _Token.first:
                sub = self._api.subs.events[0]
            elif direction == _Token.last:
                sub = self._api.subs.events[-1]
            else:
                sub = self._api.subs.selected_events[0]
                sub = _Token.prev_next(sub, direction)
        except LookupError:
            sub = None
        return _Time(_Token.start_end(sub, boundary) if sub else 0)

    async def visit_rel_frame(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        direction, _ = _flatten(visited)
        origin = self._api.playback.current_pts
        if direction == _Token.first:
            return _Time(1, _TimeUnit.frame)
        if direction == _Token.last:
            return _Time(
                len(self._api.video.current_stream.timecodes), _TimeUnit.frame
            )
        if direction == _Token.current:
            return _Time(origin)
        delta = _Token.delta_from_direction(direction)
        return _Time(_apply_frame(self._api, origin, delta))

    async def visit_rel_keyframe(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        direction, _ = _flatten(visited)
        origin = self._api.playback.current_pts
        if direction == _Token.first:
            return _Time(1, _TimeUnit.keyframe)
        if direction == _Token.last:
            return _Time(
                len(self._api.video.current_stream.keyframes),
                _TimeUnit.keyframe,
            )
        delta = _Token.delta_from_direction(direction)
        return _Time(_apply_keyframe(self._api, origin, delta))

    async def visit_audio_selection(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        _, boundary = _flatten(visited)
        if boundary == _Token.start:
            return _Time(self._api.audio.view.selection_start)
        if boundary == _Token.end:
            return _Time(self._api.audio.view.selection_end)
        raise NotImplementedError(f'unknown boundary: "{boundary}"')

    async def visit_audio_view(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        _, boundary = _flatten(visited)
        if boundary == _Token.start:
            return _Time(self._api.audio.view.view_start)
        if boundary == _Token.end:
            return _Time(self._api.audio.view.view_end)
        raise NotImplementedError(f'unknown boundary: "{boundary}"')

    async def visit_default_duration(
        self, node: T.Any, visited: T.List[T.Any]
    ) -> T.Any:
        return _Time(self._api.cfg.opt["subs"]["default_duration"])

    async def visit_min(self, node: T.Any, visited: T.List[T.Any]) -> T.Any:
        return _Time(0)

    async def visit_max(self, node: T.Any, visited: T.List[T.Any]) -> T.Any:
        return _Time(self._api.playback.max_pts)

    async def visit_dialog(self, node: T.Any, visited: T.List[T.Any]) -> T.Any:
        ret = await self._api.gui.exec(
            time_jump_dialog,
            relative_checked=False,
            show_radio=self._origin is not None,
            value=self._api.playback.current_pts,
        )
        if ret is None:
            raise CommandCanceled

        value, is_relative = ret
        if is_relative:
            assert self._origin is not None
            return _Time(self._origin + value)
        return _Time(value)


class Pts:
    def __init__(self, api: Api, expr: str) -> None:
        self._api = api
        self.expr = expr

    async def get(
        self, origin: T.Optional[int] = None, align_to_near_frame: bool = False
    ) -> int:
        ret = await self._get(origin)
        if align_to_near_frame and self._api.video.current_stream:
            ret = self._api.video.current_stream.align_pts_to_near_frame(ret)
        return ret

    async def _get(self, origin: T.Optional[int]) -> int:
        try:
            node_visitor = _PtsNodeVisitor(self._api, origin)
            return await node_visitor.parse(self.expr.strip())
        except parsimonious.exceptions.ParseError as ex:
            raise CommandError(f"syntax error near {ex.pos}: {ex}")
