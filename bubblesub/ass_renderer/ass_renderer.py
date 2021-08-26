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

"""Module for drawing ASS structures to numpy bitmaps."""

import ctypes
import fractions
from typing import Optional, Union

import numpy as np
import PIL.Image
from ass_parser import AssEventList, AssScriptInfo, AssStyleList

from bubblesub.ass_renderer import libass


class AssRenderer:
    """Public renderer facade."""

    def __init__(self) -> None:
        """Initialize self."""
        self._ctx = libass.AssContext()
        self._renderer = self._ctx.make_renderer()
        self._renderer.set_fonts()
        self._track: Optional[libass.AssTrack] = None
        self.style_list: Optional[AssStyleList] = None
        self.event_list: Optional[AssEventList] = None
        self.script_info: Optional[AssScriptInfo] = None
        self.video_resolution: Optional[tuple[int, int]] = None

    def set_source(
        self,
        style_list: AssStyleList,
        event_list: AssEventList,
        script_info: AssScriptInfo,
        video_resolution: tuple[int, int],
    ) -> None:
        """Set source ASS data.

        :param style_list: list of ASS styles
        :param event_list: list of ASS events
        :param script_info: ASS script info
        :param video_resolution: (width, height) tuple
        """
        self.style_list = style_list
        self.event_list = event_list
        self.script_info = script_info
        self.video_resolution = video_resolution

        self._track = self._ctx.make_track()
        self._track.populate(style_list, event_list)

        self._track.play_res_x = int(
            script_info.get("PlayResX") or video_resolution[0]
        )
        self._track.play_res_y = int(
            script_info.get("PlayResY") or video_resolution[1]
        )
        self._track.wrap_style = int(script_info.get("WrapStyle") or 1)
        self._track.scaled_border_and_shadow = (
            script_info.get("ScaledBorderAndShadow", "yes") == "yes"
        )

        self._renderer.storage_size = (
            self._track.play_res_x,
            self._track.play_res_y,
        )
        self._renderer.frame_size = video_resolution
        self._renderer.pixel_aspect = 1.0

    def render(
        self, time: int, aspect_ratio: Union[float, fractions.Fraction]
    ) -> PIL.Image:
        """Render the ASS data to a PIL.Image bitmap.

        :param time: PTS to render at
        :param aspect_ratio: pixel aspect ratio to use
        :return: PIL image
        """
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

        ret = PIL.Image.fromarray(image_data)
        ret = ret.resize(
            (int(ret.width * aspect_ratio), ret.height), PIL.Image.LANCZOS
        )
        final = PIL.Image.new("RGBA", self._renderer.frame_size)
        final.paste(ret, ((self._renderer.frame_size[0] - ret.width) // 2, 0))
        return final

    def render_raw(self, time: int) -> libass.AssImageSequence:
        """Render the ASS data to a numpy array.

        :param time: PTS to render at
        :return: numpy array with RGB data
        """
        if self._track is None:
            raise ValueError("need source to render")

        return self._renderer.render_frame(self._track, now=time)
