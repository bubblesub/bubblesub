import os
import re
import bisect
import bubblesub.ui.util
from bubblesub.api.cmd import CoreCommand


class VideoPlayCurrentLineCommand(CoreCommand):
    name = 'video/play-current-line'
    menu_name = 'Play current line'

    def enabled(self):
        return self.api.video.is_loaded and self.api.subs.has_selection

    async def run(self):
        sub = self.api.subs.selected_lines[0]
        self.api.video.play(sub.start, sub.end)


class VideoPlayAroundSelectionCommand(CoreCommand):
    name = 'video/play-around-sel'

    def __init__(self, api, delta_start, delta_end):
        super().__init__(api)
        self._delta_start = delta_start
        self._delta_end = delta_end

    @property
    def menu_name(self):
        return 'Play selection'

    def enabled(self):
        return self.api.video.is_loaded and self.api.audio.has_selection

    async def run(self):
        self.api.video.play(
            self.api.audio.selection_start + self._delta_start,
            self.api.audio.selection_end + self._delta_end)


class VideoPlayAroundSelectionStartCommand(CoreCommand):
    name = 'video/play-around-sel-start'

    def __init__(self, api, delta_start, delta_end):
        super().__init__(api)
        self._delta_start = delta_start
        self._delta_end = delta_end

    @property
    def menu_name(self):
        if self._delta_start < 0 and self._delta_end == 0:
            return 'Play {} ms before selection start'.format(
                abs(self._delta_start))
        if self._delta_start == 0 and self._delta_end > 0:
            return 'Play {} ms after selection start'.format(
                self._delta_end)
        return 'Play {:+} ms / {:+} ms around selection start'.format(
            self._delta_start, self._delta_end)

    def enabled(self):
        return self.api.video.is_loaded and self.api.audio.has_selection

    async def run(self):
        self.api.video.play(
            self.api.audio.selection_start + self._delta_start,
            self.api.audio.selection_start + self._delta_end)


class VideoPlayAroundSelectionEndCommand(CoreCommand):
    name = 'video/play-around-sel-end'

    def __init__(self, api, delta_start, delta_end):
        super().__init__(api)
        self._delta_start = delta_start
        self._delta_end = delta_end

    @property
    def menu_name(self):
        if self._delta_start < 0 and self._delta_end == 0:
            return 'Play {} ms before selection end'.format(
                abs(self._delta_start))
        if self._delta_start == 0 and self._delta_end > 0:
            return 'Play {} ms after selection end'.format(
                self._delta_end)
        return 'Play {:+} ms / {:+} ms around selection end'.format(
            self._delta_start, self._delta_end)

    def enabled(self):
        return self.api.video.is_loaded and self.api.audio.has_selection

    async def run(self):
        self.api.video.play(
            self.api.audio.selection_end + self._delta_start,
            self.api.audio.selection_end + self._delta_end)


class VideoStepFrameCommand(CoreCommand):
    name = 'video/step-frame'

    def __init__(self, api, delta):
        super().__init__(api)
        self._delta = delta

    @property
    def menu_name(self):
        return 'Step {} frame{} {}'.format(
            abs(self._delta),
            's' if abs(self._delta) > 1 else '',
            ['backward', 'forward'][self._delta > 0])

    def enabled(self):
        return self.api.video.is_loaded

    async def run(self):
        if self._delta == 1:
            self.api.video.step_frame_forward()
        elif self._delta == -1:
            self.api.video.step_frame_backward()
        else:
            current_pts = self.api.video.current_pts
            idx = bisect.bisect_left(self.api.video.timecodes, current_pts)
            if idx + self._delta not in range(len(self.api.video.timecodes)):
                return
            self.api.video.seek(self.api.video.timecodes[idx + self._delta])


class VideoStepMillisecondsCommand(CoreCommand):
    name = 'video/step-ms'

    def __init__(self, api, delta, precise):
        super().__init__(api)
        self._delta = delta
        self._precise = precise

    @property
    def menu_name(self):
        return 'Seek {} by {} ms'.format(
            ['backward', 'forward'][self._delta > 0],
            abs(self._delta))

    def enabled(self):
        return self.api.video.is_loaded

    async def run(self):
        self.api.video.seek(
            self.api.video.current_pts + self._delta, self._precise)


class VideoSeekWithGuiCommand(CoreCommand):
    name = 'video/seek-with-gui'
    menu_name = 'Seek to...'

    def enabled(self):
        return self.api.video.is_loaded

    async def run(self):
        async def _run_dialog(_api, main_window, **kwargs):
            return bubblesub.ui.util.time_jump_dialog(main_window, **kwargs)

        ret = await self.api.gui.exec(
            _run_dialog,
            absolute_label='Time to jump to:',
            relative_label='Time to jump by:',
            relative_checked=False,
            value=self.api.video.current_pts)

        if ret:
            value, is_relative = ret

            if is_relative:
                self.api.video.seek(self.api.video.current_pts + value)
            else:
                self.api.video.seek(value)


class VideoSetPlaybackSpeed(CoreCommand):
    name = 'video/set-playback-speed'

    def __init__(self, api, speed):
        super().__init__(api)
        self._speed = speed

    @property
    def menu_name(self):
        return 'Set playback speed to {}x'.format(self._speed)

    async def run(self):
        self.api.video.playback_speed = self._speed


class VideoTogglePauseCommand(CoreCommand):
    name = 'video/toggle-pause'
    menu_name = 'Toggle pause'

    def enabled(self):
        return self.api.video.is_loaded

    async def run(self):
        if self.api.video.is_paused:
            self.api.video.unpause()
        else:
            self.api.video.pause()


class VideoUnpauseCommand(CoreCommand):
    name = 'video/unpause'
    menu_name = 'Play until end of the file'

    def enabled(self):
        return self.api.video.is_loaded

    async def run(self):
        if not self.api.video.is_paused:
            return
        self.api.video.unpause()


class VideoPauseCommand(CoreCommand):
    name = 'video/pause'
    menu_name = 'Pause playback'

    def enabled(self):
        return self.api.video.is_loaded

    async def run(self):
        if self.api.video.is_paused:
            return
        self.api.video.pause()


class VideoScreenshotCommand(CoreCommand):
    name = 'video/screenshot'

    def __init__(self, api, include_subtitles):
        super().__init__(api)
        self._include_subtitles = include_subtitles

    def enabled(self):
        return self.api.video.is_loaded

    @property
    def menu_name(self):
        return 'Save screenshot ({} subtitles)'.format(
            'with' if self._include_subtitles else 'without')

    async def run(self):
        async def run_dialog(api, main_window):
            file_name = 'shot-{}-{}.png'.format(
                os.path.basename(api.video.path),
                bubblesub.util.ms_to_str(api.video.current_pts))

            file_name = file_name.replace(':', '.')
            file_name = file_name.replace(' ', '_')
            file_name = re.sub(r'(?u)[^-\w.]', '', file_name)

            return bubblesub.ui.util.save_dialog(
                main_window,
                'Portable Network Graphics (*.png)',
                file_name=file_name)

        path = await self.api.gui.exec(run_dialog)
        if path:
            self.api.video.screenshot(path, self._include_subtitles)
