"""JSON dosyalarını güvenli (atomik) okuma/yazma ve kartların ortak önbellek temeli."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, ClassVar, Generic, TypeVar

from pervaz.infra import paths

logger = logging.getLogger(__name__)

T = TypeVar("T")


def read_json(path: Path) -> Any | None:
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        logger.warning("%s okunamadı, yok sayılıyor: %s", path.name, exc)
        return None


def write_json(path: Path, data: Any) -> None:
    """Önce geçici dosyaya yazıp sonra yer değiştirir; yarım dosya kalmaz."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class JsonCache(Generic[T]):
    """Bir kartın son başarılı verisini kullanıcı klasöründeki tek bir JSON dosyasında tutar.

    Alt sınıf `file_name`, `encode` ve `decode` verir. Önbellek hatası kartı düşürmez: bozuk
    dosya uyarı + `None`, yazılamayan dosya yalnızca uyarıdır. Yazmaya ek iş eklemek (ör. ikili
    dosya) için `_write` genişletilir.
    """

    file_name: ClassVar[str]
    invalid_message: ClassVar[str] = "Önbellekteki veri geçersiz: %s"
    write_failed_message: ClassVar[str] = "Önbellek yazılamadı: %s"

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or paths.data_dir() / self.file_name

    def encode(self, value: T) -> dict[str, Any]:
        raise NotImplementedError

    def decode(self, data: dict[str, Any]) -> T:
        raise NotImplementedError

    def load(self) -> T | None:
        data = read_json(self.path)
        if not isinstance(data, dict):
            return None
        try:
            return self.decode(data)
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(self.invalid_message, exc)
            return None

    def save(self, value: T) -> None:
        try:
            self._write(value)
        except OSError as exc:
            logger.warning(self.write_failed_message, exc)

    def _write(self, value: T) -> None:
        write_json(self.path, self.encode(value))


__all__ = ["JsonCache", "read_json", "write_json"]
