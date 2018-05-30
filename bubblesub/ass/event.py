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

"""ASS event and event list."""

import typing as T

import bubblesub.ass
import bubblesub.model


class Event(bubblesub.model.ObservableObject):
    """ASS event."""

    def __init__(
            self,
            start: int = 0,
            end: int = 0,
            style: str = 'Default',
            actor: str = '',
            text: str = '',
            note: str = '',
            effect: str = '',
            layer: int = 0,
            margin_left: int = 0,
            margin_right: int = 0,
            margin_vertical: int = 0,
            is_comment: bool = False
    ) -> None:
        """
        Initialize self.

        :param start: start PTS
        :param end: end PTS
        :param style: style name
        :param actor: actor name
        :param text: event text
        :param note: event note
        :param effect: unused
        :param layer: layer number
        :param margin_left: pixels
        :param margin_right: pixels
        :param margin_vertical: pixels
        :param is_comment: whether to shown the subtitle in the player
        """
        super().__init__()

        self.event_list: T.Optional['EventList'] = None

        self.start = start
        self.end = end
        self.style = style
        self.actor = actor
        self._text = text
        self._note = note
        self.effect = effect
        self.layer = layer
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.margin_vertical = margin_vertical
        self.is_comment = is_comment

    @property
    def text(self) -> str:
        """
        Return event text.

        :return: text
        """
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        """
        Set new event text.

        :param value: new text
        """
        self._text = value.replace('\n', '\\N')

    @property
    def note(self) -> str:
        """
        Return event note.

        Notes are shown in the editor, but not in the player.

        :return: note
        """
        return self._note

    @note.setter
    def note(self, value: str) -> None:
        """
        Set new note.

        :param value: new note
        """
        self._note = value.replace('\n', '\\N')

    @property
    def duration(self) -> int:
        """
        Return subtitle duration in milliseconds.

        :return: duration
        """
        return self.end - self.start

    @property
    def index(self) -> T.Optional[int]:
        """
        Return subtitle index in the parent subtitle list, starting at 0.

        :return: index if subtitle has parent list, None otherwise
        """
        # XXX: meh
        if self.event_list is not None:
            return self.event_list.index(self)
        return None

    @property
    def number(self) -> T.Optional[int]:
        """
        Return subtitle index in the parent subtitle list, starting at 1.

        :return: index if subtitle has parent list, None otherwise
        """
        index = self.index
        if index is None:
            return None
        return index + 1

    @property
    def prev(self) -> T.Optional['Event']:
        """
        Return previous subtitle from the parent subtitle list.

        :return: previous subtitle if has parent list, None otherwise
        """
        index = self.index
        if index is None:
            return None
        assert self.event_list is not None
        return self.event_list.get(index - 1, None)

    @property
    def next(self) -> T.Optional['Event']:
        """
        Return next subtitle from the parent subtitle list.

        :return: next subtitle if has parent list, None otherwise
        """
        index = self.index
        if index is None:
            return None
        assert self.event_list is not None
        return self.event_list.get(index + 1, None)

    def _after_change(self) -> None:
        """Emit item changed event in the parent subtitle list."""
        index = self.index
        if index is not None and self.event_list is not None:
            self.event_list.item_changed.emit(index)

    def __getstate__(self) -> T.Any:
        """
        Return pickle compatible object representation.

        The pickled copy is detached from the parent list.

        :return: object representation
        """
        ret = self.__dict__.copy()
        del ret['event_list']
        return ret

    def __setstate__(self, state: T.Any) -> None:
        """
        Load class state from pickle compatible object representation.

        :param state: object representation
        """
        self.__dict__.update(state)
        self.event_list = None

    def __copy__(self) -> 'Event':
        """
        Duplicate self.

        The copy is detached from the parent list.

        :return: duplicate of self
        """
        ret = type(self)()
        for key, value in self.__dict__.items():
            if not callable(value):
                ret.__dict__[key] = value
        ret.__dict__['event_list'] = None
        return ret


class EventList(bubblesub.model.ObservableList[Event]):
    """ASS event list."""

    def insert_one(
            self,
            idx: T.Optional[int] = None,
            **kwargs: T.Any
    ) -> Event:
        """
        Insert single event at the specified position.

        :param idx: index to add the new event at
        :param kwargs: arguments compatible with Event's constructor
        :return: created event
        """
        subtitle = Event(**kwargs)
        self.insert(len(self) if idx is None else idx, [subtitle])
        return subtitle

    def insert(self, idx: int, items: T.List[Event]) -> None:
        """
        Insert events at the specified position.

        :param idx: index to add the new events at
        :param items: events to add
        """
        for item in items:
            assert item.event_list is None, 'Event belongs to another list'
            item.event_list = self
        super().insert(idx, items)

    def remove(self, idx: int, count: int) -> None:
        """
        Remove events at the specified position.

        :param idx: where to start the removal
        :param count: how many elements to remove
        """
        for item in self._items[idx:idx + count]:
            item.event_list = None
        super().remove(idx, count)
