# bubblesub - ASS subtitle editor
# Copyright (C) 2018 Marcin Kurczewski
# Copyright (c) 2014 Tony Young
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

# pylint: disable=attribute-defined-outside-init
# pylint: disable=invalid-name
# pylint: disable=protected-access

import ctypes
import ctypes.util
import typing as T

import numpy as np
import PIL.Image

from bubblesub.ass.event import Event, EventList
from bubblesub.ass.info import Metadata
from bubblesub.ass.style import Style, StyleList

_libass = ctypes.cdll.LoadLibrary(ctypes.util.find_library("ass"))
_libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("c"))


def _encode_str(text: T.Optional[str]) -> T.Optional[bytes]:
    return None if text is None else text.encode("utf-8")


def _color_to_int(color: T.Tuple[int, int, int, int]) -> int:
    red, green, blue, alpha = color
    return alpha | (blue << 8) | (green << 16) | (red << 24)


class _AssImageSequence:
    def __init__(self, renderer: "_AssRenderer", head_ptr: T.Any) -> None:
        self.renderer = renderer
        self.head_ptr = head_ptr

    def __iter__(self) -> T.Iterator["_AssImage"]:
        cur = self.head_ptr
        while cur:
            yield cur.contents
            cur = cur.contents.next_ptr


class _AssImage(ctypes.Structure):
    TYPE_CHARACTER = 0
    TYPE_OUTLINE = 1
    TYPE_SHADOW = 2

    @property
    def rgba(self) -> T.Tuple[int, int, int, int]:
        color = self.color
        alpha = color & 0xFF
        blue = (color >> 8) & 0xFF
        green = (color >> 16) & 0xFF
        red = (color >> 24) & 0xFF
        return (red, green, blue, alpha)

    def __getitem__(self, loc: T.Tuple[int, int]) -> int:
        x, y = loc
        return ord(self.bitmap[y * self.stride + x])


_AssImage._fields_ = [
    ("w", ctypes.c_int),
    ("h", ctypes.c_int),
    ("stride", ctypes.c_int),
    ("bitmap", ctypes.POINTER(ctypes.c_char)),
    ("color", ctypes.c_uint32),
    ("dst_x", ctypes.c_int),
    ("dst_y", ctypes.c_int),
    ("next_ptr", ctypes.POINTER(_AssImage)),
    ("type", ctypes.c_int),
]


def _make_libass_setter(
    name: str, types: T.List
) -> T.Callable[[T.Any], T.Any]:
    fun = _libass[name]
    fun.argtypes = [ctypes.c_void_p] + types

    def setter(self: T.Any, v: T.Any) -> None:
        if len(types) == 1:
            fun(ctypes.byref(self), v)
        else:
            fun(ctypes.byref(self), *v)
        self._internal_fields[name] = v

    return setter


def _make_libass_property(name: str, types: T.List) -> property:
    def getter(self: T.Any) -> T.Any:
        return self._internal_fields.get(name)

    return property(getter, _make_libass_setter(name, types))


class _AssContext(ctypes.Structure):
    fonts_dir = _make_libass_property("ass_set_fonts_dir", [ctypes.c_char_p])
    extract_fonts = _make_libass_property(
        "ass_set_extract_fonts", [ctypes.c_int]
    )

    def __new__(cls) -> T.Any:
        return _libass.ass_library_init().contents

    def __init__(self) -> None:
        super().__init__()
        self._internal_fields: T.Any = {}

        if not ctypes.byref(self):
            raise RuntimeError("could not initialize libass")

        self.extract_fonts = False

    def __del__(self) -> None:
        _libass.ass_library_done(ctypes.byref(self))

    def make_renderer(self) -> "_AssRenderer":
        renderer = _libass.ass_renderer_init(ctypes.byref(self)).contents
        renderer._after_init(self)
        return renderer

    def make_track(self) -> "_AssTrack":
        track = _libass.ass_new_track(ctypes.byref(self)).contents
        track._after_init(self)
        return track


