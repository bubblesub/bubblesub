from PyQt5 import QtWidgets
import bubblesub.util


class StatusBar(QtWidgets.QStatusBar):
    def __init__(self, api, parent):
        super().__init__(parent)
        self._api = api
        self._subs_label = QtWidgets.QLabel(self)
        self._video_frame_label = QtWidgets.QLabel(self)
        self._audio_selection_label = QtWidgets.QLabel(self)
        self.setSizeGripEnabled(False)

        for label in [
            self._subs_label,
            self._video_frame_label,
            self._audio_selection_label
        ]:
            label.setFrameStyle(
                QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)
            label.setLineWidth(1)

        self.addPermanentWidget(self._subs_label)
        self.addPermanentWidget(self._video_frame_label)
        self.addPermanentWidget(self._audio_selection_label)

        api.video.current_pts_changed.connect(self._video_current_pts_changed)
        api.audio.selection_changed.connect(self._audio_selection_changed)
        api.subs.selection_changed.connect(self._subs_selection_changed)

    def _subs_selection_changed(self):
        count = len(self._api.subs.selected_indexes)
        total = len(self._api.subs.lines)

        if count == 0:
            self._subs_label.setText(f'Subtitles: -/{total} (-%)')
        elif count == 1:
            idx = self._api.subs.selected_indexes[0]
            self._subs_label.setText(
                f'Subtitles: {idx + 1}/{total} ({idx / total:.1%})')
        else:
            def format_range(low, high):
                return f'{low}..{high}' if low != high else str(low)

            ranges = []
            for idx in self._api.subs.selected_indexes:
                if ranges and ranges[-1][1] == idx - 1:
                    ranges[-1] = (ranges[-1][0], idx)
                else:
                    ranges.append((idx, idx))

            self._subs_label.setText(
                'Subtitles: {}/{} ({}, {:.1%})'.format(
                    ','.join(
                        format_range(low + 1, high + 1)
                        for low, high in ranges),
                    total,
                    count,
                    count / total))


    def _video_current_pts_changed(self):
        self._video_frame_label.setText(
            'Video frame: {} ({:.1%})'.format(
                bubblesub.util.ms_to_str(self._api.video.current_pts),
                self._api.video.current_pts / max(1, self._api.video.max_pts)))

    def _audio_selection_changed(self):
        if len(self._api.subs.selected_lines) != 1:
            return
        sub = self._api.subs.selected_lines[0]
        start_delta = self._api.audio.selection_start - sub.start
        end_delta = self._api.audio.selection_end - sub.end

        self._audio_selection_label.setText(
            'Audio selection: {:+.0f} ms / {:+.0f} ms (duration: {})'.format(
                start_delta,
                end_delta,
                bubblesub.util.ms_to_str(self._api.audio.selection_size)))
