from bubblesub.api.cmd import CoreCommand


class AudioScrollCommand(CoreCommand):
    name = 'audio/scroll'

    async def run(self, delta):
        distance = delta * self.api.audio.view_size * 0.05
        self.api.audio.move_view(distance)


class AudioSnapSelectionStartToVideoCommand(CoreCommand):
    name = 'audio/snap-sel-start-to-video'

    def enabled(self):
        return self.api.audio.has_selection and self.api.subs.has_selection

    async def run(self):
        self.api.audio.select(
            self.api.video.current_pts,
            self.api.audio.selection_end)


class AudioSnapSelectionEndToVideoCommand(CoreCommand):
    name = 'audio/snap-sel-end-to-video'

    def enabled(self):
        return self.api.audio.has_selection and self.api.subs.has_selection

    async def run(self):
        self.api.audio.select(
            self.api.audio.selection_start,
            self.api.video.current_pts)


class AudioRealignSelectionToVideoCommand(CoreCommand):
    name = 'audio/snap-sel-to-video'

    def enabled(self):
        return self.api.audio.has_selection and self.api.subs.has_selection

    async def run(self):
        self.api.audio.select(
            self.api.video.current_pts,
            self.api.video.current_pts
            + self.api.opt.general['subs']['default_duration'])


class AudioSnapSelectionStartToPreviousSubtitleCommand(CoreCommand):
    name = 'audio/snap-sel-start-to-prev-sub'

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


class AudioMoveSelectionStartCommand(CoreCommand):
    name = 'audio/move-sel-start'

    def enabled(self):
        return self.api.audio.has_selection

    async def run(self, ms):
        self.api.audio.select(
            min(
                self.api.audio.selection_end,
                self.api.audio.selection_start + ms),
            self.api.audio.selection_end)


class AudioMoveSelectionEndCommand(CoreCommand):
    name = 'audio/move-sel-end'

    def enabled(self):
        return self.api.audio.has_selection

    async def run(self, ms):
        self.api.audio.select(
            self.api.audio.selection_start,
            max(
                self.api.audio.selection_start,
                self.api.audio.selection_end + ms))


class AudioMoveSelectionCommand(CoreCommand):
    name = 'audio/move-sel'

    def enabled(self):
        return self.api.audio.has_selection

    async def run(self, ms):
        self.api.audio.select(
            self.api.audio.selection_start + ms,
            self.api.audio.selection_end + ms)


class AudioCommitSelectionCommand(CoreCommand):
    name = 'audio/commit-sel'

    def enabled(self):
        return self.api.subs.has_selection and self.api.audio.has_selection

    async def run(self):
        for sub in self.api.subs.selected_lines:
            sub.begin_update()
            sub.start = self.api.audio.selection_start
            sub.end = self.api.audio.selection_end
            sub.end_update()
