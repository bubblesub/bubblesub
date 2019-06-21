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

import abc
import typing as T


class SpellCheckerError(Exception):
    pass


class DictNotFound(SpellCheckerError):
    def __init__(self, language: str) -> None:
        super().__init__(f"dictionary {language} not installed")


class SpellCheckerNotFound(SpellCheckerError):
    def __init__(self) -> None:
        super().__init__(
            "no spell checker module installed "
            "(either install pyenchant or pyspellchecker)"
        )


class BaseSpellChecker:
    def __init__(self, language: str) -> None:
        self.language = None

    @abc.abstractmethod
    def add(self, word: str) -> None:
        ...

    @abc.abstractmethod
    def add_to_session(self, word: str) -> None:
        ...

    @abc.abstractmethod
    def check(self, word: str) -> bool:
        ...

    @abc.abstractmethod
    def suggest(self, word: str) -> T.Iterable[str]:
        ...
