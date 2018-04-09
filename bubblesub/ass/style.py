from collections import namedtuple

import bubblesub.ass
import bubblesub.model
import bubblesub.util


Color = namedtuple('Color', ['red', 'green', 'blue', 'alpha'])


class Style(bubblesub.model.ObservableObject):
    def __init__(
            self,
            name: str,
            font_name: str = 'Arial',
            font_size: int = 20,
            primary_color: Color = Color(255, 255, 255, 0),
            secondary_color: Color = Color(255, 0, 0, 0),
            outline_color: Color = Color(32, 32, 32, 0),
            back_color: Color = Color(32, 32, 32, 127),
            bold: bool = True,
            italic: bool = False,
            underline: bool = False,
            strike_out: bool = False,
            scale_x: int = 100,
            scale_y: int = 100,
            spacing: int = 0,
            angle: int = 0,
            border_style: int = 1,
            outline: int = 3,
            shadow: int = 0,
            alignment: int = 2,
            margin_left: int = 20,
            margin_right: int = 20,
            margin_vertical: int = 20,
            encoding: int = 1,
    ) -> None:
        self._old_name = None
        self.style_list = None

        self.name = name
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

    def _before_change(self):
        self._old_name = self.name
        if self.style_list is not None:
            self.style_list.item_about_to_change.emit(self.name)

    def _after_change(self):
        if self.style_list is not None:
            self.style_list.item_changed.emit(self._old_name)

    def __getstate__(self):
        ret = self.__dict__.copy()
        key = id(ret['style_list'])
        bubblesub.util.ref_dict[key] = ret['style_list']
        ret['style_list'] = key
        return ret

    def __setstate__(self, state):
        state['style_list'] = bubblesub.util.ref_dict[state['style_list']]
        self.__dict__ = state

    def __copy__(self):
        ret = type(self)(name=self.name)
        ret.__dict__.update(self.__dict__)
        ret.__dict__['style_list'] = None
        return ret


class StyleList(bubblesub.model.ObservableList):
    def insert_one(self, name, index=None, **kwargs):
        style = Style(name=name, **kwargs)
        self.insert(len(self) if index is None else index, [style])
        return style

    def insert(self, idx, items):
        for item in items:
            assert item.style_list is None, 'Style belongs to another list'
            item.style_list = self
        return super().insert(idx, items)

    def get_by_name(self, name):
        for style in self:
            if style.name == name:
                return style
        return None
