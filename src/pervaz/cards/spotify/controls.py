"""Spotify kartının denetim satırları: ilerleme çubuğu, oynatma düğmeleri, ses ve çıkış cihazı.

Satırlar yalnızca çizer ve kullanıcı olaylarını dışarı açar; komutları kart gönderir.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import QPoint, QSignalBlocker, Qt
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QHBoxLayout, QMenu, QToolButton, QWidget

from pervaz.cards.spotify.formatting import format_time
from pervaz.cards.spotify.models import AudioOutput, NowPlaying, Repeat, Volume
from pervaz.cards.spotify.widgets import JumpSlider
from pervaz.core.widgets import make_label, repolish
from pervaz.theme import Look
from pervaz.theme.tokens import rgba

SEEK_STEPS = 10  # ilerleme çubuğunun çözünürlüğü: saniyede 10 adım
TIME_WIDTH = 28  # süre yazılarının genişliği (mantıksal px)
ICON_WIDTH = 22  # alt satırdaki simge düğmelerinin genişliği

# Segoe MDL2 Assets karakterleri
PLAY, PAUSE = "", ""
PREVIOUS, NEXT = "", ""
SHUFFLE, REPEAT_LIST, REPEAT_TRACK = "", "", ""
VOLUME, MUTED, OUTPUT = "", "", ""


def accent_stylesheet(accent: str) -> str:
    """Temanın vurgusunu şarkının rengiyle değiştiren kurallar (aynı seçiciler, kart düzeyi)."""
    return f"""
