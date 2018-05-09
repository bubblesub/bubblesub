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

"""ASS file."""

import typing as T
from collections import OrderedDict

from bubblesub.ass.event import EventList
from bubblesub.ass.style import StyleList


class AssFile:
    """ASS file."""

    def __init__(self) -> None:
        """Initialize self."""
        self.styles = StyleList()
        self.styles.insert_one(name='Default')
        self.events = EventList()
        self.info: T.Dict[str, str] = OrderedDict()
