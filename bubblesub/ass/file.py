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
        self.meta: T.Dict[str, str] = OrderedDict()
        self.info: T.Dict[str, str] = OrderedDict()
