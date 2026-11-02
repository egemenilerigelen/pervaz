"""Finans kartının son başarılı verisi: uygulama açılır açılmaz ekranda bir şey olsun diye."""

from __future__ import annotations

from typing import Any, Protocol

from pervaz.cards.finance.models import Snapshot
from pervaz.infra.storage import JsonCache


class SnapshotStore(Protocol):
    """Kartın ihtiyaç duyduğu önbellek arayüzü; testlerde değiştirilebilir."""

    def load(self) -> Snapshot | None: ...

    def save(self, snapshot: Snapshot) -> None: ...


class SnapshotCache(JsonCache[Snapshot]):
    file_name = "finance.json"

    def encode(self, value: Snapshot) -> dict[str, Any]:
        return value.to_dict()

    def decode(self, data: dict[str, Any]) -> Snapshot:
        return Snapshot.from_dict(data)