class _AssRenderer(ctypes.Structure):
    SHAPING_SIMPLE = 0
    SHAPING_COMPLEX = 1

    HINTING_NONE = 0
    HINTING_LIGHT = 1
    HINTING_NORMAL = 2
    HINTING_NATIVE = 3

    FONTPROVIDER_AUTODETECT = 1

    frame_size = _make_libass_property(
        "ass_set_frame_size", [ctypes.c_int, ctypes.c_int]
    )
    storage_size = _make_libass_property(
        "ass_set_storage_size", [ctypes.c_int, ctypes.c_int]
    )
    shaper = _make_libass_property("ass_set_shaper", [ctypes.c_int])
    margins = _make_libass_property(
        "ass_set_margins",
        [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int],
    )
    use_margins = _make_libass_property("ass_set_use_margins", [ctypes.c_int])
    pixel_aspect = _make_libass_property(
        "ass_set_pixel_aspect", [ctypes.c_double]
    )
    aspect_ratio = _make_libass_property(
        "ass_set_aspect_ratio", [ctypes.c_double, ctypes.c_double]
    )
    font_scale = _make_libass_property("ass_set_font_scale", [ctypes.c_double])
    hinting = _make_libass_property("ass_set_hinting", [ctypes.c_int])
    line_spacing = _make_libass_property(
        "ass_set_line_spacing", [ctypes.c_double]
    )
    line_position = _make_libass_property(
        "ass_set_line_position", [ctypes.c_double]
    )

    def _after_init(self, ctx: "_AssContext") -> None:
        self._ctx = ctx
        self._fonts_set = False
        self._internal_fields: T.Any = {}

        self.frame_size = (640, 480)
        self.storage_size = (640, 480)
        self.margins = (0, 0, 0, 0)
        self.use_margins = True
        self.font_scale = 1
        self.line_spacing = 0
        self.pixel_aspect = 1.0

    def __del__(self) -> None:
        _libass.ass_renderer_done(ctypes.byref(self))

    def set_fonts(
        self,
        default_font: T.Optional[str] = None,
        default_family: T.Optional[str] = None,
        fontconfig_config: T.Optional[str] = None,
    ) -> None:
        _libass.ass_set_fonts(
            ctypes.byref(self),
            _encode_str(default_font),
            _encode_str(default_family),
            _AssRenderer.FONTPROVIDER_AUTODETECT,
            _encode_str(fontconfig_config),
            True,  # update font config now?
        )
        self._fonts_set = True

    def update_fonts(self) -> None:
        if not self._fonts_set:
            raise RuntimeError("set_fonts before updating them")
        _libass.ass_fonts_update(ctypes.byref(self))

    set_cache_limits = _make_libass_setter(
        "ass_set_cache_limits", [ctypes.c_int, ctypes.c_int]
    )

    def render_frame(self, track: "_AssTrack", now: int) -> _AssImageSequence:
        if not self._fonts_set:
            raise RuntimeError("set_fonts before rendering")
        head = _libass.ass_render_frame(
            ctypes.byref(self),
            ctypes.byref(track),
            now,
            ctypes.POINTER(ctypes.c_int)(),
        )
        return _AssImageSequence(self, head)


