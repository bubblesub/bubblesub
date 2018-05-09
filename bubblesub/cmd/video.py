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

"""Commands related to video and playback."""

import bisect
import re
import typing as T
from pathlib import Path

from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ui.util
from bubblesub.api.cmd import BaseCommand


class PlayCurrentSubtitleCommand(BaseCommand):
    """Plays the currently selected subtitle."""

    name = 'video/play-current-line'
    menu_name = '&Play current line'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.is_loaded and self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        sub = self.api.subs.selected_events[0]
        self.api.media.play(sub.start, sub.end)


class PlayAroundSpectrogramSelectionCommand(BaseCommand):
    """Plays a region near the current spectrogram selection."""

    name = 'video/play-around-sel'
    menu_name = '&Play selection'

    def __init__(
            self,
            api: bubblesub.api.Api,
            delta_start: int,
            delta_end: int
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param delta_start: delta relative to the selection start in
            milliseconds
        :param delta_end: delta relative to the selection end in milliseconds
        """
        super().__init__(api)
        self._delta_start = delta_start
        self._delta_end = delta_end

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.is_loaded \
            and self.api.media.audio.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        self.api.media.play(
            self.api.media.audio.selection_start + self._delta_start,
            self.api.media.audio.selection_end + self._delta_end
        )


class PlayAroundSpectrogramSelectionStartCommand(BaseCommand):
    """Plays a region near the current spectrogram selection start."""

    name = 'video/play-around-sel-start'

    def __init__(
            self,
            api: bubblesub.api.Api,
            delta_start: int,
            delta_end: int
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param delta_start: delta relative to the selection start in
            milliseconds
        :param delta_end: delta relative to the selection start in milliseconds
        """
        super().__init__(api)
        self._delta_start = delta_start
        self._delta_end = delta_end

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        if self._delta_start < 0 and self._delta_end == 0:
            return 'Play {} ms &before selection start'.format(
                abs(self._delta_start)
            )
        if self._delta_start == 0 and self._delta_end > 0:
            return 'Play {} ms &after selection start'.format(
                self._delta_end
            )
        return '&Play {:+} ms / {:+} ms around selection start'.format(
            self._delta_start, self._delta_end
        )

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.is_loaded \
            and self.api.media.audio.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        self.api.media.play(
            self.api.media.audio.selection_start + self._delta_start,
            self.api.media.audio.selection_start + self._delta_end
        )


class PlayAroundSpectrogramSelectionEndCommand(BaseCommand):
    """Plays a region near the current spectrogram selection end."""

    name = 'video/play-around-sel-end'

    def __init__(
            self,
            api: bubblesub.api.Api,
            delta_start: int,
            delta_end: int
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param delta_start: delta relative to the selection end in milliseconds
        :param delta_end: delta relative to the selection end in milliseconds
        """
        super().__init__(api)
        self._delta_start = delta_start
        self._delta_end = delta_end

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        if self._delta_start < 0 and self._delta_end == 0:
            return 'Play {} ms &before selection end'.format(
                abs(self._delta_start)
            )
        if self._delta_start == 0 and self._delta_end > 0:
            return 'Play {} ms &after selection end'.format(
                self._delta_end
            )
        return '&Play {:+} ms / {:+} ms around selection end'.format(
            self._delta_start, self._delta_end
        )

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.is_loaded \
            and self.api.media.audio.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        self.api.media.play(
            self.api.media.audio.selection_end + self._delta_start,
            self.api.media.audio.selection_end + self._delta_end
        )


class StepFrameCommand(BaseCommand):
    """Seeks the video by the specified amount of frames."""

    name = 'video/step-frame'

    def __init__(self, api: bubblesub.api.Api, delta: int) -> None:
        """
        Initialize self.

        :param api: core API
        :param delta: how many frames to step
        """
        super().__init__(api)
        self._delta = delta

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return 'Step {} &frame{} {}'.format(
            abs(self._delta),
            's' if abs(self._delta) > 1 else '',
            'forward' if self._delta > 0 else 'backward'
        )

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.is_loaded

    async def run(self) -> None:
        """Carry out the command."""
        if self._delta == 1:
            self.api.media.step_frame_forward()
        elif self._delta == -1:
            self.api.media.step_frame_backward()
        else:
            current_pts = self.api.media.current_pts
            idx = bisect.bisect_left(
                self.api.media.video.timecodes, current_pts
            )
            if idx + self._delta not in range(
                    len(self.api.media.video.timecodes)
            ):
                return
            self.api.media.seek(
                self.api.media.video.timecodes[idx + self._delta]
            )


class StepMillisecondsCommand(BaseCommand):
    """Seeks the video by the specified milliseconds."""

    name = 'video/step-ms'

    def __init__(
            self,
            api: bubblesub.api.Api,
            delta: int,
            precise: bool
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param delta: how many milliseconds to step
        :param precise: whether to use precise seeking
            at the expense of performance
        """
        super().__init__(api)
        self._delta = delta
        self._precise = precise

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return '&Seek {} by {} ms'.format(
            ['backward', 'forward'][self._delta > 0],
            abs(self._delta)
        )

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.is_loaded

    async def run(self) -> None:
        """Carry out the command."""
        self.api.media.seek(
            self.api.media.current_pts + self._delta, self._precise
        )


class SeekWithGuiCommand(BaseCommand):
    """
    Seeks the video to the desired place.

    Prompts user for details with a GUI dialog.
    """

    name = 'video/seek-with-gui'
    menu_name = '&Seek to...'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.is_loaded

    async def run(self) -> None:
        """Carry out the command."""
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        ret = bubblesub.ui.util.time_jump_dialog(
            main_window,
            absolute_label='Time to jump to:',
            relative_label='Time to jump by:',
            relative_checked=False,
            value=self.api.media.current_pts
        )

        if ret is not None:
            value, is_relative = ret

            if is_relative:
                self.api.media.seek(
                    self.api.media.current_pts + value
                )
            else:
                self.api.media.seek(value)


class SetPlaybackSpeedCommand(BaseCommand):
    """Adjusts the video playback speed."""

    name = 'video/set-playback-speed'

    def __init__(self, api: bubblesub.api.Api, expr: str) -> None:
        """
        Initialize self.

        :param api: core API
        :param expr: expression to calculate new playback speed
        """
        super().__init__(api)
        self._expr = expr

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return '&Set playback speed to {}'.format(
            self._expr.format('current speed')
        )

    async def run(self) -> None:
        """Carry out the command."""
        self.api.media.playback_speed = bubblesub.util.eval_expr(
            self._expr.format(self.api.media.playback_speed)
        )


class SetVolumeCommand(BaseCommand):
    """Adjusts the video volume."""

    name = 'video/set-volume'

    def __init__(self, api: bubblesub.api.Api, expr: str) -> None:
        """
        Initialize self.

        :param api: core API
        :param expr: expression to calculate new volume
        """
        super().__init__(api)
        self._expr = expr

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return '&Set volume to {}'.format(self._expr.format('current volume'))

    async def run(self) -> None:
        """Carry out the command."""
        self.api.media.volume = bubblesub.util.eval_expr(
            self._expr.format(self.api.media.volume)
        )


class TogglePauseCommand(BaseCommand):
    """Pauses or unpauses the video playback."""

    name = 'video/toggle-pause'
    menu_name = '&Toggle pause'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.is_loaded

    async def run(self) -> None:
        """Carry out the command."""
        if self.api.media.is_paused:
            self.api.media.unpause()
        else:
            self.api.media.pause()


class UnpauseCommand(BaseCommand):
    """Unpauses the video playback."""

    name = 'video/unpause'
    menu_name = '&Play until end of the file'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.is_loaded

    async def run(self) -> None:
        """Carry out the command."""
        if not self.api.media.is_paused:
            return
        self.api.media.unpause()


class PauseCommand(BaseCommand):
    """Pauses the video playback."""

    name = 'video/pause'
    menu_name = '&Pause playback'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.is_loaded

    async def run(self) -> None:
        """Carry out the command."""
        if self.api.media.is_paused:
            return
        self.api.media.pause()


class ScreenshotCommand(BaseCommand):
    """
    Makes a screenshot of the current video frame.

    Prompts user for the path where to save the screenshot to.
    """

    name = 'video/screenshot'

    def __init__(
            self,
            api: bubblesub.api.Api,
            include_subtitles: bool
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param include_subtitles: whether to "burn" the subtitles into
            the screenshot
        """
        super().__init__(api)
        self._include_subtitles = include_subtitles

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.media.is_loaded

    @property
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        return '&Save screenshot ({} subtitles)'.format(
            'with' if self._include_subtitles else 'without'
        )

    async def run(self) -> None:
        """Carry out the command."""
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        path = self._show_dialog(main_window)
        if path is None:
            self.info('cancelled')
        else:
            self.api.media.video.screenshot(path, self._include_subtitles)
            self.info(f'saved screenshot to {path}')

    def _show_dialog(
            self,
            main_window: QtWidgets.QMainWindow
    ) -> T.Optional[Path]:
        assert self.api.media.path is not None

        file_name = 'shot-{}-{}.png'.format(
            self.api.media.path.name,
            bubblesub.util.ms_to_str(self.api.media.current_pts)
        )

        file_name = file_name.replace(':', '.')
        file_name = file_name.replace(' ', '_')
        file_name = re.sub(r'(?u)[^-\w.]', '', file_name)

        return bubblesub.ui.util.save_dialog(
            main_window,
            'Portable Network Graphics (*.png)',
            file_name=file_name
        )


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    """
    Register commands in this file into the command API.

    :param cmd_api: command API
    """
    for cls in [
            PlayCurrentSubtitleCommand,
            PlayAroundSpectrogramSelectionCommand,
            PlayAroundSpectrogramSelectionStartCommand,
            PlayAroundSpectrogramSelectionEndCommand,
            StepFrameCommand,
            StepMillisecondsCommand,
            SeekWithGuiCommand,
            SetPlaybackSpeedCommand,
            SetVolumeCommand,
            TogglePauseCommand,
            UnpauseCommand,
            PauseCommand,
            ScreenshotCommand,
    ]:
        cmd_api.register_core_command(cls)
