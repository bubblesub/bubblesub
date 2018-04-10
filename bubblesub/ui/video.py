from PyQt5 import QtCore
from PyQt5 import QtWidgets

import bubblesub.api
from bubblesub.ui.mpv import MpvWidget


class VideoPreview(MpvWidget):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget = None,
    ) -> None:
        super().__init__(api.media.video.get_opengl_context(), parent)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(400, 300)


class Video(QtWidgets.QWidget):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget = None,
    ) -> None:
        super().__init__(parent)

        self._api = api

        self._video_preview = VideoPreview(api, self)
        self._volume_slider = QtWidgets.QSlider()
        self._volume_slider.setMinimum(0)
        self._volume_slider.setMaximum(200)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._volume_slider)
        layout.addWidget(self._video_preview)

        self._connect_signals()
        self._on_video_volume_change()

        # TODO: buttons for play/pause like aegisub

    def shutdown(self) -> None:
        self._video_preview.shutdown()

    def _connect_signals(self) -> None:
        self._volume_slider.valueChanged.connect(
            self._on_volume_slider_value_change)
        self._api.media.volume_changed.connect(self._on_video_volume_change)

    def _disconnect_signals(self) -> None:
        self._volume_slider.valueChanged.disconnect(
            self._on_volume_slider_value_change)
        self._api.media.volume_changed.disconnect(self._on_video_volume_change)

    def _on_video_volume_change(self) -> None:
        self._disconnect_signals()
        self._volume_slider.setValue(int(self._api.media.volume))
        self._connect_signals()

    def _on_volume_slider_value_change(self) -> None:
        self._api.media.volume = self._volume_slider.value()
