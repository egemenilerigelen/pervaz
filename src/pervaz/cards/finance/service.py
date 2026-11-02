"""Fiyat servisi: arka planda veri çekme `core.polling.Poller` ile yapılır, burada durum tutulur.

`FeedState` kartın başlık bilgisini ve hata mesajını belirler. Veri zamanında gelmezse (uyku,
takılan istek) servis bunu ayrı bir zamanlayıcıyla fark edip yeniden ister.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Protocol

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from pervaz.cards.finance.models import FeedState, FeedStatus, Snapshot
from pervaz.cards.finance.providers import AllProvidersFailed
from pervaz.core.polling import Poller, retry_delay

logger = logging.getLogger(__name__)

# Son başarılı veri bu kadar yenileme süresinden eskiyse "gecikmeli" sayılır.
STALE_AFTER_INTERVALS = 3


class Fetcher(Protocol):
    def fetch(self) -> Snapshot: ...


def is_stale(last_success: datetime | None, interval: int, now: datetime) -> bool:
    if last_success is None:
        return True
    return now - last_success > timedelta(seconds=interval * STALE_AFTER_INTERVALS)


class PriceService(QObject):
    snapshot_changed = Signal(object)  # Snapshot
    state_changed = Signal(object)  # FeedState

    def __init__(
        self,
        fetcher: Fetcher,
        interval_seconds: int,
        initial: Snapshot | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._interval = interval_seconds
        self._snapshot = initial
        self._last_success: datetime | None = None
        self._state = FeedState(FeedStatus.STALE if initial else FeedStatus.LOADING)

        self._poller = Poller(fetcher.fetch, interval_seconds, self)
        self._poller.succeeded.connect(self._handle_success)
        self._poller.raised.connect(self._handle_failure)

        # Bilgisayar uykudan dönünce vb. durumlarda verinin bayatladığını yakalar.
        self._stale_check = QTimer(self)
        self._stale_check.setInterval(15_000)
        self._stale_check.timeout.connect(self._check_staleness)

    # --- Dış arayüz ---------------------------------------------------------

    @property
    def snapshot(self) -> Snapshot | None:
        return self._snapshot

    @property
    def state(self) -> FeedState:
        return self._state

    @property
    def _running(self) -> bool:
        return self._poller.running

    def start(self) -> None:
        if self._running:
            return
        self._stale_check.start()
        self.state_changed.emit(self._state)
        if self._snapshot is not None:
            self.snapshot_changed.emit(self._snapshot)
        self._poller.start()

    def stop(self) -> None:
        """Servisi durdurur. Süren istek beklenmez; sonucu yok sayılır."""
        self._poller.stop()
        self._stale_check.stop()

    def refresh(self) -> None:
        """Hemen veri çeker; süren bir istek varsa yenisini başlatmaz."""
        self._poller.refresh()

    def set_fetcher(self, fetcher: Fetcher) -> None:
        """Kaynağı değiştirir ve hemen yeni kaynaktan veri ister."""
        self._poller.set_fetch(fetcher.fetch)

    # --- İç işleyiş ---------------------------------------------------------

    @Slot(object)
    def _handle_success(self, snapshot: Snapshot) -> None:
        self._snapshot = snapshot
        self._last_success = snapshot.fetched_at
        logger.info("%s: %d fiyat alındı", snapshot.source_name, len(snapshot.quotes))
        self.snapshot_changed.emit(snapshot)
        self._set_state(FeedState(FeedStatus.LIVE, last_success=self._last_success))

    @Slot(object)
    def _handle_failure(self, error: Exception) -> None:
        if isinstance(error, AllProvidersFailed):
            errors = error.errors
        else:
            logger.error("Veri çekilirken beklenmedik hata", exc_info=error)
            errors = (f"Beklenmedik hata: {error.__class__.__name__}",)
        failures = self._poller.failures
        logger.warning(
            "Veri alınamadı (%d. hata), %ds sonra tekrar: %s",
            failures,
            retry_delay(failures, self._interval),
            "; ".join(errors),
        )
        status = FeedStatus.STALE if self._snapshot else FeedStatus.OFFLINE
        self._set_state(FeedState(status, self._last_success, tuple(errors)))

    @Slot()
    def _check_staleness(self) -> None:
        if self._state.status is not FeedStatus.LIVE:
            return
        if is_stale(self._last_success, self._interval, datetime.now()):
            self._set_state(FeedState(FeedStatus.STALE, self._last_success))
            self.refresh()

    def _set_state(self, state: FeedState) -> None:
        self._state = state
        self.state_changed.emit(state)
