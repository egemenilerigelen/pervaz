"""Komut sonrası tutma mantığı: Qt'siz, yalnızca saate bağlı küçük durum nesneleri.

Bir komuttan sonra Spotify'ın ve Windows'un yeni durumu bildirmesi biraz sürer; bu sürede
okumadan gelen eski durum, kullanıcının az önce yaptığı değişikliği geri almasın.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from pervaz.cards.spotify.models import NowPlaying

HOLD_SECONDS = 1.2
VOLUME_HOLD_SECONDS = 1.5


class Hold:
    """Başlatıldıktan sonra belirli bir süre etkin kalan bayrak."""

    def __init__(self, clock: Callable[[], float], seconds: float) -> None:
        self._clock = clock
        self._seconds = seconds
        self._until = 0.0

    @property
    def active(self) -> bool:
        return self._clock() < self._until

    def start(self) -> None:
        self._until = self._clock() + self._seconds


class CommandHold:
    """Kullanıcının az önce yaptığı, Spotify'ın henüz bildirmediği değişiklikler."""

    def __init__(self, clock: Callable[[], float], seconds: float = HOLD_SECONDS) -> None:
        self._hold = Hold(clock, seconds)
        self._intent: dict[str, Any] = {}

    def remember(self, **intent: Any) -> None:
        """Süresi dolmuş önceki komut unutulur; yenisi onu geri getirmez."""
        if not self._hold.active:
            self._intent = {}
        self._intent.update(intent)
        self._hold.start()

    def apply(self, now_playing: NowPlaying) -> NowPlaying:
        """Okunan duruma, süresi dolmamış değişiklikleri işler."""
        return replace(now_playing, **self._intent) if self._hold.active else now_playing


class PendingVolume:
    """Çubuk sürüklenirken biriken, henüz gönderilmemiş ses değişikliği."""

    def __init__(self) -> None:
        self._value: tuple[float, bool] | None = None  # (düzey, sessizden çıkarılsın mı)

    def update(self, level: float, muted: bool) -> None:
        """Sessizdeyken çubuğu oynatmak sesi de açar; bu istek sonraki adımlarda kaybolmaz."""
        unmute = muted or (self._value is not None and self._value[1])
        self._value = (level, unmute)

    def take(self) -> tuple[float, bool] | None:
        value, self._value = self._value, None
        return value
