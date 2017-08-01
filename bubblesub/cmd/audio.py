from bubblesub.cmd.registry import BaseCommand
from PyQt5 import QtWidgets


class AudioScrollCommand(BaseCommand):
    name = 'audio/scroll'

    def run(self, api, delta):
        distance = delta * api.audio.view_size * 0.05
        api.audio.move_view(distance)


class AudioSnapSelectionStartToVideoCommand(BaseCommand):
    name = 'audio/snap-sel-start-to-video'

    def enabled(self, api):
        return api.audio.has_selection and api.subs.has_selection

    def run(self, api):
        api.audio.select(api.video.current_pts, api.audio.selection_end)


class AudioSnapSelectionEndToVideoCommand(BaseCommand):
    name = 'audio/snap-sel-end-to-video'

    def enabled(self, api):
        return api.audio.has_selection and api.subs.has_selection

    def run(self, api):
        api.audio.select(api.audio.selection_start, api.video.current_pts)


class AudioRealignSelectionToVideoCommand(BaseCommand):
    name = 'audio/snap-sel-to-video'

    def enabled(self, api):
        return api.audio.has_selection and api.subs.has_selection

    def run(self, api):
        api.audio.select(
            api.video.current_pts,
            api.video.current_pts
            + api.opt.general['subs']['default_duration'])


class AudioSnapSelectionStartToPreviousSubtitleCommand(BaseCommand):
    name = 'audio/snap-sel-start-to-prev-sub'

    def enabled(self, api):
        if not api.audio.has_selection:
            return False
        if not api.subs.selected_indexes:
            return False
        return api.subs.selected_indexes[0] > 0

    def run(self, api):
        api.audio.select(
            api.subs.lines[api.subs.selected_indexes[0] - 1].end,
            api.audio.selection_end)


class AudioSnapSelectionEndToNextSubtitleCommand(BaseCommand):
    name = 'audio/snap-sel-end-to-next-sub'

    def enabled(self, api):
        if not api.audio.has_selection:
            return False
        if not api.subs.selected_indexes:
            return False
        return api.subs.selected_indexes[-1] + 1 < len(api.subs.lines)

    def run(self, api):
        api.audio.select(
            api.audio.selection_start,
            api.subs.lines[api.subs.selected_indexes[-1] + 1].start)


class AudioMoveSelectionStartCommand(BaseCommand):
    name = 'audio/move-sel-start'

    def enabled(self, api):
        return api.audio.has_selection

    def run(self, api, ms):
        api.audio.select(
            min(api.audio.selection_end, api.audio.selection_start + ms),
            api.audio.selection_end)


class AudioMoveSelectionEndCommand(BaseCommand):
    name = 'audio/move-sel-end'

    def enabled(self, api):
        return api.audio.has_selection

    def run(self, api, ms):
        api.audio.select(
            api.audio.selection_start,
            max(api.audio.selection_start, api.audio.selection_end + ms))


class AudioCommitSelectionCommand(BaseCommand):
    name = 'audio/commit-sel'

    def enabled(self, api):
        return api.subs.has_selection and api.audio.has_selection

    def run(self, api):
        for sub in api.subs.selected_lines:
            sub.begin_update()
            sub.start = api.audio.selection_start
            sub.end = api.audio.selection_end
            sub.end_update()
