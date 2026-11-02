# Yeni kart eklemek

Yeni bir kart, kendi paketi olan bağımsız bir birimdir. Çekirdeğe (`core`) dokunmak gerekmez:

1. `cards/<ad>/` paketini aç.
2. `Card`'dan türeyen sınıfı yaz (`card.py`).
3. `__init__.py` içinde `SPEC`'i dışa aktar.
4. `cards/__init__.py` içindeki `CARDS` demetine bir satır ekle.
5. Testini yaz ve belgesini güncelle.

Sözleşme testi (`tests/core/cards/test_card_contract.py`) ve mimari testi yeni kartı
kendiliğinden kapsar; onlara ekleme yapmak gerekmez.

Bu sayfadaki **Geri sayım** örneği baştan sona yazılmış, çalışan ve test edilmiş bir karttır:
aşağıdaki dosyalar olduğu gibi `src/pervaz/cards/countdown/` altına konup kayıt satırı
eklenince panelde görünür. Örnek bu belgeyi yazarken geçici olarak eklenip testlerden geçirildi,
sonra kaldırıldı; depoda yer almaz.

## 1. Paket anatomisi

Her kart paketi aynı iskeleti izler. Gereksiz olan dosya oluşturulmaz, ama **aynı iş hep aynı
adı taşır**; bir kartı okuyan biri diğerinde kaybolmaz.

```text
cards/<kart>/
├── __init__.py      # yalnızca SPEC (ve gerekirse kart sınıfı) dışa aktarır
├── card.py          # Card alt sınıfı: görünüm + sinyal bağlantıları + SPEC
├── models.py        # frozen dataclass'lar
├── source.py        # dış dünyanın Protocol'ü + gerçek uygulama (HTTP/OS)
├── cache.py         # JsonCache[T] alt sınıfı + Store Protocol'ü
├── service.py       # varsa: yoklama, yedek kaynağa düşme, durum makinesi
├── widgets.py       # karta özel QWidget'lar
├── icon.py          # QPainter ile çizilen başlık simgesi
├── formatting.py    # saf biçimlendirme fonksiyonları
└── windows.py       # varsa: yalnızca bu karta ait Windows API sarmalayıcısı
```

Kural: `card.py` yalnızca kartın görünümü ve sinyal bağlantılarıdır. Zamanlama, komut tutma,
renk seçimi gibi saf mantık Qt'siz ayrı bir dosyada durur ve ayrı test edilir. Kart **başka bir
kartı import edemez**; yalnızca kendi paketini, `core`, `infra` ve `theme`'i kullanabilir.

## 2. Kart sözleşmesi

| Kural | Nasıl |
| --- | --- |
| Zamanlayıcı ve yoklama yalnızca panel açıkken çalışır | `on_show`'da başlat, `on_hide`'da durdur |
| Uygulama kapanırken kaynaklar bırakılır | `shutdown`'da zamanlayıcıları ve arka plan işlerini durdur |
| Hata kartı çökertmez, panele sıçramaz | sinyal yuvalarını ve zamanlayıcı geri çağrılarını `@guarded` ile sar |
| Beklenen hata anlaşılır bir mesajla bildirilir | `self.fail("Mesaj")`; düzelince `self.clear_error()` |
| Dış dünya kurucudan, `Protocol` ile gelir | kaynak, önbellek, saat, pano... testte sahtesi verilir |
| Önbellek `JsonCache`'ten türer | `file_name`, `encode`, `decode` yeter |
| Ayar bozuksa kart yine açılır | `self.config`'i doğrula, bozuk değeri varsayılana çevir |
| Modeller değişmezdir | `@dataclass(frozen=True)`, `to_dict`/`from_dict` |
| Renk ve ölçü `theme`'den gelir | sabit renk yazma; `make_label(metin, "dim")` gibi rolleri, `look.metrics.sp(8)` ile boyutları kullan |
| Başlık bilgisi varsayılan boştur | `set_info` yalnızca anlamlıysa (eski veri, yedek kaynak, katlıyken özet) |

