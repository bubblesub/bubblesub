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

"""Spell checker based on the pyenchant library."""

# pylint: disable=no-member

import typing as T

import enchant

from bubblesub.spell_check.common import BaseSpellChecker, DictNotFound


class EnchantSpellChecker(BaseSpellChecker):
    """Spell checker implementation"""

    def __init__(self, language: str) -> None:
        """Initialize self.

        :param language: language to check the spelling with
        """
        super().__init__(language)
        try:
            self._dict = enchant.Dict(language)
        except enchant.errors.DictNotFoundError:
            raise DictNotFound(language)

    def add(self, word: str) -> None:
        """Add a word globally.

        :param word: word to add to the dictionary
        """
        self._dict.add(word)

    def add_to_session(self, word: str) -> None:
        """Add a word temporarily.

        :param word: word to add to the dictionary
        """
        self._dict.add_to_session(word)

    def check(self, word: str) -> bool:
        """Check whether a word is spelt correctly.

        :param word: word to check
        :return: whether the word is spelt correctly
        """
        return self._dict.check(word)

    def suggest(self, word: str) -> T.Iterable[str]:
        """Check for similar words to the given word.

        :param word: word to check
        :return: list of closest candidates
        """
        yield from self._dict.suggest(word)
