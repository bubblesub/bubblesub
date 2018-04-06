import bubblesub.ass
import bubblesub.model
import bubblesub.util


class Event(bubblesub.model.ObservableObject):
    prop = {
        'start': bubblesub.model.ObservableObject.REQUIRED,
        'end': bubblesub.model.ObservableObject.REQUIRED,
        'style': 'Default',
        'actor': '',
        'text': '',
        'note': '',
        'effect': '',
        'layer': 0,
        'margin_left': 0,
        'margin_right': 0,
        'margin_vertical': 0,
        'is_comment': False,
    }

    def __init__(self, subtitles, **kwargs):
        super().__init__(**kwargs)
        self._subtitles = subtitles

    @property
    def duration(self):
        return self.end - self.start

    @property
    def id(self):
        # XXX: meh
        for i, item in enumerate(self._subtitles):
            if item == self:
                return i
        return None

    @property
    def number(self):
        id_ = self.id
        if id_ is None:
            return None
        return id_ + 1

    @property
    def prev(self):
        id_ = self.id
        if id_ is None:
            return None
        return self._subtitles.get(id_ - 1, None)

    @property
    def next(self):
        id_ = self.id
        if id_ is None:
            return None
        return self._subtitles.get(id_ + 1, None)

    def _before_change(self):
        id_ = self.id
        if id_ is not None:
            self._subtitles.item_about_to_change.emit(id_)

    def _after_change(self):
        id_ = self.id
        if id_ is not None:
            self._subtitles.item_changed.emit(id_)


class EventList(bubblesub.model.ListModel):
    def insert_one(self, idx=None, **kwargs):
        subtitle = Event(self, **kwargs)
        self.insert(len(self) if idx is None else idx, [subtitle])
        return subtitle
