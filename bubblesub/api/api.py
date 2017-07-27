import bubblesub.api.gui
import bubblesub.api.audio
import bubblesub.api.video
import bubblesub.api.subs


class Api:
    def __init__(self):
        super().__init__()
        self.audio = bubblesub.api.audio.AudioApi()
        self.video = bubblesub.api.video.VideoApi(self.audio)  # TODO: reverse this
        self.gui = bubblesub.api.gui.GuiApi()
        self.subs = bubblesub.api.subs.SubtitlesApi(self.video)

    def log(self, text):
        print(text)  # TODO: log to GUI console via events
