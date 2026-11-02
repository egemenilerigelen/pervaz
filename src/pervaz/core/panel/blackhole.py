"""Kara delik efekti: panelin görüntüsü tutamaçtaki noktaya sarmal çizerek düşer.

Panel açılıp kapanırken gerçek kartlar değil, onların bir kez alınmış görüntüsü çizilir. Görüntü
bir ağa (`GRID_COLS` x `GRID_ROWS`) bölünür, her göz iki üçgen olarak bükülmüş yerine boyanır:

- gelgit: deliğe yakın noktalar önce düşer, uzak kenar geride kalıp uzar,
- sarmal: düşen nokta dönerek yaklaşır; iç kısım önde gittiği için kollar oluşur,
- kızıla kayma: delik çevresindeki içerik koyu kahveye boğulur,
- olay ufku: delik emilimin ortasında şişer, baş ve sonda tutamacın içinde kaybolur.

Üçgenler aynı köşeleri paylaştığı için aralarında çizgi kalmaz. Hesap saf Python olduğu için ağ
kaba tutulur; kare başına süre panel boyutuna değil, ağ yoğunluğuna bağlıdır.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QPainter,
    QPen,
    QPolygonF,
    QRadialGradient,
    QTransform,
)

from pervaz.theme.tokens import HOLE

GRID_COLS = 12
GRID_ROWS = 34
TIDE = 1.1  # uzak kenarın ne kadar geç düşmeye başladığı
SWIRL = 1.6  # düşüş boyunca toplam dönüş (radyan); fazlası paneli ekran dışına savurur
FALL_POWER = 1.4  # yarıçapın düşüşle küçülme hızı
MIN_CELL_SPAN = 0.4  # bundan küçük gözler (mantıksal px) çizilmez
REDSHIFT_REACH = 0.42  # koyulaşmanın uzanımı (panel uzaklığına oranla)
REDSHIFT_ALPHA = 0.9
RING_AT = 0.8  # foton halkasının ufuk yarıçapına oranla yeri
ARC_AT = 1.12  # savrulan yayların ufuk yarıçapına oranla yeri
ARC_SPAN = 70  # derece
ARC_TURNS = 2  # emilim boyunca yayların tur sayısı


def _alpha(color: str, alpha: float) -> QColor:
    result = QColor(color)
    result.setAlphaF(max(0.0, min(1.0, alpha)))
    return result


def warped(radius: float, angle: float, reach: float, pull: float) -> tuple[float, float]:
    """Deliğe göre kutupsal (`radius`, `angle`) noktasının `pull` anındaki yeni yeri.

    `pull` 0 iken nokta yerindedir, 1 iken delikte; `reach` panelin en uzak noktasının uzaklığıdır.
    """
    progress = max(0.0, min(1.0, pull * (1 + TIDE) - TIDE * radius / reach))
    fall = progress * progress * (3 - 2 * progress)
    return radius * (1 - fall) ** FALL_POWER, angle + SWIRL * fall * fall


def swell(pull: float) -> float:
    """Olay ufkunun açıklığı: emilimin ortasında 1, başında ve sonunda 0."""
    return math.sin(math.pi * max(0.0, min(1.0, pull)))


class BlackHoleWarp:
    """Bir panel görüntüsünü `center` noktasına emdiren çizici.

    `image` aygıt pikseli cinsindendir, `size` ve `center` pencerenin mantıksal koordinatlarıdır.
    """

    def __init__(self, image: QImage, size: QSize, center: QPointF, horizon: float) -> None:
        self._center = center
        self._horizon = horizon
        self._brush = QBrush(image)
        self._du = image.width() / GRID_COLS
        self._dv = image.height() / GRID_ROWS

        width, height = size.width(), size.height()
        self._reach = max(
            math.hypot(center.x() - x, center.y() - y) for x in (0, width) for y in (0, height)
        )
        self._polar = [
            [
                self._to_polar(width * col / GRID_COLS, height * row / GRID_ROWS)
                for col in range(GRID_COLS + 1)
            ]
            for row in range(GRID_ROWS + 1)
        ]
        # Üçgenler görüntü koordinatındadır; her biri kendi dönüşümüyle yerine taşınır.
        self._upper = [
            [self._triangle(col, row, (0, 0), (1, 0), (0, 1)) for col in range(GRID_COLS)]
            for row in range(GRID_ROWS)
        ]
        self._lower = [
            [self._triangle(col, row, (1, 0), (1, 1), (0, 1)) for col in range(GRID_COLS)]
            for row in range(GRID_ROWS)
        ]

    def _to_polar(self, x: float, y: float) -> tuple[float, float]:
        dx, dy = x - self._center.x(), y - self._center.y()
        return math.hypot(dx, dy), math.atan2(dy, dx)

    def _triangle(self, col: int, row: int, *corners: tuple[int, int]) -> QPolygonF:
        return QPolygonF(
            [QPointF((col + x) * self._du, (row + y) * self._dv) for x, y in corners],
        )

    def vertices(self, pull: float) -> list[list[tuple[float, float]]]:
        """Ağın köşelerinin `pull` anındaki yerleri (mantıksal px)."""
        cx, cy = self._center.x(), self._center.y()
        result = []
        for row in self._polar:
            points = []
            for radius, angle in row:
                new_radius, new_angle = warped(radius, angle, self._reach, pull)
                points.append(
                    (cx + new_radius * math.cos(new_angle), cy + new_radius * math.sin(new_angle))
                )
            result.append(points)
        return result

    def paint(self, painter: QPainter, pull: float) -> None:
        self._paint_mesh(painter, pull)
        painter.resetTransform()
        self._paint_redshift(painter, pull)
        self._paint_horizon(painter, pull)

    def _paint_mesh(self, painter: QPainter, pull: float) -> None:
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._brush)
        grid = self.vertices(pull)
        du, dv = self._du, self._dv
        for row in range(GRID_ROWS):
            top, bottom = grid[row], grid[row + 1]
            v0 = row * dv
            for col in range(GRID_COLS):
                ax, ay = top[col]
                bx, by = top[col + 1]
                cx, cy = bottom[col]
                dx, dy = bottom[col + 1]
                if abs(bx - cx) + abs(by - cy) + abs(dx - ax) + abs(dy - ay) < MIN_CELL_SPAN:
                    continue
                u0, u1 = col * du, (col + 1) * du
                m11, m12 = (bx - ax) / du, (by - ay) / du
                m21, m22 = (cx - ax) / dv, (cy - ay) / dv
                painter.setWorldTransform(
                    QTransform(
                        m11, m12, m21, m22, ax - m11 * u0 - m21 * v0, ay - m12 * u0 - m22 * v0
                    )
                )
                painter.drawConvexPolygon(self._upper[row][col])
                m11, m12 = (dx - cx) / du, (dy - cy) / du
                m21, m22 = (dx - bx) / dv, (dy - by) / dv
                painter.setWorldTransform(
                    QTransform(
                        m11, m12, m21, m22, bx - m11 * u1 - m21 * v0, by - m12 * u1 - m22 * v0
                    )
                )
                painter.drawConvexPolygon(self._lower[row][col])

    def _paint_redshift(self, painter: QPainter, pull: float) -> None:
        """Yalnızca panelin boyandığı yerleri, deliğe yaklaştıkça koyu kahveye boğar."""
        reach = self._reach * REDSHIFT_REACH
        strength = REDSHIFT_ALPHA * min(1.0, pull * 2)
        gradient = QRadialGradient(self._center, reach)
        gradient.setColorAt(0.0, _alpha(HOLE.void, strength))
        gradient.setColorAt(0.45, _alpha(HOLE.body, strength * 0.55))
        gradient.setColorAt(1.0, _alpha(HOLE.body, 0.0))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        painter.fillRect(
            QRectF(self._center.x() - reach, self._center.y() - reach, 2 * reach, 2 * reach),
            gradient,
        )
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    def _paint_horizon(self, painter: QPainter, pull: float) -> None:
        opening = swell(pull)
        radius = self._horizon * opening
        if radius < 1:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QRadialGradient(self._center, radius)
        gradient.setColorAt(0.0, _alpha(HOLE.void, 1.0))
        gradient.setColorAt(RING_AT - 0.14, _alpha(HOLE.void, 1.0))
        gradient.setColorAt(RING_AT - 0.04, _alpha(HOLE.deep, 1.0))
        gradient.setColorAt(RING_AT, _alpha(HOLE.glow, 0.75))
        gradient.setColorAt(RING_AT + 0.06, _alpha(HOLE.rim, 0.45))
        gradient.setColorAt(1.0, _alpha(HOLE.rim, 0.0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(self._center, radius, radius)

        arc = radius * ARC_AT
        box = QRectF(self._center.x() - arc, self._center.y() - arc, 2 * arc, 2 * arc)
        turn = round(pull * ARC_TURNS * 360 * 16)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(_alpha(HOLE.glow, 0.55 * opening), max(1.0, self._horizon * 0.06)))
        for offset in (0, 180):
            painter.drawArc(box, turn + offset * 16, -ARC_SPAN * 16)
