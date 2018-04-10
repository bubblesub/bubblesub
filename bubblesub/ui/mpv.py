import typing as T

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import QtOpenGL


def get_proc_address(proc: T.Any) -> T.Optional[int]:
    glctx = QtOpenGL.QGLContext.currentContext()
    if glctx is None:
        return None
    addr = glctx.getProcAddress(str(proc, 'utf-8'))
    return T.cast(int, addr.__int__())


class MpvWidget(QtWidgets.QOpenGLWidget):
    _schedule_update = QtCore.pyqtSignal()

    def __init__(
            self,
            opengl_context: QtGui.QOpenGLContext,
            parent: T.Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._opengl = opengl_context
        self._opengl.set_update_callback(self.maybe_update)
        self.frameSwapped.connect(self.swapped, QtCore.Qt.DirectConnection)
        self._schedule_update.connect(self.update)

    def shutdown(self) -> None:
        self.makeCurrent()
        if self._opengl:
            self._opengl.set_update_callback(lambda: None)
            self._opengl.uninit_gl()
        self.deleteLater()

    def initializeGL(self) -> None:
        if self._opengl:
            self._opengl.init_gl(None, get_proc_address)

    def paintGL(self) -> None:
        if self._opengl:
            self._opengl.draw(
                self.defaultFramebufferObject(),
                round(self.width() * self.devicePixelRatioF()),
                round(-self.height() * self.devicePixelRatioF()))

    @QtCore.pyqtSlot()
    def swapped(self) -> None:
        if self._opengl:
            self._opengl.report_flip(0)

    def maybe_update(self) -> None:
        self._schedule_update.emit()
