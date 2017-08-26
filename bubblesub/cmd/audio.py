from bubblesub.api.cmd import CoreCommand


class AudioScrollCommand(CoreCommand):
    name = 'audio/scroll'

    @property
    def menu_name(self):
        return 'Scroll waveform %s' % ['backward', 'forward'][self._delta > 0]

    def __init__(self, api, delta):
        super().__init__(api)
        self._delta = delta

    async def run(self):
        distance = self._delta * self.api.audio.view_size * 0.05
        self.api.audio.move_view(distance)


class AudioSnapSelectionStartToVideoCommand(CoreCommand):
    name = 'audio/snap-sel-start-to-video'
    menu_name = 'Snap selection start to video'

    def enabled(self):
        return self.api.audio.has_selection and self.api.subs.has_selection

    async def run(self):
        self.api.audio.select(
            self.api.video.current_pts,
            self.api.audio.selection_end)


class AudioSnapSelectionEndToVideoCommand(CoreCommand):
    name = 'audio/snap-sel-end-to-video'
    menu_name = 'Snap selection end to video'

    def enabled(self):
        return self.api.audio.has_selection and self.api.subs.has_selection

    async def run(self):
        self.api.audio.select(
            self.api.audio.selection_start,
            self.api.video.current_pts)


class AudioRealignSelectionToVideoCommand(CoreCommand):
    name = 'audio/snap-sel-to-video'
    menu_name = 'Snap selection to video'

    def enabled(self):
        return self.api.audio.has_selection and self.api.subs.has_selection

    async def run(self):
        self.api.audio.select(
            self.api.video.current_pts,
            self.api.video.current_pts
            + self.api.opt.general['subs']['default_duration'])


class AudioSnapSelectionStartToPreviousSubtitleCommand(CoreCommand):
    name = 'audio/snap-sel-start-to-prev-sub'
    menu_name = 'Snap selection start to previous subtitle'

    def enabled(self):
        if not self.api.audio.has_selection:
            return False
        if not self.api.subs.has_selection:
            return False
        return self.api.subs.selected_lines[0].prev is not None

    async def run(self):
        self.api.audio.select(
            self.api.subs.selected_lines[0].prev.end,
            self.api.audio.selection_end)


class AudioSnapSelectionEndToNextSubtitleCommand(CoreCommand):
    name = 'audio/snap-sel-end-to-next-sub'
    menu_name = 'Snap selection start to next subtitle'

    def enabled(self):
        if not self.api.audio.has_selection:
            return False
        if not self.api.subs.has_selection:
            return False
        return self.api.subs.selected_lines[-1].next is not None

    async def run(self):
        self.api.audio.select(
            self.api.audio.selection_start,
            self.api.subs.selected_lines[-1].next.start)


class AudioShiftSelectionStartCommand(CoreCommand):
    name = 'audio/shift-sel-start'

    def __init__(self, api, ms):
        super().__init__(api)
        self._ms = ms

    @property
    def menu_name(self):
        return 'Shift selection start ({:+} ms)'.format(self._ms)

    def enabled(self):
        return self.api.audio.has_selection

    async def run(self):
        self.api.audio.select(
            min(
                self.api.audio.selection_end,
                self.api.audio.selection_start + self._ms),
            self.api.audio.selection_end)


class AudioShiftSelectionEndCommand(CoreCommand):
    name = 'audio/shift-sel-end'

    def __init__(self, api, ms):
        super().__init__(api)
        self._ms = ms

    @property
    def menu_name(self):
        return 'Shift selection end ({:+} ms)'.format(self._ms)

    def enabled(self):
        return self.api.audio.has_selection

    async def run(self):
        self.api.audio.select(
            self.api.audio.selection_start,
            max(
                self.api.audio.selection_start,
                self.api.audio.selection_end + self._ms))


class AudioShiftSelectionCommand(CoreCommand):
    name = 'audio/shift-sel'

    def __init__(self, api, ms):
        super().__init__(api)
        self._ms = ms

    @property
    def menu_name(self):
        return 'Shift selection ({:+} ms)'.format(self._ms)

    def enabled(self):
        return self.api.audio.has_selection

    async def run(self):
        self.api.audio.select(
            self.api.audio.selection_start + self._ms,
            self.api.audio.selection_end + self._ms)


class AudioCommitSelectionCommand(CoreCommand):
    name = 'audio/commit-sel'
    menu_name = 'Commit selection to subtitle'

    def enabled(self):
        return self.api.subs.has_selection and self.api.audio.has_selection

    async def run(self):
        for sub in self.api.subs.selected_lines:
            sub.begin_update()
            sub.start = self.api.audio.selection_start
            sub.end = self.api.audio.selection_end
            sub.end_update()
