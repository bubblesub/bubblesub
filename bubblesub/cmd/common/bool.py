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

_YES = ('1', 'yes', 'y', 'on', 'enable')
_NO = ('0', 'no', 'n', 'off', 'disable')
_TOGGLE = ('toggle',)


class BooleanOperation:
    def __init__(self, operation: str) -> None:
        self.operation = operation

    def get_description(
            self,
            yes_desc: str,
            no_desc: str,
            toggle_desc: str
    ) -> str:
        if self.operation in _YES:
            return yes_desc
        if self.operation in _NO:
            return no_desc
        if self.operation in _TOGGLE:
            return toggle_desc
        raise ValueError(f'unknown operation: "{self.operation}"')

    def apply(self, origin: bool):
        if self.operation in _YES:
            return True
        if self.operation in _NO:
            return False
        if self.operation in _TOGGLE:
            return not origin
        raise ValueError(f'unknown operation: "{self.operation}"')
