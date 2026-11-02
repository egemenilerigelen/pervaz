"""Sağ kenarda duran, ekranın içine göçmüş gibi çizilen koyu kahve tutamaç.

Tutamaç bir çıkıntı değil, kenardaki sığ bir girintidir: uçları kenarda sönerek başlar, ortada en
derin yerine iner. Panel kara delik efektiyle bu noktadan çıkar ve buraya girer (bkz.
`core/panel/blackhole.py`).

Yalnızca tutamacın kendi alanı fareyi yakalar; ekranın geri kalan sağ kenarı (ör.
maksimize bir pencerenin kaydırma çubuğu) etkilenmez. Tamamen olay tabanlıdır.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QScreen,
)
from PySide6.QtWidgets import QWidget

from pervaz.core.settings import Settings
from pervaz.core.trigger.base import Trigger
from pervaz.theme import Look
from pervaz.theme.tokens import HOLE

IDLE_OPACITY = 0.8  # dikkat çekmesin diye masaüstüyle hafifçe karışır
HOVER_OPACITY = 1.0
TAPER = 0.26  # girintinin uçlarının kenarda sönme uzunluğu (boya oranla)


def _alpha(color: str, alpha: float) -> QColor:
    result = QColor(color)
    result.setAlphaF(alpha)
    return result


def dent_path(width: float, height: float) -> QPainterPath:
    """Girintinin ağzı: uçlarda sağ kenara iner, ortada `width` kadar içeri girer."""
    path = QPainterPath(QPointF(width, 0))
    middle = height / 2
    taper = height * TAPER
    path.cubicTo(width, taper, 0, taper, 0, middle)
    path.cubicTo(0, height - taper, width, height - taper, width, height)
    return path


class _HandleWidget(QWidget):
    def __init__(self, owner: HandleTrigger) -> None:
        super().__init__()
        self._owner = owner
        self._hover = False
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, event: QEvent) -> None:
        self._hover = True
        self.update()
        self._owner.hovered.emit(self._owner.screen, True)

    def leaveEvent(self, event: QEvent) -> None:
        self._hover = False
        self.update()
        self._owner.hovered.emit(self._owner.screen, False)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._owner.activated.emit(self._owner.screen)

    def paintEvent(self, event) -> None:
        width, height = float(self.width()), float(self.height())
        dent = dent_path(width, height)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(HOVER_OPACITY if self._hover else IDLE_OPACITY)

        # Duvar kenardan içeri doğru koyulaşır: dip, ekranın içinde kalan taraftır.
        wall = QLinearGradient(QPointF(0, 0), QPointF(width, 0))
        wall.setColorAt(0.0, QColor(HOLE.body))
        wall.setColorAt(1.0, QColor(HOLE.deep))
        painter.fillPath(dent, wall)

        # Girinti ışığı yukarıdan alır: üst ağız gölgede, alt ağız hafif aydınlık kalır.
        lip = QLinearGradient(QPointF(0, 0), QPointF(0, height))
        lip.setColorAt(0.0, _alpha(HOLE.void, 0.9))
        lip.setColorAt(0.5, _alpha(HOLE.void, 0.5))
        lip.setColorAt(1.0, QColor(HOLE.rim))
        painter.setPen(QPen(lip, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(dent)


class HandleTrigger(Trigger):
    def __init__(self) -> None:
        super().__init__()
        self._widget = _HandleWidget(self)
        self.screen: QScreen | None = None
        self._thickness = 6
        self._length = 96
        self._position = 0.5

    def configure(self, settings: Settings, look: Look) -> None:
        self._thickness = settings.handle_thickness
        self._length = settings.handle_length
        self._position = settings.handle_position
        if self.screen is not None and self._widget.isVisible():
            self._place(self.screen)

    def show_on(self, screen: QScreen) -> None:
        self.screen = screen
        self._place(screen)
        self._widget.show()

    def hide(self) -> None:
        self._widget.hide()

    def anchor_on(self, screen: QScreen) -> QPoint:
        rect = self._rect_on(screen)
        return QPoint(rect.x() + rect.width(), rect.y() + rect.height() // 2)

    def _rect_on(self, screen: QScreen) -> QRect:
        work = screen.availableGeometry()
        full = screen.geometry()
        length = min(self._length, work.height())
        y = work.top() + round((work.height() - length) * self._position)
        return QRect(full.x() + full.width() - self._thickness, y, self._thickness, length)

    def _place(self, screen: QScreen) -> None:
        self._widget.setGeometry(self._rect_on(screen))

    def shutdown(self) -> None:
        self._widget.hide()
        self._widget.deleteLater()
