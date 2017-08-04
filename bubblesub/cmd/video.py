import bisect
from bubblesub.api.cmd import CoreCommand


class VideoPlayCurrentLineCommand(CoreCommand):
    name = 'video/play-current-line'

    def enabled(self):
        return self.api.subs.has_selection

    def run(self):
        sub = self.api.subs.selected_lines[0]
        self.api.video.play(sub.start, sub.end)


class VideoPlayAroundSelectionCommand(CoreCommand):
    name = 'video/play-around-sel'

    def enabled(self):
        return self.api.audio.has_selection

    def run(self, delta_start, delta_end):
        self.api.video.play(
            self.api.audio.selection_start + delta_start,
            self.api.audio.selection_end + delta_end)


class VideoPlayAroundSelectionStartCommand(CoreCommand):
    name = 'video/play-around-sel-start'

    def enabled(self):
        return self.api.audio.has_selection

    def run(self, delta_start, delta_end):
        self.api.video.play(
            self.api.audio.selection_start + delta_start,
            self.api.audio.selection_start + delta_end)


class VideoPlayAroundSelectionEndCommand(CoreCommand):
    name = 'video/play-around-sel-end'

    def enabled(self):
        return self.api.audio.has_selection

    def run(self, delta_start, delta_end):
        self.api.video.play(
            self.api.audio.selection_end + delta_start,
            self.api.audio.selection_end + delta_end)


class VideoStepFrameCommand(CoreCommand):
    name = 'video/step-frame'

    def enabled(self):
        return len(self.api.video.timecodes) > 0

    def run(self, delta):
        current_pts = self.api.video.current_pts
        idx = bisect.bisect_left(self.api.video.timecodes, current_pts)
        if idx + delta not in range(len(self.api.video.timecodes)):
            return
        self.api.video.seek(self.api.video.timecodes[idx + delta])


class VideoSetPlaybackSpeed(CoreCommand):
    name = 'video/set-playback-speed'

    def enabled(self):
        return len(self.api.video.timecodes) > 0

    def run(self, speed):
        self.api.video.playback_speed = speed


class VideoTogglePauseCommand(CoreCommand):
    name = 'video/toggle-pause'

    def run(self):
        if self.api.video.is_paused:
            self.api.video.unpause()
        else:
            self.api.video.pause()


class VideoUnpauseCommand(CoreCommand):
    name = 'video/unpause'

    def run(self):
        if not self.api.video.is_paused:
            return
        self.api.video.unpause()


class VideoPauseCommand(CoreCommand):
    name = 'video/pause'

    def run(self):
        if self.api.video.is_paused:
            return
        self.api.video.pause()
