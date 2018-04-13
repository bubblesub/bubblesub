import bisect
import re
import typing as T
from pathlib import Path

from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ui.util
from bubblesub.api.cmd import CoreCommand


class VideoPlayCurrentLineCommand(CoreCommand):
    name = 'video/play-current-line'
    menu_name = '&Play current line'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded and self.api.subs.has_selection

    async def run(self) -> None:
        sub = self.api.subs.selected_lines[0]
        self.api.media.play(sub.start, sub.end)


class VideoPlayAroundSelectionCommand(CoreCommand):
    name = 'video/play-around-sel'
    menu_name = '&Play selection'

    def __init__(
            self,
            api: bubblesub.api.Api,
            delta_start: int,
            delta_end: int
    ) -> None:
        super().__init__(api)
        self._delta_start = delta_start
        self._delta_end = delta_end

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded \
            and self.api.media.audio.has_selection

    async def run(self) -> None:
        self.api.media.play(
            self.api.media.audio.selection_start + self._delta_start,
            self.api.media.audio.selection_end + self._delta_end
        )


class VideoPlayAroundSelectionStartCommand(CoreCommand):
    name = 'video/play-around-sel-start'

    def __init__(
            self,
            api: bubblesub.api.Api,
            delta_start: int,
            delta_end: int
    ) -> None:
        super().__init__(api)
        self._delta_start = delta_start
        self._delta_end = delta_end

    @property
    def menu_name(self) -> str:
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
        return self.api.media.is_loaded \
            and self.api.media.audio.has_selection

    async def run(self) -> None:
        self.api.media.play(
            self.api.media.audio.selection_start + self._delta_start,
            self.api.media.audio.selection_start + self._delta_end
        )


class VideoPlayAroundSelectionEndCommand(CoreCommand):
    name = 'video/play-around-sel-end'

    def __init__(
            self,
            api: bubblesub.api.Api,
            delta_start: int,
            delta_end: int
    ) -> None:
        super().__init__(api)
        self._delta_start = delta_start
        self._delta_end = delta_end

    @property
    def menu_name(self) -> str:
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
        return self.api.media.is_loaded \
            and self.api.media.audio.has_selection

    async def run(self) -> None:
        self.api.media.play(
            self.api.media.audio.selection_end + self._delta_start,
            self.api.media.audio.selection_end + self._delta_end
        )


class VideoStepFrameCommand(CoreCommand):
    name = 'video/step-frame'

    def __init__(self, api: bubblesub.api.Api, delta: int) -> None:
        super().__init__(api)
        self._delta = delta

    @property
    def menu_name(self) -> str:
        return 'Step {} &frame{} {}'.format(
            abs(self._delta),
            's' if abs(self._delta) > 1 else '',
            ['backward', 'forward'][self._delta > 0]
        )

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded

    async def run(self) -> None:
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


class VideoStepMillisecondsCommand(CoreCommand):
    name = 'video/step-ms'

    def __init__(
            self,
            api: bubblesub.api.Api,
            delta: int,
            precise: bool
    ) -> None:
        super().__init__(api)
        self._delta = delta
        self._precise = precise

    @property
    def menu_name(self) -> str:
        return '&Seek {} by {} ms'.format(
            ['backward', 'forward'][self._delta > 0],
            abs(self._delta)
        )

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded

    async def run(self) -> None:
        self.api.media.seek(
            self.api.media.current_pts + self._delta, self._precise
        )


class VideoSeekWithGuiCommand(CoreCommand):
    name = 'video/seek-with-gui'
    menu_name = '&Seek to...'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded

    async def run(self) -> None:
        async def _run_dialog(
                _api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow,
                **kwargs: T.Any
        ) -> T.Optional[T.Tuple[int, bool]]:
            return bubblesub.ui.util.time_jump_dialog(main_window, **kwargs)

        ret = await self.api.gui.exec(
            _run_dialog,
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


class VideoSetPlaybackSpeed(CoreCommand):
    name = 'video/set-playback-speed'

    def __init__(self, api: bubblesub.api.Api, expr: T.Any) -> None:
        super().__init__(api)
        self._expr = str(expr)

    @property
    def menu_name(self) -> str:
        return '&Set playback speed to {}'.format(
            self._expr.format('current speed')
        )

    async def run(self) -> None:
        self.api.media.playback_speed = bubblesub.util.eval_expr(
            self._expr.format(self.api.media.playback_speed)
        )


class VideoTogglePauseCommand(CoreCommand):
    name = 'video/toggle-pause'
    menu_name = '&Toggle pause'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded

    async def run(self) -> None:
        if self.api.media.is_paused:
            self.api.media.unpause()
        else:
            self.api.media.pause()


class VideoUnpauseCommand(CoreCommand):
    name = 'video/unpause'
    menu_name = '&Play until end of the file'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded

    async def run(self) -> None:
        if not self.api.media.is_paused:
            return
        self.api.media.unpause()


class VideoPauseCommand(CoreCommand):
    name = 'video/pause'
    menu_name = '&Pause playback'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded

    async def run(self) -> None:
        if self.api.media.is_paused:
            return
        self.api.media.pause()


class VideoScreenshotCommand(CoreCommand):
    name = 'video/screenshot'

    def __init__(
            self,
            api: bubblesub.api.Api,
            include_subtitles: bool
    ) -> None:
        super().__init__(api)
        self._include_subtitles = include_subtitles

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded

    @property
    def menu_name(self) -> str:
        return '&Save screenshot ({} subtitles)'.format(
            'with' if self._include_subtitles else 'without'
        )

    async def run(self) -> None:
        async def _run_dialog(
                api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow
        ) -> T.Optional[Path]:
            assert api.media.path is not None

            file_name = 'shot-{}-{}.png'.format(
                api.media.path.name,
                bubblesub.util.ms_to_str(api.media.current_pts)
            )

            file_name = file_name.replace(':', '.')
            file_name = file_name.replace(' ', '_')
            file_name = re.sub(r'(?u)[^-\w.]', '', file_name)

            return bubblesub.ui.util.save_dialog(
                main_window,
                'Portable Network Graphics (*.png)',
                file_name=file_name
            )

        path = await self.api.gui.exec(_run_dialog)
        if path is not None:
            self.api.media.video.screenshot(path, self._include_subtitles)


class VideoSetVolumeCommand(CoreCommand):
    name = 'video/set-volume'

    def __init__(self, api: bubblesub.api.Api, expr: T.Any) -> None:
        super().__init__(api)
        self._expr = str(expr)

    @property
    def menu_name(self) -> str:
        return '&Set volume to {}'.format(self._expr.format('current volume'))

    async def run(self) -> None:
        self.api.media.volume = bubblesub.util.eval_expr(
            self._expr.format(self.api.media.volume)
        )
