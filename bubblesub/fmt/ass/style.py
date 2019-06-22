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

"""ASS style and style list."""

import typing as T
from collections import namedtuple

from bubblesub.model import ObservableList, ObservableObject

AssColor = namedtuple("AssColor", ["red", "green", "blue", "alpha"])


class AssStyle(ObservableObject):
    """ASS style."""

    def __init__(
        self,
        name: str,
        font_name: str = "Arial",
        font_size: int = 20,
        primary_color: AssColor = AssColor(255, 255, 255, 0),
        secondary_color: AssColor = AssColor(255, 0, 0, 0),
        outline_color: AssColor = AssColor(32, 32, 32, 0),
        back_color: AssColor = AssColor(32, 32, 32, 127),
        bold: bool = True,
        italic: bool = False,
        underline: bool = False,
        strike_out: bool = False,
        scale_x: float = 100.0,
        scale_y: float = 100.0,
        spacing: float = 0.0,
        angle: float = 0.0,
        border_style: int = 1,
        outline: float = 3.0,
        shadow: float = 0.0,
        alignment: int = 2,
        margin_left: int = 20,
        margin_right: int = 20,
        margin_vertical: int = 20,
        encoding: int = 1,
    ) -> None:
        """Initialize self.

        :param name: style name
        :param font_name: font family
        :param font_size: font size in points
        :param primary_color: font color as tuple
        :param secondary_color: inactive karaoke font color as tuple
        :param outline_color: outline font color as tuple
        :param back_color: shadow font color as tuple
        :param bold: bold
        :param italic: italic
        :param underline: underline
        :param strike_out: strike out
        :param scale_x: horizontal scale factor (100.0 = 100%)
        :param scale_y: vertical scale factor (100.0 = 100%)
        :param spacing: kerning
        :param angle: angle in degrees
        :param border_style: border style
        :param outline: outline in pixels
        :param shadow: shadow in pixels
        :param alignment: alignment (1-9)
        :param margin_left: left margin in pixels
        :param margin_right: right margin in pixels
        :param margin_vertical: vertical margins in pixels
        :param encoding: text encoding
        """
        super().__init__()

        self._old_name: T.Optional[str] = None
        self.style_list: T.Optional["AssStyleList"] = None

        self._name = name
        self.font_name = font_name
        self.font_size = font_size
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.outline_color = outline_color
        self.back_color = back_color
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.strike_out = strike_out
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.spacing = spacing
        self.angle = angle
        self.border_style = border_style
        self.outline = outline
        self.shadow = shadow
        self.alignment = alignment
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.margin_vertical = margin_vertical
        self.encoding = encoding

    def scale(self, factor: float) -> None:
        """Scale self by the given factor.

        :param factor: scale to scale self by
        """
        self.font_size = int(self.font_size * factor)
        self.outline *= factor
        self.shadow *= factor
        self.margin_left = int(self.margin_left * factor)
        self.margin_right = int(self.margin_right * factor)
        self.margin_vertical = int(self.margin_vertical * factor)

    @property
    def index(self) -> T.Optional[int]:
        """Return style index in the parent style list, starting at 0.

        :return: index if style has parent list, None otherwise
        """
        # XXX: meh
        if self.style_list is not None:
            return self.style_list.index(self)
        return None

    @property
    def name(self) -> str:
        """Return style name.

        :return: style name
        """
        return self._name

    @name.setter
    def name(self, new_name: str) -> None:
        """Set new style name.

        Remembers old name so that the event with style change can be fired
        with the old name.

        :param new_name: new name
        """
        self._old_name = self._name
        self._name = new_name

    def _after_change(self) -> None:
        """Emit item changed event in the parent style list."""
        index = self.index
        if index is not None and self.style_list is not None:
            self.style_list.item_changed.emit(self.index)

    def __getstate__(self) -> T.Any:
        """Return pickle compatible object representation.

        The pickled copy is detached from the parent list.

        :return: object representation
        """
        ret = self.__dict__.copy()
        del ret["style_list"]
        return ret

    def __setstate__(self, state: T.Any) -> None:
        """Load class state from pickle compatible object representation.

        :param state: object representation
        """
        self.__dict__.update(state)
        self.style_list = None

    def __copy__(self) -> "AssStyle":
        """Duplicate self.

        The copy is detached from the parent list.

        :return: duplicate of self
        """
        ret = type(self)(name=self.name)
        for key, value in self.__dict__.items():
            if not callable(value):
                ret.__dict__[key] = value
        ret.__dict__["style_list"] = None
        return ret


class AssStyleList(ObservableList[AssStyle]):
    """ASS style list."""

    def insert(self, idx: int, *items: AssStyle) -> None:
        """Insert styles at the specified position.

        :param idx: index to add the new styles at
        :param items: styles to add
        """
        for item in items:
            assert item.style_list is None, "AssStyle belongs to another list"
            item.style_list = self
        super().insert(idx, *items)

    def remove(self, idx: int, count: int) -> None:
        """Remove styles at the specified position.

        :param idx: where to start the removal
        :param count: how many elements to remove
        """
        for item in self._items[idx : idx + count]:
            item.style_list = None
        super().remove(idx, count)

    def get_by_name(self, name: str) -> T.Optional[AssStyle]:
        """Retrieve style by its name.

        :param name: name of the style to look for
        :return: style instance if one was found, None otherwise
        """
        for style in self._items:
            if style.name == name:
                return style
        return None
