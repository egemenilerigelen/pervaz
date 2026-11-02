"""Sağ kenardaki tutamaçtan kara delik efektiyle çıkan çerçevesiz panel penceresi.

Panel ekran kenarlarına değmez: üst, alt ve sağdan neredeyse yapışık, kıl payı bir boşlukla,
yuvarlak köşeli yüzen bir kart gibi durur. Pencerenin kendisi görünen kartın boyutundadır; zemin
ve köşeler `PanelSurface` tarafından çizilir.

Animasyon boyunca gerçek yüzey pencerenin dışında bekler ve pencere yüzeyin bir görüntüsünü
`BlackHoleWarp` ile büker. Pencere bu sürede tutamaca kadar genişler, ekranın dışına taşmaz. Bitişte
yüzey yerine döner; görüntü aynı olduğu için geçiş görünmez ve boşta bir şey çizilmez.
"""

from __future__ import annotations

from PySide6.QtCore import Property as QtProperty
from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QImage, QPainter, QScreen
from PySide6.QtWidgets import QVBoxLayout, QWidget

from pervaz.core.cards.host import CardHost
from pervaz.core.panel.blackhole import BlackHoleWarp
from pervaz.core.panel.header import HeaderBar
from pervaz.core.panel.surface import PanelSurface
from pervaz.core.settings import Settings
from pervaz.core.widgets import AutoHideScrollArea
from pervaz.theme import Look

PANEL_MARGIN = 2  # kartın ekran kenarlarından uzaklığı (mantıksal px, yoğunlukla ölçeklenir)
HORIZON_RADIUS = 30  # olay ufkunun en geniş yarıçapı (mantıksal px, yoğunlukla ölçeklenir)
WARP_TIME_SCALE = 2  # efekt okunsun diye süre `animation_ms` değerinin bu katıdır


