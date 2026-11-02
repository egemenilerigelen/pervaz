"""Son başarılı katkı tablosu; internet yokken eski tabloyu göstermek için diske yazılır."""

from __future__ import annotations

from typing import Any, Protocol

from pervaz.cards.github.models import Contributions
from pervaz.infra.storage import JsonCache


class ContributionStore(Protocol):
    """Kartın ihtiyaç duyduğu önbellek arayüzü; testlerde değiştirilebilir."""

    def load(self) -> Contributions | None: ...

    def save(self, contributions: Contributions) -> None: ...


class ContributionCache(JsonCache[Contributions]):
    file_name = "github.json"
    invalid_message = "GitHub önbelleği geçersiz: %s"
    write_failed_message = "GitHub önbelleği yazılamadı: %s"

    def encode(self, value: Contributions) -> dict[str, Any]:
        return value.to_dict()

    def decode(self, data: dict[str, Any]) -> Contributions:
        return Contributions.from_dict(data)
