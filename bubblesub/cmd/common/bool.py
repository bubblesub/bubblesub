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

"""Boolean operation."""

import typing as T


class BooleanOperation:
    YES = ["1", "yes", "y", "on", "enable"]
    NO = ["0", "no", "n", "off", "disable"]
    TOGGLE = ["toggle"]

    def __init__(self, operation: str) -> None:
        self.operation = operation

    def __str__(self) -> str:
        return self.operation

    def __hash__(self) -> int:
        return hash(self.operation)

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, BooleanOperation)
            and self.operation == other.operation
        )

    @classmethod
    def choices(cls: T.Any) -> T.List[T.Any]:
        return [cls(choice) for choice in cls.YES + cls.NO + cls.TOGGLE]

    def apply(self, origin: bool) -> bool:
        if self.operation in self.YES:
            return True
        if self.operation in self.NO:
            return False
        if self.operation in self.TOGGLE:
            return not origin
        raise ValueError(f'unknown operation: "{self.operation}"')
