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
    def __init__(self, opengl_context, parent=None):
        super().__init__(parent)
        self._opengl = opengl_context
        self._opengl.set_update_callback(self.updateHandler)
        self.frameSwapped.connect(
            self.swapped, QtCore.Qt.DirectConnection)

    def shutdown(self):
        self.makeCurrent()
        if self._opengl:
            self._opengl.set_update_callback(None)
        self._opengl.uninit_gl()
        self.deleteLater()

    def initializeGL(self):
        if self._opengl:
            self._opengl.init_gl(None, get_proc_address)

    def paintGL(self):
        if self._opengl:
            self._opengl.draw(
                self.defaultFramebufferObject(),
                self.width(),
                -self.height())

    @QtCore.pyqtSlot()
    def swapped(self):
        if self._opengl:
            self._opengl.report_flip(0)

    def updateHandler(self):
        if self.window().isMinimized():
            self.makeCurrent()
            self.paintGL()
            self.context().swapBuffers(self.context().surface())
            self.swapped()
            self.doneCurrent()
        else:
            self.update()
