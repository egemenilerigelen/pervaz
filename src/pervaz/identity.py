"""Uygulamanın kimliği: adlar, Windows kimliği, veri klasörü değişkeni ve proje adresi.

Bu metinler yalnızca burada yazılır; başka her yer buradan okur.
"""

from __future__ import annotations

APP_NAME = "Pervaz"  # teknik ad: veri klasörü, QApplication, User-Agent
APP_DISPLAY_NAME = "Pervaz"  # kullanıcıya görünen ad
APP_USER_MODEL_ID = f"{APP_NAME}.Panel"  # Windows görev çubuğu kimliği
DATA_DIR_ENV = "PERVAZ_DATA_DIR"  # verilirse veri klasörü burası olur (testler kullanır)
APP_URL = "https://github.com/egemenilerigelen/pervaz"

__all__ = ["APP_DISPLAY_NAME", "APP_NAME", "APP_URL", "APP_USER_MODEL_ID", "DATA_DIR_ENV"]
