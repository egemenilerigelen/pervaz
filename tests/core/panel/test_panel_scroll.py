from PySide6.QtWidgets import QWidget

from pervaz.core.panel.window import PanelWindow
from pervaz.core.settings import Settings
from pervaz.theme import resolve_look

CARD_HEIGHT = 200
LAYOUT_MS = 30  # düzenin oturması için olay döngüsüne tanınan süre


def _panel(qtbot) -> PanelWindow:
    panel = PanelWindow(resolve_look("dark", "normal", 1.0), Settings(animations=False))
    qtbot.addWidget(panel)
    panel.open_on(panel.screen())
    return panel


def _add_card(qtbot, panel: PanelWindow) -> None:
    card = QWidget()
    card.setFixedHeight(CARD_HEIGHT)
    panel.add_host(card)
    qtbot.wait(LAYOUT_MS)


def test_card_width_stays_put_when_content_starts_to_scroll(qtbot):
    panel = _panel(qtbot)
    scroll = panel._scroll
    widths, scrolled = set(), []
    for _ in range(8):
        _add_card(qtbot, panel)
        widths.add(scroll.widget().width())
        scrolled.append(scroll.verticalScrollBar().maximum() > 0)
    assert not scrolled[0] and scrolled[-1]  # sınır gerçekten aşıldı
    assert len(widths) == 1  # çubuk belirirken kartlar daralmadı


def test_card_width_stays_put_when_content_stops_scrolling(qtbot):
    panel = _panel(qtbot)
    cards = []
    for _ in range(8):
        card = QWidget()
        card.setFixedHeight(CARD_HEIGHT)
        panel.add_host(card)
        cards.append(card)
    qtbot.wait(LAYOUT_MS)
    scroll = panel._scroll
    assert scroll.verticalScrollBar().maximum() > 0
    before = scroll.widget().width()
    for card in cards[3:]:
        card.hide()  # kartlar katlanınca içerik kısalır
    qtbot.wait(LAYOUT_MS)
    assert scroll.verticalScrollBar().maximum() == 0
    assert scroll.widget().width() == before
