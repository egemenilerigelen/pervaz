import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QGuiApplication

from pervaz.core.settings import Settings
from pervaz.core.trigger.handle import HandleTrigger, dent_path
from pervaz.theme import resolve_look
from pervaz.theme.tokens import HOLE, parse_hex


@pytest.fixture
def trigger(qapp):
    handle = HandleTrigger()
    yield handle
    handle.shutdown()


def _configure(trigger: HandleTrigger, **settings) -> None:
    trigger.configure(Settings(**settings), resolve_look("dark", "normal", 1.0))


def test_anchor_is_the_middle_of_the_handle_on_the_screen_edge(trigger):
    _configure(trigger, handle_thickness=6, handle_length=96, handle_position=0.25)
    screen = QGuiApplication.primaryScreen()
    trigger.show_on(screen)
    rect = trigger._widget.geometry()
    full = screen.geometry()
    assert trigger.anchor_on(screen) == QPoint(full.x() + full.width(), rect.y() + 48)
    assert rect.right() == full.right()


def test_dent_fades_into_the_edge_and_is_deepest_in_the_middle(qapp):
    path = dent_path(6, 96)
    assert path.pointAtPercent(0).x() == pytest.approx(6)
    assert path.pointAtPercent(1).x() == pytest.approx(6)
    assert path.pointAtPercent(0.5).x() == pytest.approx(0)


def test_handle_is_dark_brown_and_ignores_the_theme_accent(trigger):
    trigger.configure(Settings(), resolve_look("dark", "normal", 1.0, accent="#00ff00"))
    widget = trigger._widget
    widget.resize(6, 96)
    image = widget.grab().toImage()
    color = image.pixelColor(3, 48)
    assert color.alpha() > 0
    assert color.red() > color.green() > color.blue()
    assert color.lightness() < 100


@pytest.mark.parametrize("tone", ["void", "deep", "body", "rim", "glow"])
def test_tones_are_warm_browns(tone):
    r, g, b = parse_hex(getattr(HOLE, tone))
    assert r > g > b


def test_hover_makes_the_handle_more_present(trigger):
    widget = trigger._widget
    widget.resize(6, 96)
    idle = widget.grab().toImage().pixelColor(3, 48).alpha()
    widget.enterEvent(None)
    hovered = widget.grab().toImage().pixelColor(3, 48).alpha()
    widget.leaveEvent(None)
    assert hovered > idle
