from collections import namedtuple

import bubblesub.ass
import bubblesub.model
import bubblesub.util


Color = namedtuple('Color', ['red', 'green', 'blue', 'alpha'])


class Style(bubblesub.model.ObservableObject):
    prop = {
        'name': bubblesub.model.ObservableObject.REQUIRED,
        'font_name': 'Arial',
        'font_size': 20,
        'primary_color': Color(255, 255, 255, 0),
        'secondary_color': Color(255, 0, 0, 0),
        'outline_color': Color(32, 32, 32, 0),
        'back_color': Color(32, 32, 32, 127),
        'bold': True,
        'italic': False,
        'underline': False,
        'strike_out': False,
        'scale_x': 100,
        'scale_y': 100,
        'spacing': 0,
        'angle': 0,
        'border_style': 1,
        'outline': 3,
        'shadow': 0,
        'alignment': 2,
        'margin_left': 20,
        'margin_right': 20,
        'margin_vertical': 20,
        'encoding': 1,
    }

    def __init__(self, styles, **kwargs):
        super().__init__(**kwargs)
        self._styles = styles
        self._old_name = None

    def _before_change(self):
        self._old_name = self.name
        self._styles.item_about_to_change.emit(self.name)

    def _after_change(self):
        self._styles.item_changed.emit(self._old_name)


class StyleList(bubblesub.model.ListModel):
    def insert_one(self, name, index=None, **kwargs):
        style = Style(styles=self, name=name, **kwargs)
        self.insert(len(self) if index is None else index, [style])
        return style

    def get_by_name(self, name):
        for style in self:
            if style.name == name:
                return style
        return None
