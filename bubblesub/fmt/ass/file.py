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

from bubblesub.fmt.ass.event import AssEventList
from bubblesub.fmt.ass.meta import AssMeta
from bubblesub.fmt.ass.style import AssStyleList


class AssFile:
    """ASS file."""

    def __init__(self) -> None:
        """Initialize self."""
        self.styles = AssStyleList()
        self.events = AssEventList()
        self.meta = AssMeta()
