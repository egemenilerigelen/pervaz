"""Spotify kartı: çalan şarkı, kapak, ilerleme çubuğu, kontrol düğmeleri, ses ve çıkış cihazı.

Veri Windows'un medya oturumundan gelir (Spotify hesabına bağlanılmaz). Kart, panel açıkken
saniyede bir okur; çalarken ilerleme çubuğunu aradaki sürede kendisi akıtır. Spotify kapanınca
son şarkı görünür kalır, düğmeler pasifleşir.

Bu dosya parçaları birleştirir: denetim satırları `controls.py`, çalma durumu ve komutların
iyimser etkisi `session.py` (komut sonrası tutma `state.py`), arka plan işleri `worker.py`
içindedir. Kart yalnızca arayüzü, zamanlayıcıları ve yaşam döngüsünü yönetir.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QMenu, QVBoxLayout

from pervaz.cards.spotify.backdrop import SpotifyBackdrop
from pervaz.cards.spotify.backend import SpotifyBackend
from pervaz.cards.spotify.cache import LastPlayedCache, LastPlayedStore
from pervaz.cards.spotify.controls import (
    SEEK_STEPS,
    AudioRow,
    ProgressRow,
    TransportRow,
    accent_stylesheet,
)
from pervaz.cards.spotify.formatting import summary
from pervaz.cards.spotify.logo import SpotifyLogo
from pervaz.cards.spotify.models import AudioOutput, Reading
from pervaz.cards.spotify.palette import DEFAULT, accent_for, extract_palette
from pervaz.cards.spotify.session import PlaybackSession
from pervaz.cards.spotify.widgets import CoverView
from pervaz.cards.spotify.worker import Worker
from pervaz.core.cards.base import Card, CardContext, CardSpec, guarded
from pervaz.core.widgets import ElidedLabel
from pervaz.theme import Look

POLL_MS = 1000
TICK_MS = 250  # çalarken ilerleme çubuğunun ve süre yazısının yenilenme aralığı
RECHECK_MS = 350  # komuttan sonra gerçek durumu yeniden oku
VOLUME_DEBOUNCE_MS = 40
COVER_SIZE = 42


class SpotifyCard(Card):
    def __init__(
        self,
        context: CardContext,
        backend: SpotifyBackend,
        clock: Callable[[], float] = time.monotonic,
        cache: LastPlayedStore | None = None,
    ) -> None:
        super().__init__(context)
        self._backend = backend
        self._session = PlaybackSession(clock, cache or LastPlayedCache())
        self._shown = False
        self._collapsed = False
        self._reading = False
        self._cover_src: bytes | None = None
        self._palette = DEFAULT  # şu anki kapağın renkleri
        self._build_ui()

        self._worker = Worker(backend.prepare, self)
        self._worker.done.connect(self._on_done, Qt.ConnectionType.QueuedConnection)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(POLL_MS)
        self._poll_timer.timeout.connect(self._poll)
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(TICK_MS)
        self._tick_timer.timeout.connect(self._render_progress)
        self._volume_timer = QTimer(self)
        self._volume_timer.setSingleShot(True)
        self._volume_timer.setInterval(VOLUME_DEBOUNCE_MS)
        self._volume_timer.timeout.connect(self._send_volume)
        self._render()

    # --- Arayüz -------------------------------------------------------------

    def _build_ui(self) -> None:
        look = self.look
        sp = look.metrics.sp
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        # Hava kartındaki gibi çerçeveli kutu; arkasında hafif dalga/daire deseni var.
        self._backdrop = box = SpotifyBackdrop(look)
        outer.addWidget(box)
        rows = QVBoxLayout(box)
        rows.setContentsMargins(sp(8), sp(6), sp(8), sp(4))
        rows.setSpacing(sp(3))

        top = QHBoxLayout()
        top.setSpacing(sp(8))
        self._cover = CoverView(sp(COVER_SIZE), look)
        top.addWidget(self._cover)
        text = QVBoxLayout()
        text.setSpacing(0)
        self._title = ElidedLabel("value")
        self._artist = ElidedLabel("soft")
        text.addStretch()
        text.addWidget(self._title)
        text.addWidget(self._artist)
        text.addStretch()
        top.addLayout(text, 1)
        rows.addLayout(top)

        self._progress = ProgressRow(look)
        self._transport = TransportRow(look)
        self._audio = AudioRow(look)
        for row in (self._progress, self._transport, self._audio):
            rows.addWidget(row)

        self._elapsed, self._seek, self._total = (
            self._progress.elapsed,
            self._progress.seek,
            self._progress.total,
        )
        self._shuffle, self._previous, self._play, self._next, self._repeat = (
            self._transport.shuffle,
            self._transport.previous,
            self._transport.play,
            self._transport.next,
            self._transport.repeat,
        )
        self._mute, self._volume_slider, self._output = (
            self._audio.mute,
            self._audio.slider,
            self._audio.output,
        )
        self._seek.committed.connect(self._on_seek)
        self._volume_slider.valueChanged.connect(self._on_volume_moved)
        self._shuffle.clicked.connect(self._toggle_shuffle)
        self._previous.clicked.connect(self._skip_previous)
        self._play.clicked.connect(self._toggle_playing)
        self._next.clicked.connect(self._skip_next)
        self._repeat.clicked.connect(self._cycle_repeat)
        self._mute.clicked.connect(self._toggle_mute)
        self._output.clicked.connect(self._request_outputs)

    def set_look(self, look: Look) -> None:
        super().set_look(look)
        self._cover.set_look(look)
        self._backdrop.set_look(look)
        self._apply_accent()

    def _apply_accent(self) -> None:
        """Şarkı çubuğu, aktif düğmeler ve oynat dolgusu kapağın tonunu alır; kapak yoksa
        temanın vurgusu (altın) kalır. Kurallar yalnızca bu kartta geçerlidir."""
        accent = accent_for(self._palette, self.look.theme)
        self.setStyleSheet(accent_stylesheet(accent) if accent else "")

    # --- Yoklama ------------------------------------------------------------

    def _poll(self) -> None:
        if self._reading or not self._shown:
            return
        self._reading = True
        self._worker.submit("read", self._backend.read)

    @guarded
    def _on_done(self, tag: str, value: Any, error: str) -> None:
        if tag == "read":
            self._reading = False
            if error:
                self.fail("Spotify bilgisi okunamıyor")
                return
            if self.current_error:
                self.clear_error()
            self._apply(value)
        elif tag == "outputs":
            if not error:
                self._show_outputs(value)
        else:
            # Komut sonucu: başarılı olsun olmasın gerçek durumu yeniden oku.
            QTimer.singleShot(RECHECK_MS, self._poll)

    def _apply(self, reading: Reading) -> None:
        self._session.apply(reading)
        self._render()

    # --- Çizim --------------------------------------------------------------

    def _render(self) -> None:
        self._render_track()
        session = self._session
        self._transport.show_state(session.now_playing, session.live)
        self._audio.show_volume(session.volume)
        self._audio.show_output(session.output)
        self._render_progress()
        self._publish_info()
        self._sync_timers()

    def _render_track(self) -> None:
        np = self._session.now_playing
        if np is None:
            self._title.set_full_text("Spotify açık değil")
            self._artist.set_full_text("")
        else:
            self._title.set_full_text(np.track.title or "—")
            self._artist.set_full_text(np.track.artist)
        cover = np.cover if np is not None else None
        if cover is not self._cover_src:
            self._cover_src = cover
            self._cover.set_cover(cover)
            self._palette = extract_palette(cover)
            self._backdrop.set_palette(self._palette)  # arka plan kapağın tonunu alır
            self._apply_accent()

    def _render_progress(self) -> None:
        np = self._session.now_playing
        if np is None:
            self._progress.clear()
            return
        self._progress.show_position(np, self._session.position(), self._session.live)

    def _publish_info(self) -> None:
        np = self._session.now_playing
        self.set_info(
            summary(np.track.artist, np.track.title) if self._collapsed and np is not None else ""
        )

    def _sync_timers(self) -> None:
        ticking = self._shown and self._session.ticking
        if ticking and not self._tick_timer.isActive():
            self._tick_timer.start()
        elif not ticking and self._tick_timer.isActive():
            self._tick_timer.stop()

    # --- Komutlar -----------------------------------------------------------

    def _send(self, tag: str, job: Callable[[], Any], changed: bool = False) -> None:
        """Komutu arka plana verir; `changed` ise oturumun iyimser değişikliğini hemen çizer
        (düğme basıldığı anda tepki versin)."""
        if changed:
            self._render()
        self._worker.submit(tag, job)

    @guarded
    def _toggle_playing(self) -> None:
        playing = self._session.toggle_playing()
        if playing is not None:
            self._send("play", lambda: self._backend.set_playing(playing), changed=True)

    @guarded
    def _skip_next(self) -> None:
        if self._session.controllable() is not None:
            self._send("next", self._backend.next)

    @guarded
    def _skip_previous(self) -> None:
        if self._session.controllable() is not None:
            self._send("previous", self._backend.previous)

    @guarded
    def _toggle_shuffle(self) -> None:
        enabled = self._session.toggle_shuffle()
        if enabled is not None:
            self._send("shuffle", lambda: self._backend.set_shuffle(enabled), changed=True)

    @guarded
    def _cycle_repeat(self) -> None:
        mode = self._session.cycle_repeat()
        if mode is not None:
            self._send("repeat", lambda: self._backend.set_repeat(mode), changed=True)

    @guarded
    def _on_seek(self, value: int) -> None:
        seconds = value / SEEK_STEPS
        if self._session.seek(seconds):
            self._send("seek", lambda: self._backend.seek(seconds), changed=True)

    @guarded
    def _on_volume_moved(self, value: int) -> None:
        volume = self._session.drag_volume(value / 100)
        if volume is None:
            return
        self._audio.show_volume(volume)
        self._volume_timer.start()

    @guarded
    def _send_volume(self) -> None:
        pending = self._session.take_pending_volume()
        if pending is None:
            return
        level, unmute = pending

        def job() -> None:
            if unmute:
                self._backend.set_muted(False)
            self._backend.set_volume(level)

        self._worker.submit("volume", job)

    @guarded
    def _toggle_mute(self) -> None:
        muted = self._session.toggle_mute()
        if muted is None:
            return
        self._audio.show_volume(self._session.volume)
        self._worker.submit("mute", lambda: self._backend.set_muted(muted))

    # --- Ses çıkışı ---------------------------------------------------------

    @property
    def _outputs_menu(self) -> QMenu | None:
        return self._audio.outputs_menu

    def _request_outputs(self) -> None:
        self._worker.submit("outputs", self._backend.outputs)

    def _show_outputs(self, outputs: list[AudioOutput]) -> None:
        left = self.mapToGlobal(QPoint(0, 0)).x()
        self._audio.open_outputs_menu(outputs, self._select_output, left)

    @guarded
    def _select_output(self, output: AudioOutput) -> None:
        self._session.select_output(output)
        self._audio.show_output(self._session.output)
        self._worker.submit("output", lambda: self._backend.set_output(output.id))

    # --- Yaşam döngüsü ------------------------------------------------------

    def on_show(self) -> None:
        self._shown = True
        self._poll()
        self._poll_timer.start()
        self._sync_timers()

    def on_hide(self) -> None:
        self._shown = False
        self._session.remember_if_live()
        self._poll_timer.stop()
        self._tick_timer.stop()

    def on_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self._publish_info()

    def shutdown(self) -> None:
        self._session.remember_if_live()
        self._shown = False
        for timer in (self._poll_timer, self._tick_timer, self._volume_timer):
            timer.stop()
        self._worker.stop()


def _create(context: CardContext) -> Card:
    # İçe aktarma burada: WinRT ya da pycaw yüklenemezse yalnızca bu kart başlatılamaz.
    from pervaz.cards.spotify.windows import WindowsBackend

    return SpotifyCard(context, WindowsBackend())


SPEC = CardSpec(id="spotify", title="Spotify", icon="", factory=_create, icon_factory=SpotifyLogo)


__all__ = ["SPEC", "SpotifyCard"]