class _AssStyle(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char_p),
        ("fontname", ctypes.c_char_p),
        ("fontsize", ctypes.c_double),
        ("primary_color", ctypes.c_uint32),
        ("secondary_color", ctypes.c_uint32),
        ("outline_color", ctypes.c_uint32),
        ("back_color", ctypes.c_uint32),
        ("bold", ctypes.c_int),
        ("italic", ctypes.c_int),
        ("underline", ctypes.c_int),
        ("strike_out", ctypes.c_int),
        ("scale_x", ctypes.c_double),
        ("scale_y", ctypes.c_double),
        ("spacing", ctypes.c_double),
        ("angle", ctypes.c_double),
        ("border_style", ctypes.c_int),
        ("outline", ctypes.c_double),
        ("shadow", ctypes.c_double),
        ("alignment", ctypes.c_int),
        ("margin_l", ctypes.c_int),
        ("margin_r", ctypes.c_int),
        ("margin_v", ctypes.c_int),
        ("encoding", ctypes.c_int),
        ("treat_fontname_as_pattern", ctypes.c_int),
        ("blur", ctypes.c_double),
        ("jsutify", ctypes.c_int),
    ]

    @staticmethod
    def _numpad_align(val: int) -> int:
        v = (val - 1) // 3
        if v != 0:
            v = 3 - v
        res = ((val - 1) % 3) + 1
        res += v * 4
        return res

    def _after_init(self, track: "_AssTrack") -> None:
        self._track = track

    def populate(self, style: Style) -> None:
        self.name = _encode_str(style.name)
        self.fontname = _encode_str(style.font_name)
        self.fontsize = style.font_size
        self.primary_color = _color_to_int(style.primary_color)
        self.secondary_color = _color_to_int(style.secondary_color)
        self.outline_color = _color_to_int(style.outline_color)
        self.back_color = _color_to_int(style.back_color)
        self.bold = style.bold
        self.italic = style.italic
        self.underline = style.underline
        self.strike_out = style.strike_out
        self.scale_x = style.scale_x / 100.0
        self.scale_y = style.scale_y / 100.0
        self.spacing = style.spacing
        self.angle = style.angle
        self.border_style = style.border_style
        self.outline = style.outline
        self.shadow = style.shadow
        self.alignment = _AssStyle._numpad_align(style.alignment)
        self.margin_l = style.margin_left
        self.margin_r = style.margin_right
        self.margin_v = style.margin_vertical
        self.encoding = style.encoding


class _AssEvent(ctypes.Structure):
    _fields_ = [
        ("start_ms", ctypes.c_longlong),
        ("duration_ms", ctypes.c_longlong),
        ("read_order", ctypes.c_int),
        ("layer", ctypes.c_int),
        ("style_id", ctypes.c_int),
        ("name", ctypes.c_char_p),
        ("margin_l", ctypes.c_int),
        ("margin_r", ctypes.c_int),
        ("margin_v", ctypes.c_int),
        ("effect", ctypes.c_char_p),
        ("text", ctypes.c_char_p),
        ("render_priv", ctypes.c_void_p),
    ]

    def _after_init(self, track: "_AssTrack") -> None:
        self._track = track

    def _style_name_to_style_id(self, name: str) -> int:
        for i, style in enumerate(self._track.styles):
            if style.name is not None and style.name.decode("utf-8") == name:
                return i
        return -1

    def populate(self, event: Event) -> None:
        self.start_ms = int(event.start)
        self.duration_ms = int(event.end - event.start)
        self.layer = event.layer
        self.style_id = self._style_name_to_style_id(event.style)
        self.name = _encode_str(event.actor)
        self.margin_l = event.margin_left
        self.margin_r = event.margin_right
        self.margin_v = event.margin_vertical
        self.effect = _encode_str(event.effect)
        self.text = _encode_str(event.text)


