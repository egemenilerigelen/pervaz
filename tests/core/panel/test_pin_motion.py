import pytest
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter

from pervaz.core.panel.pin_motion import (
    LIFT_END,
    PIN_GLYPH,
    PINNED_GLYPH,
    STRIKE_AT,
    YANK_END,
    PinMotion,
    angle,
    height,
    sway,
)
from pervaz.core.panel.window import PanelWindow
from pervaz.core.settings import Settings
from pervaz.theme import resolve_look

LOOK = resolve_look("dark", "normal", 1.0)
ANIMATION_MS = 50
TIMEOUT_MS = 3000
STEPS = [i / 100 for i in range(101)]


@pytest.fixture
def panel(qtbot):
    window = PanelWindow(LOOK, Settings(animation_ms=ANIMATION_MS))
    qtbot.addWidget(window)
    window._settings = Settings(animations=False)
    window.open_on(window.screen())
    window._settings = Settings(animation_ms=ANIMATION_MS)
    return window


def _finish(qtbot, panel: PanelWindow) -> None:
    qtbot.waitUntil(lambda: panel._pin_motion is None, timeout=TIMEOUT_MS)


def test_sway_starts_and_ends_still_and_never_swings_backwards():
    assert sway(0.0) == 0
    assert sway(1.0) == 0
    assert all(sway(t) >= 0 for t in STEPS)  # pencerenin sola büyümesi gerekmez
    assert max(sway(t) for t in STEPS) > 0.1


def test_later_swings_are_smaller():
    assert sway(0.2) > sway(0.6)


def test_pin_rises_then_strikes_and_stays_in():
    assert height(True, 0.0) == 0
    assert height(True, LIFT_END) == pytest.approx(1)
    assert height(True, STRIKE_AT) == 0
    assert all(height(True, t) == 0 for t in STEPS if t >= STRIKE_AT)


def test_panel_only_moves_after_the_strike():
    assert all(angle(True, t) == 0 for t in STEPS if t <= STRIKE_AT)
    assert any(angle(True, t) > 1 for t in STEPS)
    assert angle(True, 1.0) == 0


def test_releasing_is_a_small_shake_that_ends_on_the_button():
    assert height(False, YANK_END) == pytest.approx(1)
    assert height(False, 1.0) == 0
    assert angle(False, 1.0) == 0
    pinning = max(angle(True, t) for t in STEPS)
    assert 0 < max(angle(False, t) for t in STEPS) < pinning


@pytest.mark.parametrize("pinning", [True, False])
def test_every_frame_keeps_the_panel_painted_and_the_pivot_in_place(pinning, qapp):
    width, height_px = 120, 200
    source = QImage(width, height_px, QImage.Format.Format_ARGB32_Premultiplied)
    source.fill(QColor("#336699"))
    pivot = QPointF(100, 20)
    motion = PinMotion(source, QRectF(0, 0, width, height_px), pivot, pinning, LOOK)
    for t in (0.0, 0.1, 0.4, 0.5, 1.0):
        frame = QImage(width + 20, height_px + 20, QImage.Format.Format_ARGB32_Premultiplied)
        frame.fill(Qt.GlobalColor.transparent)
        painter = QPainter(frame)
        motion.paint(painter, t)
        painter.end()
        assert frame.pixelColor(60, 100).alpha() == 255, t


def test_pinning_an_open_panel_plays_the_motion_and_settles(qtbot, panel):
    rect = panel.geometry()
    panel.set_pinned(True)
    assert panel._pin_motion is not None
    assert panel._surface.x() < 0  # gerçek kartlar görüntünün altında görünmez
    assert panel.geometry().topLeft() == rect.topLeft()  # pencere zıplamaz
    assert panel.geometry().contains(rect)
    _finish(qtbot, panel)
    assert panel._surface.pos() == QPoint(0, 0)
    assert panel.geometry() == rect


def test_motion_stays_on_the_screen(qtbot, panel):
    panel.set_pinned(True)
    assert panel.screen().geometry().contains(panel.geometry())
    _finish(qtbot, panel)


def test_unpinning_plays_the_motion_too(qtbot, panel):
    panel.set_pinned(True)
    _finish(qtbot, panel)
    panel.set_pinned(False)
    assert panel._pin_motion is not None
    _finish(qtbot, panel)


def test_toggling_during_the_motion_restarts_cleanly(qtbot, panel):
    panel.set_pinned(True)
    panel.set_pinned(False)
    assert panel._pin_time == 0
    _finish(qtbot, panel)
    assert panel._surface.pos() == QPoint(0, 0)


def test_no_motion_when_nothing_changes_or_the_panel_is_closed(qtbot):
    window = PanelWindow(LOOK, Settings(animation_ms=ANIMATION_MS))
    qtbot.addWidget(window)
    window.set_pinned(True)  # açılışta hatırlanan durum sessizce uygulanır
    assert window._pin_motion is None
    window._settings = Settings(animations=False)
    window.open_on(window.screen())
    window._settings = Settings(animation_ms=ANIMATION_MS)
    window.set_pinned(True)
    assert window._pin_motion is None


def test_animations_setting_turns_the_motion_off(panel):
    panel._settings = Settings(animations=False)
    panel.set_pinned(True)
    assert panel._pin_motion is None


def test_no_motion_while_the_panel_goes_through_the_handle(qtbot):
    window = PanelWindow(LOOK, Settings(animation_ms=ANIMATION_MS))
    qtbot.addWidget(window)
    window.open_on(window.screen())
    window.set_pinned(True)
    assert window._warp is not None
    assert window._pin_motion is None


def test_closing_during_the_motion_goes_straight_into_the_hole(qtbot, panel):
    panel.set_pinned(True)
    with qtbot.waitSignal(panel.hidden, timeout=TIMEOUT_MS):
        panel.close_panel()
        assert panel._pin_motion is None
    assert not panel.isVisible()
    assert panel._get_pull() == 1.0


def test_button_shows_a_stuck_pin_only_while_pinned(panel):
    button = panel.header._pin
    size = button.sizeHint()
    panel._settings = Settings(animations=False)
    assert button.text() == PIN_GLYPH
    panel.set_pinned(True)
    assert button.text() == PINNED_GLYPH
    assert button.sizeHint() == size  # başlık satırı zıplamaz
    panel.set_pinned(False)
    assert button.text() == PIN_GLYPH


def test_button_is_not_left_invisible_after_the_motion(qtbot, panel):
    panel.set_pinned(True)
    assert not panel.header._pin.property("ghost")
    _finish(qtbot, panel)


def test_pivot_is_the_pin_button_in_the_top_right_corner(panel):
    pivot = panel.header.pin_center(panel._surface)
    assert pivot.x() > panel._width * 0.8
    assert pivot.y() < panel._height * 0.1
