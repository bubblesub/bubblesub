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

        api.subs.selection_changed.connect(self._on_subs_selection_change)
        api.media.current_pts_changed.connect(self._on_current_pts_change)
        api.media.audio.selection_changed.connect(
            self._on_audio_selection_change)

    def _on_subs_selection_change(self):
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

    def _on_current_pts_change(self):
        self._video_frame_label.setText(
            'Video frame: {} ({:.1%})'.format(
                bubblesub.util.ms_to_str(self._api.media.current_pts),
                self._api.media.current_pts / max(1, self._api.media.max_pts)))

    def _on_audio_selection_change(self):
        def format_ms_delta(delta):
            ret = bubblesub.util.ms_to_str(abs(delta))
            ret = ('\u2212', '+')[delta >= 0] + ret
            return ret

        if len(self._api.subs.selected_lines) != 1:
            return
        sub = self._api.subs.selected_lines[0]
        start_delta = self._api.media.audio.selection_start - sub.start
        end_delta = self._api.media.audio.selection_end - sub.end

        self._audio_selection_label.setText(
            'Audio selection: {} / {} (duration: {})'.format(
                format_ms_delta(start_delta),
                format_ms_delta(end_delta),
                bubblesub.util.ms_to_str(
                    self._api.media.audio.selection_size)))