class PanelWindow(QWidget):
    shown = Signal()
    hidden = Signal()
    pin_clicked = Signal()

    def __init__(self, look: Look, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Durum paneli")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # görev çubuğunda görünmez
            | Qt.WindowType.WindowDoesNotAcceptFocus  # başka uygulamanın odağını çalmaz
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._look = look
        self._settings = settings
        self._open = False
        self._pull = 1.0  # 0 = panel yerinde, 1 = tamamen delikte
        self._warp: BlackHoleWarp | None = None
        self._width = settings.panel_width
        self._height = 600
        self._margin = look.metrics.sp(PANEL_MARGIN)
        self._right = 0  # kartın sağ kenarı (ekran kenarından `_margin` içeride)
        self._top = 0
        self._anchor = QPoint(0, 0)  # panelin çıkıp girdiği nokta (ekran koordinatı)

        self._surface = PanelSurface(look, self)
        sp = look.metrics.sp
        root = QVBoxLayout(self._surface)
        root.setContentsMargins(sp(14), sp(8), sp(8), sp(8))
        root.setSpacing(sp(4))

        self.header = HeaderBar(look)
        self.header.pin_clicked.connect(self.pin_clicked)
        root.addWidget(self.header)

        self._scroll = AutoHideScrollArea()
        inner = QWidget()
        self._column = QVBoxLayout(inner)
        self._column.setContentsMargins(0, 0, 0, 0)  # çubuğun yeri kaydırma alanında ayrılı
        self._column.setSpacing(sp(8))
        self._column.addStretch(1)
        self._scroll.setWidget(inner)
        root.addWidget(self._scroll, 1)

        self._anim = QPropertyAnimation(self, b"pull", self)
        self._anim.finished.connect(self._on_anim_finished)

        self.setStyleSheet(look.stylesheet)

    # --- Animasyon özelliği -------------------------------------------------

    def _get_pull(self) -> float:
        return self._pull

    def _set_pull(self, value: float) -> None:
        self._pull = value
        self.update()

    pull = QtProperty(float, _get_pull, _set_pull)

    def paintEvent(self, event) -> None:
        if self._warp is not None:
            self._warp.paint(QPainter(self), self._pull)

    # --- Dış arayüz ---------------------------------------------------------

    @property
    def is_open(self) -> bool:
        return self._open

    def target_rect(self) -> QRect:
        """Panelin tamamen açık haldeki etkileşim alanı (animasyondan bağımsız).

        Kartın etrafındaki boşluğu da kapsar: fare ekran kenarına kaydığında panelden
        çıkmış sayılmaz.
        """
        left = self._right - self._width
        return QRect(
            left,
            self._top - self._margin,
            self._width + self._margin,
            self._height + 2 * self._margin,
        )

    def add_host(self, host: CardHost) -> None:
        self._column.insertWidget(self._column.count() - 1, host)

    def set_pinned(self, pinned: bool) -> None:
        self.header.set_pinned(pinned)

    def set_look(self, look: Look) -> None:
        self._look = look
        self.setStyleSheet(look.stylesheet)
        self._surface.set_look(look)

    def open_on(self, screen: QScreen, anchor: QPoint | None = None) -> None:
        """Paneli `screen` üzerinde açar; `anchor` verilmezse sağ kenarın ortasından çıkar."""
        work = screen.availableGeometry()
        # Yazı ölçeği büyüdükçe panel de orantılı genişler.
        self._width = round(self._settings.panel_width * max(1.0, self._look.metrics.font))
        self._margin = self._look.metrics.sp(PANEL_MARGIN)
        self._height = work.height() - 2 * self._margin
        self._right = work.x() + work.width() - self._margin
        self._top = work.y() + self._margin
        if anchor is None:
            anchor = QPoint(work.x() + work.width(), work.y() + work.height() // 2)
        self._anchor = anchor
        self._surface.setFixedSize(self._width, self._height)

        was_open = self._open
        self._open = True
        if not was_open:
            self.header.start()
        if self._settings.animations and not was_open:
            self._begin_warp()
            self.show()
            self._start_animation(0.0, QEasingCurve.Type.OutCubic)
        else:
            self._anim.stop()
            self._settle()
            self.show()
            self.shown.emit()

    def close_panel(self) -> None:
        if not self._open:
            return
        self._open = False
        self.header.stop()
        if self._settings.animations and self.isVisible():
            self._begin_warp()
            self._start_animation(1.0, QEasingCurve.Type.InCubic)
        else:
            self._anim.stop()
            self.hide()
            self._settle()
            self.hidden.emit()

    # --- İç işleyiş ---------------------------------------------------------

    def _panel_rect(self) -> QRect:
        return QRect(self._right - self._width, self._top, self._width, self._height)

    def _begin_warp(self) -> None:
        """Yüzeyin görüntüsünü alır; animasyon boyunca çizimi pencere devralır."""
        rect = self._panel_rect()
        self._warp = BlackHoleWarp(
            self._snapshot(),
            QSize(self._width, self._height),
            QPointF(self._anchor - rect.topLeft()),
            self._look.metrics.sp(HORIZON_RADIUS),
        )
        self._surface.move(-2 * self._width, 0)
        rect.setRight(max(rect.right(), self._anchor.x() - 1))
        self.setGeometry(rect)

    def _snapshot(self) -> QImage:
        """Aygıt pikseli cinsinden yüzey görüntüsü.

        `grab()` pencere zeminini de boyadığı için yuvarlak köşeler saydam kalmaz; zeminsiz çizilir.
        """
        ratio = self.devicePixelRatioF()
        size = QSize(round(self._width * ratio), round(self._height * ratio))
        image = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(ratio)
        image.fill(Qt.GlobalColor.transparent)
        self._surface.render(image, renderFlags=QWidget.RenderFlag.DrawChildren)
        image.setDevicePixelRatio(1.0)
        return image

    def _settle(self) -> None:
        """Gerçek yüzeyi yerine koyar, pencereyi kart boyutuna döndürür."""
        self._warp = None
        self._surface.move(0, 0)
        self.setGeometry(self._panel_rect())
        self._pull = 0.0 if self._open else 1.0

    def _start_animation(self, end: float, curve: QEasingCurve.Type) -> None:
        """Yarıda tersine dönen animasyon, kalan yolu oranlı sürede tamamlar."""
        self._anim.stop()
        full = self._settings.animation_ms * WARP_TIME_SCALE
        self._anim.setDuration(max(1, round(full * abs(end - self._pull))))
        self._anim.setEasingCurve(curve)
        self._anim.setStartValue(self._pull)
        self._anim.setEndValue(end)
        self._anim.start()

    def _on_anim_finished(self) -> None:
        if self._open:
            self._settle()
            self.shown.emit()
        else:
            self.hide()
            self._settle()
            self.hidden.emit()