QSlider[role="seek"]::sub-page:horizontal {{ background: {accent}; }}
QToolButton[role="icon"][active="true"] {{ color: {accent}; }}
QToolButton[role="play"][playing="false"] {{ background: {rgba(accent, 0.38)}; }}
QToolButton[role="play"][playing="false"]:hover {{ background: {rgba(accent, 0.5)}; }}
"""


def _tool(glyph: str, tooltip: str, role: str = "icon") -> QToolButton:
    button = QToolButton()
    button.setText(glyph)
    button.setToolTip(tooltip)
    button.setProperty("role", role)
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def _set_flag(button: QToolButton, name: str, value: bool) -> None:
    """Düğmenin stil sayfasında kullanılan dinamik özelliği (`active`, `playing`)."""
    if button.property(name) != value:
        button.setProperty(name, value)
        repolish(button)


def _set_value(slider: JumpSlider, value: int) -> None:
    """Değeri programla değiştirir; kullanıcı değişikliği gibi sinyal yayınlamaz."""
    if slider.value() != value:
        with QSignalBlocker(slider):
            slider.setValue(value)


class ProgressRow(QWidget):
    """Geçen süre, ilerleme çubuğu ve toplam süre."""

    def __init__(self, look: Look, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        sp = look.metrics.sp
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(sp(4))
        self.elapsed = make_label("0:00", "dim")
        self.total = make_label("0:00", "dim")
        # Süreler, altındaki simgelerle aynı sütunda ortalanır.
        for label in (self.elapsed, self.total):
            label.setFixedWidth(sp(TIME_WIDTH))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.seek = JumpSlider("seek")
        self.seek.valueChanged.connect(self._on_moved)
        row.addWidget(self.elapsed)
        row.addWidget(self.seek, 1)
        row.addWidget(self.total)

    def _on_moved(self, value: int) -> None:
        if self.seek.isSliderDown():
            self.elapsed.setText(format_time(value / SEEK_STEPS))

    def clear(self) -> None:
        self.elapsed.setText("0:00")
        self.total.setText("0:00")
        self.seek.setEnabled(False)
        _set_value(self.seek, 0)

    def show_position(self, now_playing: NowPlaying, position: float, live: bool) -> None:
        steps = round(now_playing.duration * SEEK_STEPS)
        with QSignalBlocker(self.seek):
            self.seek.setRange(0, steps)
        self.seek.setEnabled(live and now_playing.can_seek and steps > 0)
        self.total.setText(format_time(now_playing.duration))
        if not self.seek.isSliderDown():  # sürüklerken değeri kullanıcı belirler
            _set_value(self.seek, round(position * SEEK_STEPS))
            self.elapsed.setText(format_time(position))


class TransportRow(QWidget):
    """Yalnızca düğmeler: oynat kartın tam ortasında."""

    def __init__(self, look: Look, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(look.metrics.sp(10))
        self.shuffle = _tool(SHUFFLE, "Karıştır")
        self.previous = _tool(PREVIOUS, "Önceki")
        self.play = _tool(PLAY, "Oynat", role="play")
        self.next = _tool(NEXT, "Sonraki")
        self.repeat = _tool(REPEAT_LIST, "Tekrarla")
        row.addStretch()
        for button in (self.shuffle, self.previous, self.play, self.next, self.repeat):
            row.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch()

    def show_state(self, now_playing: NowPlaying | None, live: bool) -> None:
        np = now_playing
        live = live and np is not None
        playing = live and np.playing
        self.play.setText(PAUSE if playing else PLAY)
        _set_flag(self.play, "playing", playing)  # çalarken içi boş, duraklayınca dolu
        self.play.setToolTip("Duraklat" if playing else "Oynat")
        self.play.setEnabled(live)
        self.previous.setEnabled(live and np.can_previous)
        self.next.setEnabled(live and np.can_next)
        self.shuffle.setEnabled(live and np.can_shuffle)
        _set_flag(self.shuffle, "active", live and np.shuffle)
        repeat = np.repeat if live else Repeat.OFF
        self.repeat.setEnabled(live and np.can_repeat)
        self.repeat.setText(REPEAT_TRACK if repeat is Repeat.TRACK else REPEAT_LIST)
        _set_flag(self.repeat, "active", repeat is not Repeat.OFF)


class AudioRow(QWidget):
    """Satırın tamamı ses: solda sessize alma, sağda çıkış cihazı simgesi (tıklayınca cihaz
    listesi açılır; seçili cihazın adı ipucunda). Simgeler dar ve eşit genişlikte: ses çubuğu
    ilerleme çubuğundan uzun, satır iki yanda simetrik."""

    def __init__(self, look: Look, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        sp = look.metrics.sp
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(sp(4))
        self.mute = _tool(VOLUME, "Sistem sesini kapat")
        self.slider = JumpSlider("volume")
        self.slider.setRange(0, 100)
        self.slider.setMinimumWidth(sp(40))
        self.slider.setToolTip("Sistem sesi")
        self.output = _tool(OUTPUT, "Ses çıkışı", role="output")
        for button in (self.mute, self.output):
            button.setFixedWidth(sp(ICON_WIDTH))
        row.addWidget(self.mute, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.slider, 1, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.output, 0, Qt.AlignmentFlag.AlignVCenter)
        self.outputs_menu: QMenu | None = None

    def show_volume(self, volume: Volume | None) -> None:
        self.slider.setEnabled(volume is not None)
        self.mute.setEnabled(volume is not None)
        if volume is None:
            return
        if not self.slider.isSliderDown():
            _set_value(self.slider, round(volume.level * 100))
        silent = volume.muted or volume.level == 0
        self.mute.setText(MUTED if silent else VOLUME)
        self.mute.setToolTip("Sistem sesini aç" if volume.muted else "Sistem sesini kapat")

    def show_output(self, output: AudioOutput | None) -> None:
        self.output.setToolTip(f"Ses çıkışı: {output.name}" if output is not None else "Ses çıkışı")

    def open_outputs_menu(
        self,
        outputs: Sequence[AudioOutput],
        on_select: Callable[[AudioOutput], None],
        left_limit: int,
    ) -> None:
        if self.outputs_menu is not None:
            self.outputs_menu.deleteLater()
        menu = self.outputs_menu = QMenu(self)
        group = QActionGroup(menu)
        for output in outputs:
            action = menu.addAction(output.name)
            action.setCheckable(True)
            action.setChecked(output.is_default)
            action.triggered.connect(lambda _checked=False, o=output: on_select(o))
            group.addAction(action)
        if not outputs:
            menu.addAction("Çıkış cihazı bulunamadı").setEnabled(False)
        # Simgenin sol aşağısına açılır: menünün sağ üst köşesi simgenin sağ alt köşesinde.
        # Menü `left_limit`ten (kartın sol kenarı) taşacak kadar genişse oraya hizalanır; böylece
        # panelin dışına çıkıp 'dışarı tıklama' sayılmaz.
        corner = self.output.mapToGlobal(QPoint(self.output.width(), self.output.height()))
        menu.popup(QPoint(max(corner.x() - menu.sizeHint().width(), left_limit), corner.y()))
