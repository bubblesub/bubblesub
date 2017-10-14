from PyQt5 import QtCore
from bubblesub.ui.mpv import MpvWidget


class Video(MpvWidget):
    def __init__(self, api, parent=None):
        super().__init__(api.video.get_opengl_context(), parent)
        # TODO: buttons for play/pause like aegisub

    def sizeHint(self):
        return QtCore.QSize(400, 300)
