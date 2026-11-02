"""Son çalan şarkının diske yazılan kaydı: uygulama Spotify kapalıyken açılsa da kart, telefondaki
gibi en son kalan şarkıyı (kapak ve konumuyla) göstersin."""

from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path
from typing import Any, Protocol

from pervaz.cards.spotify.models import NowPlaying, Track
from pervaz.infra import paths
from pervaz.infra.storage import JsonCache

COVER_FILE = "spotify_cover.bin"


class LastPlayedStore(Protocol):
    """Kartın ihtiyaç duyduğu depo arayüzü; testlerde değiştirilebilir."""

    def load(self) -> NowPlaying | None: ...

    def save(self, now_playing: NowPlaying) -> None: ...


class LastPlayedCache(JsonCache[NowPlaying]):
    """Şarkı bilgisi JSON'da, kapak yanındaki ikili dosyada durur."""

    file_name = "spotify.json"
    invalid_message = "Spotify önbelleği geçersiz: %s"
    write_failed_message = "Spotify önbelleği yazılamadı: %s"

    def __init__(self, path: Path | None = None, cover_path: Path | None = None) -> None:
        super().__init__(path)
        self.cover_path = cover_path or paths.data_dir() / COVER_FILE
        self._cover_written: bytes | None = None  # değişmeyen kapak her seferinde yazılmasın

    def encode(self, value: NowPlaying) -> dict[str, Any]:
        track = value.track
        return {
            "title": track.title,
            "artist": track.artist,
            "album": track.album,
            "position": value.position,
            "duration": value.duration,
        }

    def decode(self, data: dict[str, Any]) -> NowPlaying:
        track = Track(str(data["title"]), str(data["artist"]), str(data["album"]))
        position, duration = float(data["position"]), float(data["duration"])
        cover = self._read_cover()
        self._cover_written = cover
        return NowPlaying(
            track=track,
            playing=False,
            position=min(max(position, 0.0), duration) if duration > 0 else 0.0,
            duration=max(duration, 0.0),
            taken_at=time.monotonic(),
            cover=cover,
        )

    def _write(self, value: NowPlaying) -> None:
        super()._write(value)
        self._write_cover(value.cover)

    def _read_cover(self) -> bytes | None:
        try:
            return self.cover_path.read_bytes() or None
        except OSError:
            return None

    def _write_cover(self, cover: bytes | None) -> None:
        if cover == self._cover_written:
            return
        if cover:
            tmp = self.cover_path.with_name(self.cover_path.name + ".tmp")
            tmp.write_bytes(cover)
            os.replace(tmp, self.cover_path)
        else:
            with contextlib.suppress(FileNotFoundError):
                self.cover_path.unlink()
        self._cover_written = cover
