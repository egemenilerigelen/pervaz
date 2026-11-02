import math

import pytest
from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter

from pervaz.core.panel.blackhole import GRID_COLS, GRID_ROWS, BlackHoleWarp, swell, warped

W, H = 120, 300
CENTER = QPointF(W + 4, H / 2)
HORIZON = 20


def _source() -> QImage:
    image = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor("#336699"))
    return image


def _warp() -> BlackHoleWarp:
    return BlackHoleWarp(_source(), QSize(W, H), CENTER, HORIZON)


def _frame(warp: BlackHoleWarp, pull: float) -> QImage:
    image = QImage(W + 4, H, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    warp.paint(painter, pull)
    painter.end()
    return image


def test_points_stay_put_before_the_pull_and_end_in_the_hole():
    assert warped(100, 1.0, 300, 0.0) == (100, 1.0)
    assert warped(100, 1.0, 300, 1.0)[0] == 0


def test_near_points_fall_first_so_the_panel_stretches():
    reach = 300
    near, _ = warped(60, 0.0, reach, 0.4)
    far, _ = warped(240, 0.0, reach, 0.4)
    assert near / 60 < far / 240


def test_falling_points_spiral_more_the_closer_they_are():
    reach = 300
    assert warped(60, 0.0, reach, 0.5)[1] > warped(240, 0.0, reach, 0.5)[1] >= 0


@pytest.mark.parametrize("pull", [i / 20 for i in range(21)])
def test_points_never_overtake_each_other_on_a_ray(pull):
    # Sıra korunursa ağ kendi üstüne katlanmaz, görüntü yırtılmaz.
    radii = [warped(r, 0.0, 300, pull)[0] for r in range(0, 301, 10)]
    assert radii == sorted(radii)


def test_horizon_is_closed_at_both_ends_and_widest_in_the_middle():
    assert swell(0.0) == 0
    assert swell(1.0) == pytest.approx(0)
    assert swell(0.5) == 1


def test_mesh_is_the_panel_itself_before_the_pull(qapp):
    grid = _warp().vertices(0.0)
    assert len(grid) == GRID_ROWS + 1 and len(grid[0]) == GRID_COLS + 1
    assert grid[0][0] == pytest.approx((0, 0))
    assert grid[-1][-1] == pytest.approx((W, H))


def test_mesh_collapses_into_the_hole(qapp):
    for row in _warp().vertices(1.0):
        for x, y in row:
            assert math.hypot(x - CENTER.x(), y - CENTER.y()) == pytest.approx(0)


def test_opening_frame_paints_the_whole_panel_without_seams(qapp):
    image = _frame(_warp(), 0.0)
    missing = [
        (x, y)
        for y in range(H)
        for x in range(W)
        if image.pixelColor(x, y).name() != "#336699" or image.pixelColor(x, y).alpha() != 255
    ]
    assert not missing[:5]


@pytest.mark.parametrize("pull", [0.2, 0.4, 0.6])
def test_bent_panel_has_no_pinholes_between_triangles(pull, qapp):
    # Üçgenler köşe paylaşmasaydı dört yanı boyalı, tek başına saydam pikseller kalırdı.
    image = QImage(W + 4, H, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    _warp()._paint_mesh(painter, pull)
    painter.end()

    def solid(x, y):
        return image.pixelColor(x, y).alpha() > 0

    pinholes = [
        (x, y)
        for y in range(1, H - 1)
        for x in range(1, W + 3)
        if not solid(x, y)
        and solid(x - 1, y)
        and solid(x + 1, y)
        and solid(x, y - 1)
        and solid(x, y + 1)
    ]
    assert not pinholes


def test_fully_swallowed_frame_leaves_nothing_behind(qapp):
    image = _frame(_warp(), 1.0)
    assert not any(image.pixelColor(x, y).alpha() for y in range(0, H, 2) for x in range(W + 4))


def test_horizon_is_dark_while_the_hole_is_open(qapp):
    image = _frame(_warp(), 0.5)
    core = image.pixelColor(round(CENTER.x()) - 2, round(CENTER.y()))
    assert core.alpha() == 255
    assert core.lightness() < 16