Ağ ya da sistem okuyan bir kart yoklama için `core.polling.Poller`'ı kullanır; arka plan iş
parçacığını, nesil numaralarını ve hata sonrası yeniden denemeyi o yönetir:

```python
# _fetch arka plan iş parçacığında çalışır; sonuç sinyalle ana iş parçacığına gelir
self._poller = Poller(self._fetch, interval_seconds, self)
self._poller.succeeded.connect(self._on_success)  # @guarded
self._poller.failed.connect(self._on_failure)  # @guarded

# on_show: self._poller.start()
# on_hide ve shutdown: self._poller.stop()
```

Çalışan örnekler için hava durumu (`cards/weather/card.py`) ve telemetri
(`cards/telemetry/card.py`) kartlarına bak.

Katlanmayı öğrenmek isteyen kart `on_collapsed(collapsed)`'ı ezer; tema değişince çizimini
yenilemek isteyen `set_look(look)`'u. Başlık simgesi yazı tipinden (`CardSpec.icon`, Segoe MDL2
Assets karakteri) ya da `icon_factory` ile kendi çizdiği bir widget'tan gelebilir.

## 3. Örnek: Geri sayım kartı

Ayardaki tarihe kaç gün kaldığını gösterir. Dış dünyası bugünün tarihidir, önbelleği son
gösterilen değerdir, yaşam döngüsü bir saatlik zamanlayıcıdır.

### `cards/countdown/models.py`

```python
"""Geri sayımın veri modeli."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class Countdown:
    target: date
    days: int  # hedefe kalan gün; geçmişse negatif

    def to_dict(self) -> dict[str, Any]:
        return {"target": self.target.isoformat(), "days": self.days}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Countdown:
        return cls(date.fromisoformat(data["target"]), int(data["days"]))
```

### `cards/countdown/source.py`

Kartın dış dünyadan beklediği her şey bir `Protocol` ile tanımlanır; gerçek uygulama aynı
dosyada, varsayılan olarak kullanılır:

```python
"""Kartın dış dünyadan beklediği tek şey: bugünün tarihi."""

from __future__ import annotations

from datetime import date
from typing import Protocol


class DateSource(Protocol):
    def today(self) -> date: ...


class SystemDate:
    """Gerçek uygulama: sistem saatinden okur."""

    def today(self) -> date:
        return date.today()
```

### `cards/countdown/cache.py`

```python
"""Son gösterilen geri sayım: uygulama açılır açılmaz ekranda bir şey olsun diye."""

from __future__ import annotations

from typing import Any, Protocol

from pervaz.cards.countdown.models import Countdown
from pervaz.infra.storage import JsonCache


class CountdownStore(Protocol):
    """Kartın ihtiyaç duyduğu önbellek arayüzü; testlerde değiştirilebilir."""

    def load(self) -> Countdown | None: ...

    def save(self, countdown: Countdown) -> None: ...


class CountdownCache(JsonCache[Countdown]):
    file_name = "countdown.json"

    def encode(self, value: Countdown) -> dict[str, Any]:
        return value.to_dict()

    def decode(self, data: dict[str, Any]) -> Countdown:
        return Countdown.from_dict(data)
```

Dosya `%APPDATA%\Pervaz\countdown.json` olur. Bozuk dosya kartı düşürmez: `JsonCache` uyarı
yazıp `None` döndürür.

### `cards/countdown/card.py`

