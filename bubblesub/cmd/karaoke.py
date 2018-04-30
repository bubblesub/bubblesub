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

import re
import typing as T
from copy import copy

import bubblesub.ass.event
from bubblesub.api.cmd import CoreCommand


class Syllable:
    def __init__(self, text: str, duration: int) -> None:
        self.text = text
        self.duration = duration


class EditKaraokeSplitCommand(CoreCommand):
    name = 'edit/karaoke-split'
    menu_name = '&Split subtitles as karaoke'

    @property
    def is_enabled(self) -> bool:
        return (
            len(self.api.subs.selected_indexes) == 1
            and '\\k' in self.api.subs.selected_lines[0].text
        )

    async def run(self) -> None:
        idx = self.api.subs.selected_indexes[0]
        sub = self.api.subs.lines[idx]
        start = sub.start
        end = sub.end
        syllables = self._get_syllables(sub.text)

        self.api.gui.begin_update()
        with self.api.undo.capture():
            self.api.subs.lines.remove(idx, 1)

            new_subs: T.List[bubblesub.ass.event.Event] = []
            for syllable in syllables:
                sub_copy = copy(sub)
                sub_copy.text = syllable.text
                sub_copy.start = start
                sub_copy.end = min(end, start + syllable.duration * 10)
                start = sub_copy.end
                new_subs.append(sub_copy)

            self.api.subs.lines.insert(idx, new_subs)
            self.api.subs.selected_indexes = list(
                range(idx, idx + len(syllables))
            )
        self.api.gui.end_update()

    def _get_syllables(self, text: str) -> T.List[Syllable]:
        syllables = [Syllable(text='', duration=0)]
        for group in re.split('({[^{}]*})', text):
            if group.startswith('{'):
                match = re.search('\\\\k(\\d+)', group)
                if match:
                    syllables.append(Syllable(
                        text='',
                        duration=int(match.group(1))
                    ))
                    # remove the leftover \k tag
                    group = group[:match.start()] + group[match.end():]
                    if group == '{}':
                        group = ''
                syllables[-1].text += group
            else:
                syllables[-1].text += group
        if not syllables[0].text and syllables[0].duration == 0:
            syllables = syllables[1:]
        return syllables


class EditKaraokeJoinCommand(CoreCommand):
    name = 'edit/karaoke-join'
    menu_name = '&Join subtitles (as karaoke)'

    @property
    def is_enabled(self) -> bool:
        return len(self.api.subs.selected_indexes) > 1

    async def run(self) -> None:
        subs = self.api.subs.selected_lines
        with self.api.undo.capture():
            for idx in reversed(self.api.subs.selected_indexes[1:]):
                self.api.subs.lines.remove(idx, 1)

            text = ''
            for sub in subs:
                text += ('{\\k%d}' % (sub.duration // 10)) + sub.text
            subs[0].text = text
            subs[0].end = subs[-1].end

            assert subs[0].index is not None
            self.api.subs.selected_indexes = [subs[0].index]


class EditTransformationJoinCommand(CoreCommand):
    name = 'edit/transformation-join'
    menu_name = '&Join subtitles (as transformation)'

    @property
    def is_enabled(self) -> bool:
        return len(self.api.subs.selected_indexes) > 1

    async def run(self) -> None:
        subs = self.api.subs.selected_lines
        with self.api.undo.capture():
            for idx in reversed(self.api.subs.selected_indexes[1:]):
                self.api.subs.lines.remove(idx, 1)

            text = ''
            note = ''
            pos = 0
            for i, sub in enumerate(subs):
                pos += sub.duration
                text += sub.text
                note += sub.note
                if i != len(subs) - 1:
                    text += (
                        '{\\alpha&HFF&\\t(%d,%d,\\alpha&H00&)}' % (pos, pos)
                    )
            subs[0].text = text
            subs[0].note = note
            subs[0].end = subs[-1].end

            assert subs[0].index is not None
            self.api.subs.selected_indexes = [subs[0].index]
