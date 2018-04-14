import typing as T

import bubblesub.ass
import bubblesub.model
import bubblesub.util


class Event(bubblesub.model.ObservableObject):
    def __init__(
            self,
            start: int,
            end: int,
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

    def set_event_list(self, events: 'EventList') -> None:
        self.event_list = events

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        self._text = value.replace('\n', '\\N')

    @property
    def note(self) -> str:
        return self._note

    @note.setter
    def note(self, value: str) -> None:
        self._note = value.replace('\n', '\\N')

    @property
    def duration(self) -> int:
        return self.end - self.start

    @property
    def index(self) -> T.Optional[int]:
        # XXX: meh
        if self.event_list is not None:
            return self.event_list.index(self)
        return None

    @property
    def number(self) -> T.Optional[int]:
        index = self.index
        if index is None:
            return None
        return index + 1

    @property
    def prev(self) -> T.Optional['Event']:
        index = self.index
        if index is None:
            return None
        assert self.event_list is not None
        return self.event_list.get(index - 1, None)

    @property
    def next(self) -> T.Optional['Event']:
        index = self.index
        if index is None:
            return None
        assert self.event_list is not None
        return self.event_list.get(index + 1, None)

    def _before_change(self) -> None:
        index = self.index
        if index is not None and self.event_list is not None:
            self.event_list.item_about_to_change.emit(index)

    def _after_change(self) -> None:
        index = self.index
        if index is not None and self.event_list is not None:
            self.event_list.item_changed.emit(index)

    def __getstate__(self) -> T.Any:
        ret = self.__dict__.copy()
        key = id(ret['event_list'])
        bubblesub.util.ref_dict[key] = ret['event_list']
        ret['event_list'] = key
        return ret

    def __setstate__(self, state: T.Any) -> None:
        state['event_list'] = bubblesub.util.ref_dict[state['event_list']]
        self.__dict__.update(state)

    def __copy__(self) -> 'Event':
        ret = type(self)(start=self.start, end=self.end)
        ret.__dict__.update(self.__dict__)
        ret.__dict__['event_list'] = None
        return ret


class EventList(bubblesub.model.ObservableList[Event]):
    def insert_one(
            self,
            idx: T.Optional[int] = None,
            **kwargs: T.Any
    ) -> Event:
        subtitle = Event(**kwargs)
        self.insert(len(self) if idx is None else idx, [subtitle])
        return subtitle

    def insert(self, idx: int, items: T.List[Event]) -> None:
        for item in items:
            assert item.event_list is None, 'Event belongs to another list'
            item.event_list = self
        super().insert(idx, items)
