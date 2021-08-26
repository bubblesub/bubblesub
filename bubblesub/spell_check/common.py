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

"""Shared definitions of spell checker classes."""

import abc
from collections.abc import Iterable


class SpellCheckerError(Exception):
    """Base spell checker error."""


class DictNotFound(SpellCheckerError):
    """Dictionary not found error."""

    def __init__(self, language: str) -> None:
        """Initialize self.

        :param language: dictionary language that wasn't found
        """
        super().__init__(f"dictionary {language} not installed")


class SpellCheckerNotFound(SpellCheckerError):
    """Spell checker not found error."""

    def __init__(self) -> None:
        """Initialize self."""
        super().__init__(
            "no spell checker module installed "
            "(either install pyenchant or pyspellchecker)"
        )


class BaseSpellChecker:
    """Base spell checker class."""

    def __init__(self, language: str) -> None:
        """Initialize self.

        :param language: language to check the spelling with
        """
        self.language = language

    @abc.abstractmethod
    def add(self, word: str) -> None:
        """Add a word globally.

        :param word: word to add to the dictionary
        """

    @abc.abstractmethod
    def add_to_session(self, word: str) -> None:
        """Add a word temporarily.

        :param word: word to add to the dictionary
        """

    @abc.abstractmethod
    def check(self, word: str) -> bool:
        """Check whether a word is spelt correctly.

        :param word: word to check
        :return: whether the word is spelt correctly
        """

    @abc.abstractmethod
    def suggest(self, word: str) -> Iterable[str]:
        """Check for similar words to the given word.

        :param word: word to check
        :return: list of closest candidates
        """
