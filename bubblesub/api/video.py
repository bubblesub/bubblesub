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

"""Video stream API."""

import typing as T
from pathlib import Path

from bubblesub.api.base_streams_api import BaseStreamsApi, TStream
from bubblesub.api.log import LogApi
from bubblesub.api.subs import SubtitlesApi
from bubblesub.api.threading import ThreadingApi
from bubblesub.api.video_stream import VideoStream

# TODO: remove this condition when switching to Python 3.7
if T.TYPE_CHECKING:
    # this trigger a mypy error at the moment, but once bubblesub switches to
    # Python 3.7, this issue will get resolved on its own.
    VideoApiBaseClass = BaseStreamsApi[VideoStream]
else:
    VideoApiBaseClass = BaseStreamsApi


class VideoApi(VideoApiBaseClass):
    """Manages video streams."""

    def __init__(
        self,
        threading_api: ThreadingApi,
        log_api: LogApi,
        subs_api: SubtitlesApi,
    ) -> None:
        """Initialize self.

        :param threading_api: threading API
        :param log_api: logging API
        :param subs_api: subtitles API
        """
        super().__init__()
        self._threading_api = threading_api
        self._log_api = log_api
        self._subs_api = subs_api

    def _on_stream_load(self, stream: VideoStream) -> None:
        super()._on_stream_load(stream)
        self._subs_api.remember_video_path_if_needed(stream.path)

    def _create_stream(self, path: Path) -> TStream:
        return VideoStream(
            self._threading_api, self._log_api, self._subs_api, path
        )
