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

import typing as T

import spellchecker

from bubblesub.spell_check.common import BaseSpellChecker, DictNotFound


class PySpellCheckerSpellChecker(BaseSpellChecker):
    def __init__(self, language: str) -> None:
        self._ignored: T.Set[str] = set()
        try:
            self._dict = spellchecker.SpellChecker(language=language)
        except ValueError:
            raise DictNotFound(language)

    def add(self, word: str) -> None:
        self._dict.word_frequency.add(word)

    def add_to_session(self, word: str) -> None:
        self._ignored.add(word)

    def check(self, word: str) -> bool:
        return word in self._ignored or self._dict.known([word])

    def suggest(self, word: str) -> T.Iterable[str]:
        yield from self._dict.candidates(word)
