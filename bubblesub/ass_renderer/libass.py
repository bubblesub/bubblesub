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
from collections.abc import Callable, Iterator
from typing import Any, Optional

import ass_parser
from ass_parser import write_ass

_libass_path = ctypes.util.find_library("ass") or ctypes.util.find_library(
    "libass"
)
assert _libass_path, "libass was not found"
_libass = ctypes.cdll.LoadLibrary(_libass_path)

_libc_path = ctypes.util.find_library("c") or ctypes.util.find_library(
    "msvcrt"
)
assert _libc_path, "libc was not found"
_libc = ctypes.cdll.LoadLibrary(_libc_path)


def _encode_str(text: Optional[str]) -> Optional[bytes]:
    return None if text is None else text.encode("utf-8")


def _color_to_int(color: tuple[int, int, int, int]) -> int:
    red, green, blue, alpha = color
    return alpha | (blue << 8) | (green << 16) | (red << 24)


class AssImageSequence:
    def __init__(self, renderer: "AssRenderer", head_ptr: Any) -> None:
        self.renderer = renderer
        self.head_ptr = head_ptr

    def __iter__(self) -> Iterator["AssImage"]:
        cur = self.head_ptr
        while cur:
            yield cur.contents
            cur = cur.contents.next_ptr


class AssImage(ctypes.Structure):
    TYPE_CHARACTER = 0
    TYPE_OUTLINE = 1
    TYPE_SHADOW = 2

    @property
    def rgba(self) -> tuple[int, int, int, int]:
        color = self.color
        alpha = color & 0xFF
        blue = (color >> 8) & 0xFF
        green = (color >> 16) & 0xFF
        red = (color >> 24) & 0xFF
        return (red, green, blue, alpha)

    def __getitem__(self, loc: tuple[int, int]) -> int:
        x, y = loc
        return ord(self.bitmap[y * self.stride + x])


AssImage._fields_ = [
    ("w", ctypes.c_int),
    ("h", ctypes.c_int),
    ("stride", ctypes.c_int),
    ("bitmap", ctypes.POINTER(ctypes.c_char)),
    ("color", ctypes.c_uint32),
    ("dst_x", ctypes.c_int),
    ("dst_y", ctypes.c_int),
    ("next_ptr", ctypes.POINTER(AssImage)),
    ("type", ctypes.c_int),
]


def _make_libass_setter(
    name: str, types: list[Any]
) -> Callable[[Any, Any], Any]:
    fun = _libass[name]
    fun.argtypes = [ctypes.c_void_p] + types

    def setter(self: Any, v: Any) -> None:
        if len(types) == 1:
            fun(ctypes.byref(self), v)
        else:
            fun(ctypes.byref(self), *v)
        self._internal_fields[name] = v

    return setter


def _make_libass_property(name: str, types: list[Any]) -> property:
    def getter(self: Any) -> Any:
        return self._internal_fields.get(name)

    return property(getter, _make_libass_setter(name, types))


class AssLibrary(ctypes.Structure):
    fonts_dir = _make_libass_property("ass_set_fonts_dir", [ctypes.c_char_p])
    extract_fonts = _make_libass_property(
        "ass_set_extract_fonts", [ctypes.c_int]
    )

    def __new__(cls) -> Any:
        return _libass.ass_library_init().contents

    def __init__(self) -> None:
        super().__init__()
        self._internal_fields: Any = {}

        if not ctypes.byref(self):
            raise RuntimeError("could not initialize libass")

        self.extract_fonts = False

    def __del__(self) -> None:
        _libass.ass_library_done(ctypes.byref(self))

    def make_renderer(self) -> "AssRenderer":
        renderer = _libass.ass_renderer_init(ctypes.byref(self)).contents
        renderer._after_init(self)
        return renderer

    def make_track(self) -> "AssTrack":
        track = _libass.ass_new_track(ctypes.byref(self)).contents
        track._after_init(self)
        return track


