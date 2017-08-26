import bisect
from bubblesub.api.cmd import CoreCommand


class VideoPlayCurrentLineCommand(CoreCommand):
    name = 'video/play-current-line'
    menu_name = 'Play current line'

    def enabled(self):
        return self.api.subs.has_selection

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
        return self.api.audio.has_selection

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
        return self.api.audio.has_selection

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
        return self.api.audio.has_selection

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
        return len(self.api.video.timecodes) > 0

    async def run(self):
        current_pts = self.api.video.current_pts
        idx = bisect.bisect_left(self.api.video.timecodes, current_pts)
        if idx + self._delta not in range(len(self.api.video.timecodes)):
            return
        self.api.video.seek(self.api.video.timecodes[idx + self._delta])


class VideoSetPlaybackSpeed(CoreCommand):
    name = 'video/set-playback-speed'

    def __init__(self, api, speed):
        super().__init__(api)
        self._speed = speed

    @property
    def menu_name(self):
        return 'Set playback speed to {}x'.format(self._speed)

    def enabled(self):
        return len(self.api.video.timecodes) > 0

    async def run(self):
        self.api.video.playback_speed = self._speed


class VideoTogglePauseCommand(CoreCommand):
    name = 'video/toggle-pause'
    menu_name = 'Toggle pause'

    async def run(self):
        if self.api.video.is_paused:
            self.api.video.unpause()
        else:
            self.api.video.pause()


class VideoUnpauseCommand(CoreCommand):
    name = 'video/unpause'
    menu_name = 'Play until end of the file'

    async def run(self):
        if not self.api.video.is_paused:
            return
        self.api.video.unpause()


class VideoPauseCommand(CoreCommand):
    name = 'video/pause'
    menu_name = 'Pause playback'

    async def run(self):
        if self.api.video.is_paused:
            return
        self.api.video.pause()