class _AssTrack(ctypes.Structure):
    TYPE_UNKNOWN = 0
    TYPE_ASS = 1
    TYPE_SSA = 2

    _fields_ = [
        ("n_styles", ctypes.c_int),
        ("max_styles", ctypes.c_int),
        ("n_events", ctypes.c_int),
        ("max_events", ctypes.c_int),
        ("styles_arr", ctypes.POINTER(_AssStyle)),
        ("events_arr", ctypes.POINTER(_AssEvent)),
        ("style_format", ctypes.c_char_p),
        ("event_format", ctypes.c_char_p),
        ("track_type", ctypes.c_int),
        ("play_res_x", ctypes.c_int),
        ("play_res_y", ctypes.c_int),
        ("timer", ctypes.c_double),
        ("wrap_style", ctypes.c_int),
        ("scaled_border_and_shadow", ctypes.c_int),
        ("kerning", ctypes.c_int),
        ("language", ctypes.c_char_p),
        ("ycbcr_matrix", ctypes.c_int),
        ("default_style", ctypes.c_int),
        ("name", ctypes.c_char_p),
        ("library", ctypes.POINTER(_AssContext)),
        ("parser_priv", ctypes.c_void_p),
    ]

    def _after_init(self, ctx: _AssContext) -> None:
        self._ctx = ctx

    @property
    def styles(self) -> T.List[_AssStyle]:
        if self.n_styles == 0:
            return []
        return ctypes.cast(
            self.styles_arr, ctypes.POINTER(_AssStyle * self.n_styles)
        ).contents

    @property
    def events(self) -> T.List[_AssEvent]:
        if self.n_events == 0:
            return []
        return ctypes.cast(
            self.events_arr, ctypes.POINTER(_AssEvent * self.n_events)
        ).contents

    def make_style(self) -> _AssStyle:
        style = self.styles_arr[_libass.ass_alloc_style(ctypes.byref(self))]
        style._after_init(self)
        return style

    def make_event(self) -> _AssEvent:
        event = self.events_arr[_libass.ass_alloc_event(ctypes.byref(self))]
        event._after_init(self)
        return event

    def __del__(self) -> None:
        # XXX: we can't use ass_free_track because it assumes we've allocated
        #      our strings in the heap (wat), so we just free them with libc.
        _libc.free(self.styles_arr)
        _libc.free(self.events_arr)
        _libc.free(ctypes.byref(self))

    def populate(self, style_list: StyleList, event_list: EventList) -> None:
        self.type = _AssTrack.TYPE_ASS

        self.style_format = _encode_str(
            "Name, Fontname, Fontsize, "
            "PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, "
            "Angle, BorderStyle, Outline, Shadow, Alignment, "
            "MarginL, MarginR, MarginV, Encoding"
        )

        self.event_format = _encode_str(
            "Layer, Start, End, Style, Name, "
            "MarginL, MarginR, MarginV, Effect, Text"
        )

        for source_style in style_list:
            style = self.make_style()
            style.populate(source_style)

        for source_event in event_list:
            if source_event.is_comment:
                continue
            event = self.make_event()
            event.populate(source_event)


_libc.free.argtypes = [ctypes.c_void_p]
_libass.ass_library_init.restype = ctypes.POINTER(_AssContext)
_libass.ass_library_done.argtypes = [ctypes.POINTER(_AssContext)]
_libass.ass_renderer_init.argtypes = [ctypes.POINTER(_AssContext)]
_libass.ass_renderer_init.restype = ctypes.POINTER(_AssRenderer)
_libass.ass_renderer_done.argtypes = [ctypes.POINTER(_AssRenderer)]
_libass.ass_new_track.argtypes = [ctypes.POINTER(_AssContext)]
_libass.ass_new_track.restype = ctypes.POINTER(_AssTrack)
_libass.ass_set_style_overrides.argtypes = [
    ctypes.POINTER(_AssContext),
    ctypes.POINTER(ctypes.c_char_p),
]
_libass.ass_set_fonts.argtypes = [
    ctypes.POINTER(_AssRenderer),
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
]
_libass.ass_fonts_update.argtypes = [ctypes.POINTER(_AssRenderer)]
_libass.ass_render_frame.argtypes = [
    ctypes.POINTER(_AssRenderer),
    ctypes.POINTER(_AssTrack),
    ctypes.c_longlong,
    ctypes.POINTER(ctypes.c_int),
]
_libass.ass_render_frame.restype = ctypes.POINTER(_AssImage)
_libass.ass_read_memory.argtypes = [
    ctypes.POINTER(_AssContext),
    ctypes.c_char_p,
    ctypes.c_size_t,
    ctypes.c_char_p,
]
_libass.ass_read_memory.restype = ctypes.POINTER(_AssTrack)
_libass.ass_alloc_style.argtypes = [ctypes.POINTER(_AssTrack)]
_libass.ass_alloc_style.restype = ctypes.c_int
_libass.ass_alloc_event.argtypes = [ctypes.POINTER(_AssTrack)]
_libass.ass_alloc_event.restype = ctypes.c_int


