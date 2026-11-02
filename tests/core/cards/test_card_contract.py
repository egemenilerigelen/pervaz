"""Kart sözleşmesi: `CARDS` içindeki her kart aynı yaşam döngüsüne uyar.

Kur -> göster -> gizle -> yeniden göster -> kapat. Gizlendikten sonra zamanlayıcı kalmaz, kapanınca
hiçbir zamanlayıcı ve iş parçacığı kalmaz. Yeni kart buraya kendiliğinden girer. Sistem kaynağı
kullanan kart `BUILDERS`'a sahte bağımlılıklarıyla eklenir; eklenmese de ağa çıkamaz.
"""

import socket
import threading

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget

from pervaz.cards import CARDS
from pervaz.cards.finance.card import FinanceCard
from pervaz.cards.finance.models import Snapshot
from pervaz.cards.github.card import GithubCard
from pervaz.cards.spotify.card import SpotifyCard
from pervaz.cards.spotify.models import Reading
from pervaz.cards.telemetry.card import TelemetryCard
from pervaz.cards.telemetry.models import Sample
from pervaz.cards.weather.card import WeatherCard
from pervaz.core.cards.base import Card, CardContext
from pervaz.core.cards.host import CardHost
from pervaz.infra.http import ProviderError
from pervaz.theme import resolve_look

LOOK = resolve_look("dark", "normal", 1.0)
LIGHT = resolve_look("light", "normal", 1.0)
SHOW_MS = 30

# Bu kartlar veriyi bilerek panel kapalıyken de seyrek yeniler (hafif istek, açılışta hazır veri).
BACKGROUND_REFRESH = {"weather", "github"}


class _Empty:
    """Hiç önbelleği olmayan depo."""

    def load(self):
        return None

    def save(self, *args):
        pass


class _EmptyWeather(_Empty):
    def load(self):
        return None, None


class _Unreachable:
    """Kaynağa ulaşılamıyor: kartlar bunu kendi içinde hata olarak gösterir."""

    def __getattr__(self, name):
        def fail(*args):
            raise ProviderError("kaynak yok")

        return fail


class _FakeSystem:
    def sample(self):
        return Sample("İşlemci", 10.0, 3.0, 1, 2, 0.0, 0.0, None)

    def reset(self):
        pass

    def close(self):
        pass


class _FakeSpotify:
    def prepare(self):
        pass

    def read(self):
        return Reading(None, None)

    def __getattr__(self, name):
        return lambda *args: None


class _FakeFetcher:
    def fetch(self) -> Snapshot:
        raise ProviderError("kaynak yok")


BUILDERS = {
    "weather": lambda c: WeatherCard(c, _EmptyWeather(), _Unreachable()),
    "finance": lambda c: FinanceCard(c, _Empty(), _FakeFetcher()),
    "telemetry": lambda c: TelemetryCard(c, _FakeSystem(), lambda: 12.0),
    "spotify": lambda c: SpotifyCard(c, _FakeSpotify(), cache=_Empty()),
    "github": lambda c: GithubCard(c, _Empty(), _Unreachable()),
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise OSError("testte ağ yok")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)


@pytest.fixture(params=CARDS, ids=lambda spec: spec.id)
def spec(request):
    return request.param


def _build(spec):
    return BUILDERS.get(spec.id, spec.factory)(CardContext(LOOK, {}))


def _active_timers(card):
    return [t for t in card.findChildren(QTimer) if t.isActive()]


def test_factory_result_is_a_card(qtbot, spec):
    card = _build(spec)
    qtbot.addWidget(card)
    assert isinstance(card, Card)
    card.shutdown()


def test_no_timer_keeps_running_after_hide(qtbot, spec):
    card = _build(spec)
    qtbot.addWidget(card)
    card.on_show()
    qtbot.wait(SHOW_MS)
    card.on_hide()
    if spec.id not in BACKGROUND_REFRESH:
        assert not _active_timers(card)
    card.shutdown()


def test_card_can_be_shown_again_after_hide(qtbot, spec):
    card = _build(spec)
    qtbot.addWidget(card)
    for _ in range(2):
        card.on_show()
        qtbot.wait(SHOW_MS)
        card.on_hide()
    card.shutdown()


def test_shutdown_leaves_no_timer_or_thread(qtbot, spec):
    before = set(threading.enumerate())
    card = _build(spec)
    qtbot.addWidget(card)
    card.on_show()
    qtbot.wait(SHOW_MS)
    card.on_hide()
    card.shutdown()
    assert not _active_timers(card)
    qtbot.waitUntil(lambda: not (set(threading.enumerate()) - before), timeout=3000)


def test_collapse_and_look_change_are_safe(qtbot, spec):
    card = _build(spec)
    host = CardHost(spec, card, LOOK, animate=False)
    qtbot.addWidget(host)
    card.on_show()
    host.toggle()
    host.toggle()
    host.set_look(LIGHT)
    host.card_hidden()
    assert host._error.isHidden() or card.current_error
    card.shutdown()


def test_header_icon_is_a_widget(qtbot, spec):
    if spec.icon_factory is None:
        pytest.skip("kart yazı tipi simgesi kullanıyor")
    icon = spec.icon_factory(LOOK)
    qtbot.addWidget(icon)
    assert isinstance(icon, QWidget)
