from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtOpenGL import QGLContext
from PyQt5.QtWidgets import QOpenGLWidget


def get_proc_address(proc):
    glctx = QGLContext.currentContext()
    if glctx is None:
        return None
    addr = glctx.getProcAddress(str(proc, 'utf-8'))
    return addr.__int__()


class MpvWidget(QOpenGLWidget):
    _schedule_update = QtCore.pyqtSignal()

    def __init__(self, opengl_context, parent=None):
        super().__init__(parent)
        self._opengl = opengl_context
        self._opengl.set_update_callback(self.maybe_update)
        self.frameSwapped.connect(self.swapped, QtCore.Qt.DirectConnection)
        self._schedule_update.connect(self.update)

    def shutdown(self):
        self.makeCurrent()
        if self._opengl:
            self._opengl.set_update_callback(lambda: None)
            self._opengl.uninit_gl()
        self.deleteLater()

    def initializeGL(self):
        if self._opengl:
            self._opengl.init_gl(None, get_proc_address)

    def paintGL(self):
        if self._opengl:
            self._opengl.draw(
                self.defaultFramebufferObject(),
                round(self.width() * self.devicePixelRatioF()),
                round(-self.height() * self.devicePixelRatioF()))

    @QtCore.pyqtSlot()
    def swapped(self):
        if self._opengl:
            self._opengl.report_flip(0)

    def maybe_update(self):
        self._schedule_update.emit()
