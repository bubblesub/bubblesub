import bubblesub.api.gui
import bubblesub.api.audio
import bubblesub.api.video
import bubblesub.api.subs


class Api:
    def __init__(self):
        super().__init__()
        self.gui = bubblesub.api.gui.GuiApi()
        self.audio = bubblesub.api.audio.AudioApi()
        self.video = bubblesub.api.video.VideoApi(self.gui, self.audio)  # TODO: reverse this
        self.subs = bubblesub.api.subs.SubtitlesApi(self.video)
