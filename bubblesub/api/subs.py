import bubblesub.util


class Subtitle(bubblesub.util.ObservableObject):
    start = bubblesub.util.ObservableProperty('start')
    end = bubblesub.util.ObservableProperty('end')
    style = bubblesub.util.ObservableProperty('style')
    actor = bubblesub.util.ObservableProperty('actor')
    text = bubblesub.util.ObservableProperty('text')

    def __init__(self, subtitles, start, end, style, actor='', text=''):
        super().__init__()
        self._subtitles = subtitles
        self.begin_update()
        self.start = start
        self.end = end
        self.style = style
        self.actor = actor
        self.text = text
        self.end_update()

    @property
    def duration(self):
        return self.end - self.start

    @property
    def number(self):
        for i, item in enumerate(self._subtitles):
            if item == self:
                return i
        return None

    def _changed(self):
        self._subtitles.item_changed.emit(self.number)


class SubtitleList(bubblesub.util.ListModel):
    def insert_one(self, idx, **kwargs):
        self.insert(idx, [Subtitle(self, **kwargs)])
