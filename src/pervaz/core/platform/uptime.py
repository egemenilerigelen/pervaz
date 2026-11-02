"""Windows açılışından beri geçen süre."""

from __future__ import annotations

import ctypes
import sys


def uptime_seconds() -> int | None:
    """Açık kalma süresi (saniye); okunamazsa None."""
    if sys.platform != "win32":
        return None
    func = ctypes.windll.kernel32.GetTickCount64
    func.restype = ctypes.c_ulonglong
    return int(func() // 1000)