```python
"""Geri sayım kartı: hedef tarihe kaç gün kaldığını gösterir.

Ayar: `cards` içindeki `countdown` girdisinin `config` alanında `target` (`"2027-01-01"`).
Panel açıkken saatte bir yenilenir; kapanınca zamanlayıcı durur.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout

from pervaz.cards.countdown.cache import CountdownCache, CountdownStore
from pervaz.cards.countdown.models import Countdown
from pervaz.cards.countdown.source import DateSource, SystemDate
from pervaz.core.cards.base import Card, CardContext, CardSpec, guarded
from pervaz.core.turkish import month_name
from pervaz.core.widgets import make_frame, make_label

DEFAULT_TARGET = date(2027, 1, 1)
REFRESH_MS = 60 * 60 * 1000


def parse_target(raw: object) -> date:
    """Ayardaki tarih; bozuksa varsayılan kullanılır (ayar dosyası yüzünden kart açılmaz olmaz)."""
    if isinstance(raw, str):
        try:
            return date.fromisoformat(raw)
        except ValueError:
            pass
    return DEFAULT_TARGET


class CountdownCard(Card):
    def __init__(
        self,
        context: CardContext,
        cache: CountdownStore | None = None,
        source: DateSource | None = None,
    ) -> None:
        super().__init__(context)
        self._target = parse_target(self.config.get("target"))
        self._cache = cache or CountdownCache()
        self._source = source or SystemDate()
        self._build_ui()

        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self._refresh)

        saved = self._cache.load()
        self._shown: Countdown | None = saved if saved and saved.target == self._target else None
        if self._shown is not None:
            self._render(self._shown)  # ilk yenilemeden önce son değer görünür

    # --- Arayüz -------------------------------------------------------------

    def _build_ui(self) -> None:
        sp = self.look.metrics.sp
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        box = make_frame("inner")
        outer.addWidget(box)
        column = QVBoxLayout(box)
        column.setContentsMargins(sp(8), sp(6), sp(8), sp(6))
        column.setSpacing(0)
        self._days = make_label("—", "big")
        self._date = make_label(f"{self._target.day} {month_name(self._target)}", "dim")
        column.addWidget(self._days)
        column.addWidget(self._date)

    def _render(self, countdown: Countdown) -> None:
        self._days.setText(f"{max(countdown.days, 0)} gün")

    # --- Veri ---------------------------------------------------------------

    @guarded
    def _refresh(self) -> None:
        days = (self._target - self._source.today()).days
        countdown = Countdown(self._target, days)
        if days < 0:
            self.fail("Hedef tarih geçmiş")
        else:
            self.clear_error()
        self._render(countdown)
        if countdown != self._shown:  # aynı değer her saat diske yazılmasın
            self._shown = countdown
            self._cache.save(countdown)

    # --- Yaşam döngüsü ------------------------------------------------------

    def on_show(self) -> None:
        self._refresh()
        self._timer.start()

    def on_hide(self) -> None:
        self._timer.stop()

    def shutdown(self) -> None:
        self._timer.stop()


def _create(context: CardContext) -> Card:
    return CountdownCard(context)


SPEC = CardSpec(id="countdown", title="Geri sayım", icon="\ue787", factory=_create)


__all__ = ["SPEC", "CountdownCard"]
```

### `cards/countdown/__init__.py`

```python
"""Geri sayım kartı: ayardaki tarihe kaç gün kaldığını gösterir."""

from pervaz.cards.countdown.card import SPEC, CountdownCard

__all__ = ["SPEC", "CountdownCard"]
```

`SPEC` ve `__all__` içinde `"SPEC"` olması şarttır; mimari testi bunu denetler.

### Kayıt: `cards/__init__.py`

```python
from pervaz.cards import clipboard, countdown, finance, github, spotify, telemetry, weather
...
CARDS: tuple[CardSpec, ...] = (
    ...
    github.SPEC,
    countdown.SPEC,
)
```

`CARDS` sırası, ayarlarda kartın olmadığı yeni kurulumlardaki varsayılan sıradır. Mevcut
kullanıcıların `settings.json` dosyasında kart yoksa sona eklenir.

### Ayar

```json
{ "id": "countdown", "enabled": true, "collapsed": false, "config": { "target": "2027-06-01" } }
```

### Test: `tests/cards/countdown/test_countdown_card.py`

Sahte tarih ve sahte önbellekle, gerçek sisteme dokunmadan:

