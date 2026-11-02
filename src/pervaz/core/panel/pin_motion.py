"""Raptiye efekti: panel, sağ üstteki düğmenin yerine gerçekten çakılıyormuş gibi davranır.

Sabitlerken raptiye düğmeden havaya kalkar, panele saplanır (halka yayılır) ve panel o noktadan
asılı kalmış gibi kendi ağırlığıyla sallanıp durulur. Sabitleme kalkarken raptiye sökülür, panel
hafifçe sarsılır. Raptiye hep yerinde durur; dönen yalnızca panelin görüntüsüdür.

Panel tek yöne sallanır: sol kenarın ekranın üstüne çıkmasını ve pencerenin sola büyütülmesini
gerektiren ters salınım yoktur, pencerenin sol üst köşesi hiç kıpırdamaz.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)

from pervaz.theme import Look
from pervaz.theme.tokens import ICON_FONT, blend, shade_for

PIN_GLYPH = ""
PINNED_GLYPH = ""

PEAK_SCALE = 3.0  # raptiyenin havadayken görünen büyüklüğü
PEAK_TILT = -32.0  # havadayken eğimi (derece)
PEAK_LIFT = 0.55  # havadayken yerinden sola kayması (ikon boyuna oranla, gölge payı için)
SHADOW_ALPHA = 0.45
RING_RADIUS = 46.0  # saplanma halkasının ulaştığı yarıçap (mantıksal px)
RING_SPAN = 0.42  # halkanın ömrü (salınım süresine oranla)

LIFT_END = 0.2  # sabitlerken: raptiye en yüksekte
STRIKE_AT = 0.32  # sabitlerken: panele saplandığı an
PIN_SWING = 4.0  # salınım çarpanıyla birlikte en çok ~1,7 derece döner
YANK_END = 0.16  # sökerken: raptiye en yüksekte
LAND_AT = 0.62  # sökerken: raptiye düğmeye döndü
RELEASE_SWING = 1.2  # sökerken panelin sarsıntısı (aynı çarpanla, ~0,5 derece)
SWAY_DECAY = 3.2
SWAY_COUNT = 2.5  # durulana dek salınım sayısı


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _ease_out(value: float) -> float:
    return 1 - (1 - value) ** 3


def _ease_in(value: float) -> float:
    return value**3


def sway(progress: float) -> float:
    """Salınım çarpanı: başta ve sonda 0, ağırlıkla sarkar, hiç eksiye geçmez."""
    x = _clamp(progress)
    return math.exp(-SWAY_DECAY * x) * math.sin(math.pi * SWAY_COUNT * x) ** 2 * (1 - x)


def height(pinning: bool, t: float) -> float:
    """Raptiyenin panelden yüksekliği: 0 = saplı (ya da düğmede), 1 = en yüksekte."""
    rise_end, fall_end = (LIFT_END, STRIKE_AT) if pinning else (YANK_END, LAND_AT)
    if t < rise_end:
        return _ease_out(t / rise_end)
    if t < fall_end:
        progress = (t - rise_end) / (fall_end - rise_end)
        return 1 - (_ease_in(progress) if pinning else progress * progress * (3 - 2 * progress))
    return 0.0


def angle(pinning: bool, t: float) -> float:
    """Panelin raptiye çevresindeki dönüşü (derece); pozitif = saat yönünün tersi."""
    if pinning:
        return PIN_SWING * sway((t - STRIKE_AT) / (1 - STRIKE_AT))
    return RELEASE_SWING * sway(t)


def _pin_path(glyph: str, pixel_size: float) -> QPainterPath:
    """Karakterin merkezi (0, 0) olan dış hattı; ölçeklenince bulanıklaşmaz."""
    font = QFont(ICON_FONT)
    font.setPixelSize(max(1, round(pixel_size)))
    path = QPainterPath()
    path.addText(0, 0, font, glyph)
    center = path.boundingRect().center()
    path.translate(-center)
    return path


class PinMotion:
    """Panel görüntüsünü raptiye çevresinde döndürüp raptiyeyi üstüne çizen çizici.

    `image` aygıt pikseli cinsindendir; `rect` ve `pivot` pencerenin mantıksal koordinatlarıdır.
    """

    def __init__(
        self, image: QImage, rect: QRectF, pivot: QPointF, pinning: bool, look: Look
    ) -> None:
        self._image = image
        self._rect = rect
        self._pivot = pivot
        self._pinning = pinning
        theme = look.theme
        self._idle = theme.text_dim
        self._active = theme.accent
        self._shade = shade_for(theme.ink)
        self._base_size = look.metrics.fs(12)
        before, after = (PIN_GLYPH, PINNED_GLYPH) if pinning else (PINNED_GLYPH, PIN_GLYPH)
        self._before = _pin_path(before, self._base_size * PEAK_SCALE)
        self._after = _pin_path(after, self._base_size * PEAK_SCALE)

    def paint(self, painter: QPainter, t: float) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._paint_panel(painter, t)
        if self._pinning:
            self._paint_ring(painter, t)
        self._paint_pin(painter, t)

    def _paint_panel(self, painter: QPainter, t: float) -> None:
        painter.save()
        painter.translate(self._pivot)
        painter.rotate(-angle(self._pinning, t))
        painter.translate(-self._pivot)
        painter.drawImage(self._rect, self._image)
        painter.restore()

    def _paint_ring(self, painter: QPainter, t: float) -> None:
        progress = (t - STRIKE_AT) / ((1 - STRIKE_AT) * RING_SPAN)
        if not 0 <= progress < 1:
            return
        radius = RING_RADIUS * _ease_out(progress)
        color = QColor(self._active)
        color.setAlphaF(0.7 * (1 - progress) ** 2)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color, 1.5))
        painter.drawEllipse(self._pivot, radius, radius)

    def _paint_pin(self, painter: QPainter, t: float) -> None:
        lift = height(self._pinning, t)
        # Çizgi en yükseğe varınca yeni karaktere geçer: düşen raptiye artık son hâlidir.
        rising = t < (LIFT_END if self._pinning else YANK_END)
        path = self._before if rising else self._after
        target = 0.0 if rising else 1.0
        tone = blend(self._active, self._idle, target if self._pinning else 1 - target)

        scale = (1 + (PEAK_SCALE - 1) * lift) / PEAK_SCALE
        offset = QPointF(-PEAK_LIFT * self._base_size * lift, PEAK_LIFT * self._base_size * lift)
        center = self._pivot + offset * PEAK_SCALE * scale

        painter.save()
        painter.translate(center)
        painter.rotate(PEAK_TILT * lift)
        painter.scale(scale, scale)
        if lift > 0:
            shadow = QColor(self._shade)
            shadow.setAlphaF(SHADOW_ALPHA * lift)
            drop = self._base_size * 1.4 * lift
            painter.fillPath(path.translated(-drop * 0.6, drop), QBrush(shadow))
        box = path.boundingRect()
        fill = QLinearGradient(box.topLeft(), box.bottomRight())
        fill.setColorAt(0.0, QColor(blend("#ffffff", tone, 0.35)))
        fill.setColorAt(0.55, QColor(tone))
        fill.setColorAt(1.0, QColor(blend(self._shade, tone, 0.3)))
        painter.fillPath(path, QBrush(fill))
        painter.restore()
