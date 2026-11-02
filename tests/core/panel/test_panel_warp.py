import pytest
from PySide6.QtCore import QPoint

from pervaz.core.panel.window import PANEL_MARGIN, PanelWindow
from pervaz.core.settings import Settings
from pervaz.theme import resolve_look

ANIMATION_MS = 50
TIMEOUT_MS = 3000


@pytest.fixture
def panel(qtbot):
    window = PanelWindow(
        resolve_look("dark", "normal", 1.0), Settings(animation_ms=ANIMATION_MS, panel_width=280)
    )
    qtbot.addWidget(window)
    return window


def _anchor(panel: PanelWindow) -> QPoint:
    work = panel.screen().availableGeometry()
    return QPoint(work.x() + work.width(), work.y() + work.height() // 3)


def _open(qtbot, panel: PanelWindow) -> None:
    with qtbot.waitSignal(panel.shown, timeout=TIMEOUT_MS):
        panel.open_on(panel.screen(), _anchor(panel))


def test_panel_hugs_the_edges_without_touching(panel):
    assert 1 <= PANEL_MARGIN <= 2
    panel._settings = Settings(animations=False)
    panel.open_on(panel.screen())
    work = panel.screen().availableGeometry()
    assert panel.geometry().top() - work.top() == PANEL_MARGIN
    assert work.bottom() - panel.geometry().bottom() == PANEL_MARGIN
    assert work.right() - panel.geometry().right() == PANEL_MARGIN


def test_real_surface_waits_outside_while_the_snapshot_is_warped(qtbot, panel):
    panel.open_on(panel.screen(), _anchor(panel))
    assert panel._warp is not None
    assert panel._surface.x() < -panel._width  # kartlar efektin altında görünmez
    with qtbot.waitSignal(panel.shown, timeout=TIMEOUT_MS):
        pass
    assert panel._warp is None
    assert panel._surface.pos() == QPoint(0, 0)


def test_window_reaches_the_handle_only_during_the_animation(qtbot, panel):
    anchor = _anchor(panel)
    panel.open_on(panel.screen(), anchor)
    assert panel.geometry().right() == anchor.x() - 1
    assert panel.geometry().top() == panel._top  # yüzey ile görüntü aynı köşeden hizalı
    with qtbot.waitSignal(panel.shown, timeout=TIMEOUT_MS):
        pass
    assert panel.geometry() == panel.target_rect().adjusted(
        0, panel._margin, -panel._margin, -panel._margin
    )


def test_closing_goes_back_into_the_handle_and_hides(qtbot, panel):
    _open(qtbot, panel)
    panel.close_panel()
    assert panel.isVisible()  # hemen kaybolmaz, deliğe düşer
    assert panel._warp is not None
    with qtbot.waitSignal(panel.hidden, timeout=TIMEOUT_MS):
        pass
    assert not panel.isVisible()
    assert panel._warp is None
    assert panel._get_pull() == 1.0


def test_reopening_midway_reverses_from_the_current_point(qtbot, panel):
    _open(qtbot, panel)
    panel.close_panel()
    qtbot.waitUntil(lambda: panel._get_pull() > 0.05, timeout=TIMEOUT_MS)
    panel._anim.stop()
    midway = panel._get_pull()
    assert midway < 1.0
    hidden = []
    panel.hidden.connect(lambda: hidden.append(True))
    with qtbot.waitSignal(panel.shown, timeout=TIMEOUT_MS):
        panel.open_on(panel.screen(), _anchor(panel))
    assert not hidden
    assert panel.is_open


def test_snapshot_keeps_the_rounded_corners_transparent(panel):
    # `grab()` pencere zemini de boyadığı için bükülen köşelerde açık renk lekeler kalıyordu.
    panel._settings = Settings(animations=False)
    panel.open_on(panel.screen())
    image = panel._snapshot()
    right, bottom = image.width() - 1, image.height() - 1
    for x, y in ((0, 0), (right, 0), (0, bottom), (right, bottom)):
        assert image.pixelColor(x, y).alpha() == 0, (x, y)
    assert image.pixelColor(image.width() // 2, image.height() // 2).alpha() > 0


def test_nothing_is_painted_and_no_animation_runs_when_idle(qtbot, panel):
    _open(qtbot, panel)
    assert panel._warp is None  # görüntü bellekte tutulmaz
    assert panel._anim.state() != panel._anim.State.Running
