# bubblesub - ASS subtitle editor
# Copyright (C) 2018 Marcin Kurczewski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import typing as T

from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.ui.assets import ASSETS_DIR


def refresh_font_db() -> None:
    # XXX:
    # Qt doesn't expose API to refresh the fonts, so we try to trick it into
    # invalidating its internal database by adding a dummy application font.
    # On Linux, this works with `fc-cache -r`.
    font_db = QtGui.QFontDatabase()
    font_db.addApplicationFont(str(ASSETS_DIR / "AdobeBlank.ttf"))
    font_db.removeAllApplicationFonts()


def _get_font_families() -> T.List[str]:
    return list(
        sorted(
            {
                family
                if " [" not in family
                else family[0 : family.index(" [")]
                for family in QtGui.QFontDatabase().families()
            }
        )
    )


class _FontFamilyDelegate(QtWidgets.QAbstractItemDelegate):
    def __init__(self, parent: QtCore.QObject) -> None:
        super().__init__(parent)
        self.truetype = QtGui.QIcon(
            ":/qt-project.org/styles/commonstyle/images/fonttruetype-16.png"
        )
        self.bitmap = QtGui.QIcon(
            ":/qt-project.org/styles/commonstyle/images/fontbitmap-16.png"
        )
        self.sample_text = "abc123"

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        idx: QtCore.QModelIndex,
    ) -> None:
        font_family = idx.data(QtCore.Qt.DisplayRole)
        font = QtGui.QFont(option.font)
        font.setPointSize(QtGui.QFontInfo(font).pointSize() * 3 / 2)
        font2 = QtGui.QFont(font)
        font2.setFamily(font_family)

        if option.state & QtWidgets.QStyle.State_Selected:
            painter.save()
            painter.setBrush(option.palette.highlight())
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(option.rect)
            painter.setPen(QtGui.QPen(option.palette.highlightedText(), 0))

        icon = self.bitmap
        if QtGui.QFontDatabase().isSmoothlyScalable(font_family):
            icon = self.truetype
        actual_size = icon.actualSize(option.rect.size())

        icon.paint(
            painter, option.rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        if option.direction == QtCore.Qt.RightToLeft:
            option.rect.setRight(option.rect.right() - actual_size.width() - 4)
        else:
            option.rect.setLeft(option.rect.left() + actual_size.width() + 4)

        half1 = QtCore.QRect(option.rect)
        half2 = QtCore.QRect(option.rect)
        half1.setRight(half1.right() / 2)
        half2.setLeft(half1.right())

        painter.drawText(
            half1,
            QtCore.Qt.AlignVCenter
            | QtCore.Qt.AlignLeading
            | QtCore.Qt.TextSingleLine,
            font_family,
        )

        old = painter.font()
        painter.setFont(font2)
        painter.drawText(
            half2,
            QtCore.Qt.AlignVCenter
            | QtCore.Qt.AlignLeading
            | QtCore.Qt.TextSingleLine,
            self.sample_text,
        )
        painter.setFont(old)

        if option.state & QtWidgets.QStyle.State_Selected:
            painter.restore()

    def sizeHint(
        self, option: QtWidgets.QStyleOptionViewItem, idx: QtCore.QModelIndex
    ) -> QtCore.QSize:
        font_family = idx.data(QtCore.Qt.DisplayRole)
        font = QtGui.QFont(option.font)
        font.setPointSize(QtGui.QFontInfo(font).pointSize() * 3 / 2)
        metrics = QtGui.QFontMetrics(font)
        box = metrics.boundingRect(font_family + self.sample_text)
        w = box.width()
        h = metrics.height()

        return QtCore.QSize(w, h)


class FontComboBox(QtWidgets.QComboBox):
    def __init__(self, api: Api, parent: QtWidgets.QWidget) -> None:
        super().__init__(
            parent,
            editable=True,
            insertPolicy=QtWidgets.QComboBox.NoInsert,
            sizeAdjustPolicy=(
                QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon
            ),
        )
        self.addItems(_get_font_families())
        if api.cfg.opt["gui"]["preview_fonts"]:
            self.setItemDelegate(_FontFamilyDelegate(self))
            self.setStyleSheet(
                "QComboBox QAbstractItemView { min-width: 800px; }"
            )

    def set_sample_text(self, text: str) -> None:
        self.itemDelegate().sample_text = text
