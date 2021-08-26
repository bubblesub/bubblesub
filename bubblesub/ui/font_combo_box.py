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

from PyQt5.QtCore import QModelIndex, QObject, QRect, QSize, Qt
from PyQt5.QtGui import (
    QFont,
    QFontDatabase,
    QFontInfo,
    QFontMetrics,
    QIcon,
    QPainter,
    QPen,
)
from PyQt5.QtWidgets import (
    QAbstractItemDelegate,
    QComboBox,
    QStyle,
    QStyleOptionViewItem,
    QWidget,
)

from bubblesub.api import Api
from bubblesub.ui.assets import ASSETS_DIR


def refresh_font_db() -> None:
    # XXX:
    # Qt doesn't expose API to refresh the fonts, so we try to trick it into
    # invalidating its internal database by adding a dummy application font.
    # On Linux, this works with `fc-cache -r`.
    font_db = QFontDatabase()
    font_db.addApplicationFont(str(ASSETS_DIR / "AdobeBlank.ttf"))
    font_db.removeAllApplicationFonts()


def _get_font_families() -> list[str]:
    return list(
        sorted(
            {
                family
                if " [" not in family
                else family[0 : family.index(" [")]
                for family in QFontDatabase().families()
            }
        )
    )


class _FontFamilyDelegate(QAbstractItemDelegate):
    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self.truetype = QIcon(
            ":/qt-project.org/styles/commonstyle/images/fonttruetype-16.png"
        )
        self.bitmap = QIcon(
            ":/qt-project.org/styles/commonstyle/images/fontbitmap-16.png"
        )
        self.sample_text = "abc123"

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        idx: QModelIndex,
    ) -> None:
        font_family = idx.data(Qt.DisplayRole)
        font = QFont(option.font)
        font.setPointSize(QFontInfo(font).pointSize() * 3 / 2)
        font2 = QFont(font)
        font2.setFamily(font_family)

        if option.state & QStyle.State_Selected:
            painter.save()
            painter.setBrush(option.palette.highlight())
            painter.setPen(Qt.NoPen)
            painter.drawRect(option.rect)
            painter.setPen(QPen(option.palette.highlightedText(), 0))

        icon = self.bitmap
        if QFontDatabase().isSmoothlyScalable(font_family):
            icon = self.truetype
        actual_size = icon.actualSize(option.rect.size())

        icon.paint(painter, option.rect, Qt.AlignLeft | Qt.AlignVCenter)
        if option.direction == Qt.RightToLeft:
            option.rect.setRight(option.rect.right() - actual_size.width() - 4)
        else:
            option.rect.setLeft(option.rect.left() + actual_size.width() + 4)

        half1 = QRect(option.rect)
        half2 = QRect(option.rect)
        half1.setRight(half1.right() / 2)
        half2.setLeft(half1.right())

        painter.drawText(
            half1,
            Qt.AlignVCenter | Qt.AlignLeading | Qt.TextSingleLine,
            font_family,
        )

        old = painter.font()
        painter.setFont(font2)
        painter.drawText(
            half2,
            Qt.AlignVCenter | Qt.AlignLeading | Qt.TextSingleLine,
            self.sample_text,
        )
        painter.setFont(old)

        if option.state & QStyle.State_Selected:
            painter.restore()

    def sizeHint(
        self, option: QStyleOptionViewItem, idx: QModelIndex
    ) -> QSize:
        font_family = idx.data(Qt.DisplayRole)
        font = QFont(option.font)
        font.setPointSize(QFontInfo(font).pointSize() * 3 / 2)
        metrics = QFontMetrics(font)
        box = metrics.boundingRect(font_family + self.sample_text)
        w = box.width()
        h = metrics.height()

        return QSize(w, h)


class FontComboBox(QComboBox):
    def __init__(self, api: Api, parent: QWidget) -> None:
        super().__init__(
            parent,
            editable=True,
            insertPolicy=QComboBox.NoInsert,
            sizeAdjustPolicy=(QComboBox.AdjustToMinimumContentsLengthWithIcon),
        )
        self.addItems(_get_font_families())
        if api.cfg.opt["gui"]["preview_fonts"]:
            self.setItemDelegate(_FontFamilyDelegate(self))
            self.setStyleSheet(
                "QComboBox QAbstractItemView { min-width: 800px; }"
            )

    def set_sample_text(self, text: str) -> None:
        self.itemDelegate().sample_text = text