class AssRenderer(ctypes.Structure):
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

    def _after_init(self, library: "AssLibrary") -> None:
        self._library = library
        self._fonts_set = False
        self._internal_fields: Any = {}

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
        default_font: Optional[str] = None,
        default_family: Optional[str] = None,
        fontconfig_config: Optional[str] = None,
    ) -> None:
        _libass.ass_set_fonts(
            ctypes.byref(self),
            _encode_str(default_font),
            _encode_str(default_family),
            AssRenderer.FONTPROVIDER_AUTODETECT,
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

    def render_frame(self, track: "AssTrack", now: int) -> AssImageSequence:
        if not self._fonts_set:
            raise RuntimeError("set_fonts before rendering")
        head = _libass.ass_render_frame(
            ctypes.byref(self),
            ctypes.byref(track),
            now,
            ctypes.POINTER(ctypes.c_int)(),
        )
        return AssImageSequence(self, head)


class AssStyle(ctypes.Structure):
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
        ("justify", ctypes.c_int),
    ]

    def _after_init(self, track: "AssTrack") -> None:
        self._track = track


class AssEvent(ctypes.Structure):
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

    def _after_init(self, track: "AssTrack") -> None:
        self._track = track


class AssTrack(ctypes.Structure):
    TYPE_UNKNOWN = 0
    TYPE_ASS = 1
    TYPE_SSA = 2

    _fields_ = [
        ("n_styles", ctypes.c_int),
        ("max_styles", ctypes.c_int),
        ("n_events", ctypes.c_int),
        ("max_events", ctypes.c_int),
        ("styles_arr", ctypes.POINTER(AssStyle)),
        ("events_arr", ctypes.POINTER(AssEvent)),
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
        ("library", ctypes.POINTER(AssLibrary)),
        ("parser_priv", ctypes.c_void_p),
    ]

    def _after_init(self, library: AssLibrary) -> None:
        self._library = library

    def __del__(self) -> None:
        _libass.ass_free_track(ctypes.byref(self))

    def load_ass_file(
        self, ass_file: ass_parser.AssFile, video_resolution: tuple[int, int]
    ) -> None:
        self.type = AssTrack.TYPE_ASS

        text = write_ass(ass_file).encode("utf-8")
        _libass.ass_process_data(ctypes.byref(self), text, len(text))

        self.play_res_x = int(
            ass_file.script_info.get("PlayResX") or video_resolution[0]
        )
        self.play_res_y = int(
            ass_file.script_info.get("PlayResY") or video_resolution[1]
        )
        self.wrap_style = int(ass_file.script_info.get("WrapStyle") or 1)
        self.scaled_border_and_shadow = (
            ass_file.script_info.get("ScaledBorderAndShadow", "yes") == "yes"
        )


_libc.free.argtypes = [ctypes.c_void_p]
_libass.ass_library_init.restype = ctypes.POINTER(AssLibrary)
_libass.ass_library_done.argtypes = [ctypes.POINTER(AssLibrary)]
_libass.ass_renderer_init.argtypes = [ctypes.POINTER(AssLibrary)]
_libass.ass_renderer_init.restype = ctypes.POINTER(AssRenderer)
_libass.ass_renderer_done.argtypes = [ctypes.POINTER(AssRenderer)]
_libass.ass_new_track.argtypes = [ctypes.POINTER(AssLibrary)]
_libass.ass_new_track.restype = ctypes.POINTER(AssTrack)
_libass.ass_process_data.restype = None
_libass.ass_process_data.argtypes = [
    ctypes.POINTER(AssTrack),
    ctypes.c_char_p,
    ctypes.c_int,
]
_libass.ass_set_style_overrides.argtypes = [
    ctypes.POINTER(AssLibrary),
    ctypes.POINTER(ctypes.c_char_p),
]
_libass.ass_set_fonts.argtypes = [
    ctypes.POINTER(AssRenderer),
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
]
_libass.ass_fonts_update.argtypes = [ctypes.POINTER(AssRenderer)]
_libass.ass_render_frame.argtypes = [
    ctypes.POINTER(AssRenderer),
    ctypes.POINTER(AssTrack),
    ctypes.c_longlong,
    ctypes.POINTER(ctypes.c_int),
]
_libass.ass_render_frame.restype = ctypes.POINTER(AssImage)
_libass.ass_read_memory.argtypes = [
    ctypes.POINTER(AssLibrary),
    ctypes.c_char_p,
    ctypes.c_size_t,
    ctypes.c_char_p,
]
_libass.ass_read_memory.restype = ctypes.POINTER(AssTrack)
_libass.ass_alloc_style.argtypes = [ctypes.POINTER(AssTrack)]
_libass.ass_alloc_style.restype = ctypes.c_int
_libass.ass_alloc_event.argtypes = [ctypes.POINTER(AssTrack)]
_libass.ass_alloc_event.restype = ctypes.c_int
