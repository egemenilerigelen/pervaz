"""Bileşenleri birbirine bağlayan denetleyici.

Burası bileşenlerin tek bağlandığı yerdir (composition root): çekirdek (`core`) kartları,
kartlar da birbirini bilmez; kimin kime bağlanacağı yalnızca burada belirlenir.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from PySide6.QtCore import QObject, QTimer, Slot
from PySide6.QtGui import QIcon, QScreen
from PySide6.QtWidgets import QApplication

from pervaz.cards import CARDS
from pervaz.core.cards.base import CardSpec
from pervaz.core.cards.manager import CardManager
from pervaz.core.panel.auto_close import PanelAutoClose, Pointer
from pervaz.core.panel.screens import resolve_screen
from pervaz.core.panel.window import PanelWindow
from pervaz.core.platform.hotkey import HotkeyManager
from pervaz.core.platform.mouse import SystemPointer
from pervaz.core.settings import SettingsStore, look_from_settings
from pervaz.core.tray import TrayIcon
from pervaz.core.trigger import create_trigger
from pervaz.identity import APP_DISPLAY_NAME
from pervaz.infra import paths

logger = logging.getLogger(__name__)


class AppController(QObject):
    def __init__(
        self,
        app: QApplication,
        specs: Sequence[CardSpec] | None = None,
        hotkeys: HotkeyManager | None = None,
        store: SettingsStore | None = None,
        pointer: Pointer | None = None,
    ) -> None:
        super().__init__()
        self._app = app
        self._store = store or SettingsStore(paths.settings_file())
        self.settings = self._store.load()
        self.look = look_from_settings(self.settings)

        icon = QIcon(str(paths.ICON_PATH))
        self.manager = CardManager(
            specs if specs is not None else CARDS,
            self.settings.cards,
            self.look,
            animate=self.settings.animations,
            parent=self,
        )
        self.settings = self.settings.with_changes(cards=self.manager.card_settings())

        self.panel = PanelWindow(self.look, self.settings)
        self.panel.setWindowIcon(icon)
        self.panel.set_pinned(self.settings.pinned)
        for host in self.manager.hosts:
            self.panel.add_host(host)

        self.trigger = create_trigger(self.settings.trigger_kind)
        self.trigger.configure(self.settings, self.look)
        self.hotkeys = hotkeys or HotkeyManager(self)
        self.auto_close = PanelAutoClose(
            zone=self.panel.target_rect,
            policy=lambda: self.settings,
            pointer=pointer or SystemPointer(),
            parent=self,
        )

        self._hover_screen: QScreen | None = None
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._open_hovered)

        self.tray: TrayIcon | None = None
        if TrayIcon.is_available():
            self.tray = TrayIcon(icon, APP_DISPLAY_NAME, self.settings.pinned, self)
            app.setQuitOnLastWindowClosed(False)

        self._connect()

    def _connect(self) -> None:
        self.trigger.hovered.connect(self._on_trigger_hovered)
        self.trigger.activated.connect(self.open_panel)
        self.hotkeys.triggered.connect(lambda: self.toggle_panel(self.settings.hotkey_screen))
        self.panel.pin_clicked.connect(lambda: self.set_pinned(not self.settings.pinned))
        self.panel.shown.connect(self.trigger.hide)
        self.auto_close.close_requested.connect(self.close_panel)
        self.manager.collapsed_changed.connect(self._on_collapsed)
        self.manager.config_changed.connect(self._on_card_config)
        self._app.aboutToQuit.connect(self._shutdown)
        if self.tray is not None:
            self.tray.toggle_requested.connect(lambda: self.toggle_panel("cursor"))
            self.tray.pin_toggled.connect(self.set_pinned)
            self.tray.quit_requested.connect(self.quit)

    # --- Yaşam döngüsü ------------------------------------------------------

    def start(self) -> None:
        screen = resolve_screen(self.settings.trigger_screen)
        self.trigger.show_on(screen)
        if self.settings.hotkey and not self.hotkeys.register(self.settings.hotkey):
            self._notify(
                f"'{self.settings.hotkey}' kısayolu kaydedilemedi; başka bir uygulama "
                "kullanıyor olabilir. Paneli tutamaçtan ya da tepsi ikonundan açabilirsin."
            )
        if self.tray:
            self.tray.show()
        if self.settings.pinned:
            self.open_panel(screen)

    @Slot()
    def quit(self) -> None:
        self._app.quit()

    @Slot()
    def _shutdown(self) -> None:
        self.auto_close.stop()
        self.manager.shutdown()
        self.hotkeys.unregister()
        self.trigger.shutdown()
        if self.tray:
            self.tray.hide()
        self._store.save(self.settings)

    def _notify(self, message: str) -> None:
        logger.warning(message)
        if self.tray:
            self.tray.warn(message)

    # --- Panel açma / kapama ------------------------------------------------

    @Slot(QScreen)
    def open_panel(self, screen: QScreen) -> None:
        if self.panel.is_open:
            return
        self._hover_timer.stop()
        # Kartlar önce uyanır: panelin efekte giren görüntüsü güncel olsun. Tutamaç, panel
        # içinden çıkıp yerine oturana kadar görünür kalır.
        self.manager.show_all()
        self.panel.open_on(screen, self.trigger.anchor_on(screen))
        self.auto_close.start()

    def close_panel(self, force: bool = False) -> None:
        """Sabitliyken yalnızca `force` ile (kısayol, tepsi, iğne) kapanır."""
        if not self.panel.is_open or (self.settings.pinned and not force):
            return
        self._hover_timer.stop()
        self.auto_close.stop()
        self.trigger.show_on(resolve_screen(self.settings.trigger_screen))  # panel içine girecek
        self.panel.close_panel()
        self.manager.hide_all()

    def toggle_panel(self, screen_spec: str) -> None:
        if self.panel.is_open:
            self.close_panel(force=True)
        else:
            self.open_panel(resolve_screen(screen_spec))

    @Slot(QScreen, bool)
    def _on_trigger_hovered(self, screen: QScreen, entered: bool) -> None:
        if self.settings.open_mode != "hover":
            return
        if entered:
            self._hover_screen = screen
            self._hover_timer.start(self.settings.hover_delay_ms)
        else:
            self._hover_timer.stop()

    @Slot()
    def _open_hovered(self) -> None:
        if self._hover_screen is not None:
            self.open_panel(self._hover_screen)

    # --- Ayar değişiklikleri --------------------------------------------------

    def _update_settings(self, **changes) -> None:
        self.settings = self.settings.with_changes(**changes)
        self._store.save(self.settings)

    @Slot(bool)
    def set_pinned(self, pinned: bool) -> None:
        self._update_settings(pinned=pinned)
        self.panel.set_pinned(pinned)
        if self.tray is not None:
            self.tray.set_pinned(pinned)
        if not pinned:
            self.auto_close.reset()  # sabitlik kalkınca fare takibi sıfırdan başlasın

    @Slot(str, bool)
    def _on_collapsed(self, card_id: str, collapsed: bool) -> None:
        self.manager.set_collapsed(card_id, collapsed)
        self._update_settings(cards=self.manager.card_settings())

    @Slot(str, object)
    def _on_card_config(self, card_id: str, config: dict) -> None:
        self.manager.set_config(card_id, config)
        self._update_settings(cards=self.manager.card_settings())
