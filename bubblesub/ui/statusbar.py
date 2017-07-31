from PyQt5 import QtWidgets
import bubblesub.util


class StatusBar(QtWidgets.QStatusBar):
    def __init__(self, api, parent):
        super().__init__(parent)
        self._api = api
        self.video_frame_label = QtWidgets.QLabel(self)
        self.audio_selection_label = QtWidgets.QLabel(self)

        self.addPermanentWidget(self.video_frame_label)
        self.addPermanentWidget(self.audio_selection_label)

        api.video.current_pts_changed.connect(self._video_current_pts_changed)
        api.audio.selection_changed.connect(self._audio_selection_changed)

    def _video_current_pts_changed(self):
        self.video_frame_label.setText(
            'Video frame: {} ({:.1%})'.format(
                bubblesub.util.ms_to_str(self._api.video.current_pts),
                self._api.video.current_pts / max(1, self._api.video.max_pts)))

    def _audio_selection_changed(self):
        if len(self._api.subs.selected_lines) != 1:
            return
        sub = self._api.subs.lines[self._api.subs.selected_lines[0]]
        start_delta = self._api.audio.selection_start - sub.start
        end_delta = self._api.audio.selection_end - sub.end

        self.audio_selection_label.setText(
            'Audio selection: {:+.0f} ms / {:+.0f} ms (duration: {})'.format(
                start_delta,
                end_delta,
                bubblesub.util.ms_to_str(self._api.audio.selection_size)))