```python
from datetime import date

import pytest

from pervaz.cards import CARDS
from pervaz.cards.countdown import SPEC, CountdownCard
from pervaz.cards.countdown.cache import CountdownCache
from pervaz.cards.countdown.models import Countdown
from pervaz.core.cards.base import CardContext
from pervaz.theme import resolve_look

LOOK = resolve_look("dark", "normal", 1.0)


class FakeDate:
    def __init__(self, today: date):
        self._today = today

    def today(self) -> date:
        return self._today


class FakeStore:
    def __init__(self, loaded: Countdown | None = None):
        self.loaded = loaded
        self.saved: list[Countdown] = []

    def load(self):
        return self.loaded

    def save(self, countdown):
        self.saved.append(countdown)


@pytest.fixture
def make_card(qtbot):
    def make(config=None, today=date(2026, 12, 22), store=None):
        card = CountdownCard(
            CardContext(LOOK, config or {"target": "2027-01-01"}),
            store or FakeStore(),
            FakeDate(today),
        )
        qtbot.addWidget(card)
        return card

    return make


def test_registered():
    assert SPEC.id == "countdown"
    assert SPEC in CARDS


def test_shows_the_days_left_when_shown(make_card):
    card = make_card()
    card.on_show()
    assert card._days.text() == "10 gün"
    card.on_hide()


def test_timer_runs_only_while_the_panel_is_open(make_card):
    card = make_card()
    card.on_show()
    assert card._timer.isActive()
    card.on_hide()
    assert not card._timer.isActive()


def test_target_in_the_past_reports_an_error_that_clears_later(make_card):
    card = make_card(today=date(2027, 1, 5))
    card.on_show()
    assert card.current_error == "Hedef tarih geçmiş"
    assert card._days.text() == "0 gün"
    card._source = FakeDate(date(2026, 12, 31))
    card._refresh()
    assert card.current_error == ""
    card.shutdown()


@pytest.mark.parametrize("raw", [None, 5, "yarın", "2027-13-40"])
def test_bad_target_falls_back_to_the_default(make_card, raw):
    card = make_card({"target": raw})
    assert card._target == date(2027, 1, 1)


def test_last_value_is_shown_before_the_first_refresh(make_card):
    card = make_card(store=FakeStore(Countdown(date(2027, 1, 1), 99)))
    assert card._days.text() == "99 gün"


def test_cached_value_for_another_target_is_ignored(make_card):
    card = make_card(store=FakeStore(Countdown(date(2030, 1, 1), 99)))
    assert card._days.text() == "—"


def test_unchanged_value_is_not_written_again(make_card):
    store = FakeStore()
    card = make_card(store=store)
    card.on_show()
    card._refresh()
    assert len(store.saved) == 1
    card.shutdown()


def test_cache_roundtrip(tmp_path):
    cache = CountdownCache(tmp_path / "countdown.json")
    cache.save(Countdown(date(2027, 1, 1), 10))
    assert cache.load() == Countdown(date(2027, 1, 1), 10)
```

Sözleşme testi bu kartı `CARDS` içinde bulur ve kurma, gösterme, gizleme, kapatma ve zamanlayıcı
kalmaması kurallarını sınar. Gerçek ağ, saat dışında bir sistem kaynağı ya da iş parçacığı
kullanan bir kart için `tests/core/cards/test_card_contract.py` içindeki `BUILDERS` sözlüğüne,
sahte bağımlılıklarıyla bir satır eklenir.

## 4. Kartı bitirirken

- [ ] `python -m ruff check .`, `python -m ruff format --check .` ve `python -m pytest -q` temiz.
- [ ] Kartın kullanıcıya dönük anlatımı ve geliştirici notları `docs/cards/<kart>.md` içinde
      (örnek için [GitHub kartı](cards/github.md)); `config` alanları tablo halinde.
- [ ] README'deki kart tablosuna bir satır eklendi.
- [ ] Panelin görünümü değiştiyse `docs/images/panel.png` yenilendi.
- [ ] Yeni bir bağımlılık ya da Qt modülü eklendiyse exe boyutu ölçüldü
      ([geliştirme rehberi](development.md#exe-ve-boyut-bütçesi)).
- [ ] Hesap ya da anahtar isteyen bir kaynak kullanılmadı
      ([ADR 0003](decisions/0003-hesapsiz-veri-kaynaklari.md)).