class AssRenderer:
    """Public renderer facade"""

    def __init__(self) -> None:
        self._ctx = _AssContext()
        self._renderer = self._ctx.make_renderer()
        self._renderer.set_fonts()
        self._track: T.Optional["_AssTrack"] = None
        self.style_list: T.Optional[StyleList] = None
        self.event_list: T.Optional[EventList] = None
        self.info: T.Optional[Metadata] = None
        self.video_resolution: T.Optional[T.Tuple[int, int]] = None

    def set_source(
        self,
        style_list: StyleList,
        event_list: EventList,
        info: Metadata,
        video_resolution: T.Tuple[int, int],
    ) -> None:
        self.style_list = style_list
        self.event_list = event_list
        self.info = info
        self.video_resolution = video_resolution

        self._track = self._ctx.make_track()
        self._track.populate(style_list, event_list)

        self._track.play_res_x = int(info.get("PlayResX", video_resolution[0]))
        self._track.play_res_y = int(info.get("PlayResY", video_resolution[1]))
        self._track.wrap_style = int(info.get("WrapStyle", 1))
        self._track.scaled_border_and_shadow = (
            info.get("ScaledBorderAndShadow", "yes") == "yes"
        )

        self._renderer.frame_size = (
            self._track.play_res_x,
            self._track.play_res_y,
        )
        self._renderer.storage_size = video_resolution
        self._renderer.pixel_aspect = 1.0

    def render(self, time: int) -> PIL.Image:
        if self._track is None:
            raise ValueError("need source to render")

        if any(dim <= 0 for dim in self._renderer.frame_size):
            raise ValueError("resolution needs to be a positive integer")

        image_data = np.zeros(
            (self._renderer.frame_size[1], self._renderer.frame_size[0], 4),
            dtype=np.uint8,
        )

        for layer in self.render_raw(time):
            red, green, blue, alpha = layer.rgba

            mask_data = np.lib.stride_tricks.as_strided(
                np.frombuffer(
                    (ctypes.c_uint8 * (layer.stride * layer.h)).from_address(
                        ctypes.addressof(layer.bitmap.contents)
                    ),
                    dtype=np.uint8,
                ),
                (layer.h, layer.w),
                (layer.stride, 1),
            )

            overlay = np.zeros((layer.h, layer.w, 4), dtype=np.uint8)
            overlay[..., :3] = (red, green, blue)
            overlay[..., 3] = mask_data
            overlay[..., 3] = (overlay[..., 3] * (1.0 - alpha / 255.0)).astype(
                np.uint8
            )

            fragment = image_data[
                layer.dst_y : layer.dst_y + layer.h,
                layer.dst_x : layer.dst_x + layer.w,
            ]

            src_color = overlay[..., :3].astype(np.float32) / 255.0
            src_alpha = overlay[..., 3].astype(np.float32) / 255.0
            dst_color = fragment[..., :3].astype(np.float32) / 255.0
            dst_alpha = fragment[..., 3].astype(np.float32) / 255.0

            out_alpha = src_alpha + dst_alpha * (1.0 - src_alpha)
            out_color = (
                src_color * src_alpha[..., None]
                + dst_color
                * dst_alpha[..., None]
                * (1.0 - src_alpha[..., None])
            ) / out_alpha[..., None]

            fragment[..., :3] = out_color * 255
            fragment[..., 3] = out_alpha * 255

        return PIL.Image.fromarray(image_data)

    def render_raw(self, time: int) -> _AssImageSequence:
        if self._track is None:
            raise ValueError("need source to render")

        return self._renderer.render_frame(self._track, now=time)
