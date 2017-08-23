import bubblesub.api.log
import bubblesub.api.gui
import bubblesub.api.audio
import bubblesub.api.video
import bubblesub.api.subs
import bubblesub.api.undo
import bubblesub.api.cmd


class Api:
    def __init__(self, opt):
        super().__init__()
        self.opt = opt
        self.log = bubblesub.api.log.LogApi()
        self.gui = bubblesub.api.gui.GuiApi(self)
        self.subs = bubblesub.api.subs.SubtitlesApi()
        self.video = bubblesub.api.video.VideoApi(self.subs, self.log, self.opt)
        self.audio = bubblesub.api.audio.AudioApi(self.video, self.log)
        self.undo = bubblesub.api.undo.UndoApi(self.subs)
        self.cmd = bubblesub.api.cmd.CommandApi(self)
