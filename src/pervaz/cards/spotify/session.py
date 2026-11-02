"""Çalma oturumu: kartın bildiği şarkı, ses ve çıkış durumu ile komutların iyimser etkisi.

Qt'siz ve yalnızca saate bağlıdır; kart arayüzü, zamanlayıcıları ve arka plan işini yönetir,
"şu an ne çalıyor, kullanıcı az önce ne yaptı, ne diske yazılmalı" sorularını bu sınıf yanıtlar.
Komut yöntemleri ekranda hemen görünecek değişikliği uygular ve arka uca gönderilecek değeri
döndürür; komutun kendisini göndermek kartın işidir.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from pervaz.cards.spotify.cache import LastPlayedStore
from pervaz.cards.spotify.models import AudioOutput, NowPlaying, Reading, Repeat, Volume
from pervaz.cards.spotify.state import (
    HOLD_SECONDS,
    VOLUME_HOLD_SECONDS,
    CommandHold,
    Hold,
    PendingVolume,
)


class PlaybackSession:
    def __init__(self, clock: Callable[[], float], cache: LastPlayedStore) -> None:
        self._clock = clock
        self._cache = cache
        # Son bilinen şarkı: Spotify kapanınca da, uygulama Spotify kapalıyken açılınca da kalır.
        self._now_playing: NowPlaying | None = cache.load()
        self._saved_key = self._key(self._now_playing)
        self._live = False  # Spotify'ın medya oturumu şu an var mı
        self._volume: Volume | None = None
        self._output: AudioOutput | None = None  # seçili (varsayılan) çıkış cihazı
        self._command_hold = CommandHold(clock, HOLD_SECONDS)
        self._volume_hold = Hold(clock, VOLUME_HOLD_SECONDS)
        self._output_hold = Hold(clock, HOLD_SECONDS)
        self._pending_volume = PendingVolume()

    @property
    def now_playing(self) -> NowPlaying | None:
        return self._now_playing

    @property
    def live(self) -> bool:
        return self._live

    @property
    def volume(self) -> Volume | None:
        return self._volume

    @property
    def output(self) -> AudioOutput | None:
        return self._output

    @property
    def ticking(self) -> bool:
        """İlerleme çubuğunun kendi kendine akması gerekiyor mu."""
        np = self._now_playing
        return self._live and np is not None and np.playing

    def position(self) -> float:
        """Şu anki konum (saniye); çalarken son okumadan bu yana geçen süre eklenir."""
        np = self._now_playing
        if np is None:
            return 0.0
        return np.position_at(self._clock()) if self._live else np.position

    def controllable(self) -> NowPlaying | None:
        return self._now_playing if self._live else None

    # --- Okuma ve kayıt -----------------------------------------------------

    def apply(self, reading: Reading) -> None:
        np = reading.now_playing
        if np is None and self._live:
            self.remember()  # Spotify az önce kapandı: son konum diske yazılsın
        self._live = np is not None
        if np is not None:
            np = self._now_playing = self._command_hold.apply(np)
            if self._key(np) != self._saved_key:
                self.remember()
        if not self._volume_hold.active:
            self._volume = reading.volume
        if not self._output_hold.active:
            self._output = reading.output

    @staticmethod
    def _key(np: NowPlaying | None) -> tuple[Any, ...] | None:
        """Diske yeniden yazmayı gerektiren değişiklikler: şarkı ya da kapağı (geç gelen ya da
        düzelen kapak dahil) değişti mi."""
        return None if np is None else (np.track, np.duration, np.cover)

    def remember(self) -> None:
        np = self._now_playing
        if np is None:
            return
        self._saved_key = self._key(np)
        self._cache.save(replace(np, position=self.position()))

    def remember_if_live(self) -> None:
        """Panel kapanırken konum güncellenmez; son konum saklansın."""
        if self._live:
            self.remember()

    # --- Komutlar -----------------------------------------------------------

    def _expect(self, **intent: Any) -> None:
        """`intent`teki değişikliği Spotify bildirene kadar ekranda tutar."""
        np = self._now_playing
        if np is None:
            return
        self._command_hold.remember(**intent)
        self._now_playing = replace(np, **intent)

    def toggle_playing(self) -> bool | None:
        np = self.controllable()
        if np is None:
            return None
        playing = not np.playing
        now = self._clock()
        # Durunca konum dondurulur, başlayınca oradan akar.
        self._expect(playing=playing, position=np.position_at(now), taken_at=now)
        return playing

    def toggle_shuffle(self) -> bool | None:
        np = self.controllable()
        if np is None:
            return None
        enabled = not np.shuffle
        self._expect(shuffle=enabled)
        return enabled

    def cycle_repeat(self) -> Repeat | None:
        np = self.controllable()
        if np is None:
            return None
        mode = np.repeat.next()
        self._expect(repeat=mode)
        return mode

    def seek(self, seconds: float) -> bool:
        if self.controllable() is None:
            return False
        self._expect(position=seconds, taken_at=self._clock())
        return True

    # --- Ses ----------------------------------------------------------------

    def drag_volume(self, level: float) -> Volume | None:
        """Çubuk sürüklenirken ekrandaki sesi günceller; gönderme `take_pending_volume`'dadır."""
        volume = self._volume
        if volume is None:
            return None
        self._pending_volume.update(level, volume.muted)
        self._volume = Volume(level, False)
        self._volume_hold.start()
        return self._volume

    def take_pending_volume(self) -> tuple[float, bool] | None:
        return self._pending_volume.take()

    def toggle_mute(self) -> bool | None:
        volume = self._volume
        if volume is None:
            return None
        muted = not volume.muted
        self._volume = Volume(volume.level, muted)
        self._volume_hold.start()
        return muted

    def select_output(self, output: AudioOutput) -> None:
        """Kutucuk hemen yeni cihazı göstersin; Windows'un yeni varsayılanı bildirmesi sürer."""
        self._output = replace(output, is_default=True)
        self._output_hold.start()
