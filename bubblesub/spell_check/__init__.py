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

"""Spell checker utilities."""

# pylint: disable=import-outside-toplevel

import typing as T

from .common import (
    BaseSpellChecker,
    DictNotFound,
    SpellCheckerError,
    SpellCheckerNotFound,
)


def create_spell_checker(language: str) -> BaseSpellChecker:
    """Create a new spell checker instance.

    If no spell checker libraries are installed in the system, raises
    SpellCheckerNotFound.

    :param language: language to check spelling with
    :return: a spell checker instance
    """
    try:
        from .enchant import EnchantSpellChecker

        return EnchantSpellChecker(language)
    except ImportError:
        pass

    try:
        from .pyspellchecker import PySpellCheckerSpellChecker

        return PySpellCheckerSpellChecker(language)
    except ImportError:
        pass

    raise SpellCheckerNotFound
