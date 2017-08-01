import bisect
from bubblesub.cmd.registry import BaseCommand


class VideoPlayCurrentLineCommand(BaseCommand):
    name = 'video/play-current-line'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api):
        sel = api.subs.lines[api.subs.selected_lines[0]]
        api.video.play(sel.start, sel.end)


class VideoPlayAroundSelectionCommand(BaseCommand):
    name = 'video/play-around-sel'

    def enabled(self, api):
        return api.audio.has_selection

    def run(self, api, delta_start, delta_end):
        api.video.play(
            api.audio.selection_start + delta_start,
            api.audio.selection_end + delta_end)


class VideoPlayAroundSelectionStartCommand(BaseCommand):
    name = 'video/play-around-sel-start'

    def enabled(self, api):
        return api.audio.has_selection

    def run(self, api, delta_start, delta_end):
        api.video.play(
            api.audio.selection_start + delta_start,
            api.audio.selection_start + delta_end)


class VideoPlayAroundSelectionEndCommand(BaseCommand):
    name = 'video/play-around-sel-end'

    def enabled(self, api):
        return api.audio.has_selection

    def run(self, api, delta_start, delta_end):
        api.video.play(
            api.audio.selection_end + delta_start,
            api.audio.selection_end + delta_end)


class VideoStepFrameCommand(BaseCommand):
    name = 'video/step-frame'

    def enabled(self, api):
        return len(api.video.timecodes) > 0

    def run(self, api, delta):
        current_pts = api.video.current_pts
        idx = bisect.bisect_left(api.video.timecodes, current_pts)
        if idx + delta not in range(len(api.video.timecodes)):
            return
        api.video.seek(api.video.timecodes[idx + delta])


class VideoSetPlaybackSpeed(BaseCommand):
    name = 'video/set-playback-speed'

    def enabled(self, api):
        return len(api.video.timecodes) > 0

    def run(self, api, speed):
        api.video.playback_speed = speed


class VideoTogglePauseCommand(BaseCommand):
    name = 'video/toggle-pause'

    def run(self, api):
        if api.video.is_paused:
            api.video.unpause()
        else:
            api.video.pause()


class VideoUnpauseCommand(BaseCommand):
    name = 'video/unpause'

    def run(self, api):
        if not api.video.is_paused:
            return
        api.video.unpause()


class VideoPauseCommand(BaseCommand):
    name = 'video/pause'

    def run(self, api):
        if api.video.is_paused:
            return
        api.video.pause()
