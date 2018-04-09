import bisect
from bubblesub.api.cmd import CoreCommand


class AudioScrollCommand(CoreCommand):
    name = 'audio/scroll'

    @property
    def menu_name(self):
        return '&Scroll waveform %s' % ['backward', 'forward'][self._delta > 0]

    def __init__(self, api, delta):
        super().__init__(api)
        self._delta = delta

    async def run(self):
        distance = self._delta * self.api.media.audio.view_size * 0.05
        self.api.media.audio.move_view(distance)


class AudioZoomCommand(CoreCommand):
    name = 'audio/zoom'

    @property
    def menu_name(self):
        return '&Zoom waveform %s' % ['in', 'out'][self._delta > 1]

    def __init__(self, api, delta):
        super().__init__(api)
        self._delta = delta

    async def run(self):
        mouse_x = 0.5
        cur_factor = self.api.media.audio.view_size / self.api.media.audio.size
        new_factor = cur_factor * self._delta
        self.api.media.audio.zoom_view(new_factor, mouse_x)


class AudioSnapSelectionStartToVideoCommand(CoreCommand):
    name = 'audio/snap-sel-start-to-video'
    menu_name = '&Snap selection start to video'

    @property
    def is_enabled(self):
        return self.api.media.audio.has_selection \
            and self.api.subs.has_selection

    async def run(self):
        self.api.media.audio.select(
            self.api.media.current_pts,
            self.api.media.audio.selection_end)


class AudioSnapSelectionEndToVideoCommand(CoreCommand):
    name = 'audio/snap-sel-end-to-video'
    menu_name = '&Snap selection end to video'

    @property
    def is_enabled(self):
        return self.api.media.audio.has_selection \
            and self.api.subs.has_selection

    async def run(self):
        self.api.media.audio.select(
            self.api.media.audio.selection_start,
            self.api.media.current_pts)


class AudioRealignSelectionToVideoCommand(CoreCommand):
    name = 'audio/snap-sel-to-video'
    menu_name = '&Snap selection to video'

    @property
    def is_enabled(self):
        return self.api.media.audio.has_selection \
            and self.api.subs.has_selection

    async def run(self):
        self.api.media.audio.select(
            self.api.media.current_pts,
            self.api.media.current_pts
            + self.api.opt.general['subs']['default_duration'])


class AudioSnapSelectionStartToPreviousSubtitleCommand(CoreCommand):
    name = 'audio/snap-sel-start-to-prev-sub'
    menu_name = '&Snap selection start to previous subtitle'

    @property
    def is_enabled(self):
        if not self.api.media.audio.has_selection:
            return False
        if not self.api.subs.has_selection:
            return False
        return self.api.subs.selected_lines[0].prev is not None

    async def run(self):
        self.api.media.audio.select(
            self.api.subs.selected_lines[0].prev.end,
            self.api.media.audio.selection_end)


class AudioSnapSelectionEndToNextSubtitleCommand(CoreCommand):
    name = 'audio/snap-sel-end-to-next-sub'
    menu_name = '&Snap selection start to next subtitle'

    @property
    def is_enabled(self):
        if not self.api.media.audio.has_selection:
            return False
        if not self.api.subs.has_selection:
            return False
        return self.api.subs.selected_lines[-1].next is not None

    async def run(self):
        self.api.media.audio.select(
            self.api.media.audio.selection_start,
            self.api.subs.selected_lines[-1].next.start)


class AudioShiftSelectionStartCommand(CoreCommand):
    name = 'audio/shift-sel-start'

    def __init__(self, api, delta, frames=True):
        super().__init__(api)
        self._delta = delta
        self._frames = frames

    @property
    def menu_name(self):
        return '&Shift selection start ({:+} {})'.format(
            self._delta, 'frames' if self._frames else 'ms')

    @property
    def is_enabled(self):
        return self.api.media.audio.has_selection and (
            not self._frames or self.api.media.video.timecodes)

    async def run(self):
        if self._frames:
            idx = bisect.bisect_left(
                self.api.media.video.timecodes,
                self.api.media.audio.selection_start)
            idx += self._delta
            idx = max(0, min(idx, len(self.api.media.video.timecodes) - 1))
            self.api.media.audio.select(
                self.api.media.video.timecodes[idx],
                self.api.media.audio.selection_end)
        else:
            self.api.media.audio.select(
                min(
                    self.api.media.audio.selection_end,
                    self.api.media.audio.selection_start + self._delta),
                self.api.media.audio.selection_end)


class AudioShiftSelectionEndCommand(CoreCommand):
    name = 'audio/shift-sel-end'

    def __init__(self, api, delta, frames=True):
        super().__init__(api)
        self._delta = delta
        self._frames = frames

    @property
    def menu_name(self):
        return '&Shift selection end ({:+} {})'.format(
            self._delta, 'frames' if self._frames else 'ms')

    @property
    def is_enabled(self):
        return self.api.media.audio.has_selection and (
            not self._frames or self.api.media.video.timecodes)

    async def run(self):
        if self._frames:
            idx = bisect.bisect_left(
                self.api.media.video.timecodes,
                self.api.media.audio.selection_end)
            idx += self._delta
            idx = max(0, min(idx, len(self.api.media.video.timecodes) - 1))
            self.api.media.audio.select(
                self.api.media.audio.selection_start,
                self.api.media.video.timecodes[idx])
        else:
            self.api.media.audio.select(
                self.api.media.audio.selection_start,
                max(
                    self.api.media.audio.selection_start,
                    self.api.media.audio.selection_end + self._delta))


class AudioShiftSelectionCommand(CoreCommand):
    name = 'audio/shift-sel'

    def __init__(self, api, delta, frames=True):
        super().__init__(api)
        self._delta = delta
        self._frames = frames

    @property
    def menu_name(self):
        return '&Shift selection ({:+} {})'.format(
            self._delta, 'frames' if self._frames else 'ms')

    @property
    def is_enabled(self):
        return self.api.media.audio.has_selection and (
            not self._frames or self.api.media.video.timecodes)

    async def run(self):
        if self._frames:
            idx1 = bisect.bisect_left(
                self.api.media.video.timecodes,
                self.api.media.audio.selection_start)
            idx2 = bisect.bisect_left(
                self.api.media.video.timecodes,
                self.api.media.audio.selection_end)
            idx1 += self._delta
            idx2 += self._delta
            idx1 = max(0, min(idx1, len(self.api.media.video.timecodes) - 1))
            idx2 = max(0, min(idx2, len(self.api.media.video.timecodes) - 1))
            self.api.media.audio.select(
                self.api.media.video.timecodes[idx1],
                self.api.media.video.timecodes[idx2])
        else:
            self.api.media.audio.select(
                self.api.media.audio.selection_start + self._delta,
                self.api.media.audio.selection_end + self._delta)


class AudioCommitSelectionCommand(CoreCommand):
    name = 'audio/commit-sel'
    menu_name = '&Commit selection to subtitle'

    @property
    def is_enabled(self):
        return self.api.subs.has_selection \
            and self.api.media.audio.has_selection

    async def run(self):
        for sub in self.api.subs.selected_lines:
            sub.begin_update()
            sub.start = self.api.media.audio.selection_start
            sub.end = self.api.media.audio.selection_end
            sub.end_update()
        self.api.undo.mark_undo()
