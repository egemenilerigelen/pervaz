"""Uygulama ikonunu (src/pervaz/assets/icon.ico) üretir.

İkon elle çizilmiş bir dosya değil, bu betiğin çıktısıdır; değiştirmek için
betiği düzenleyip yeniden çalıştırın:

    python tools/make_icon.py

Tasarım: panelin kendisi. Koyu, yuvarlatılmış kare bir zeminde sağ kenara yaslı ince
vurgu şeridi (pervaz) ve solunda üst üste duran yuvarlak köşeli kartlar. Renkler koyu
temanın belirteçlerinden gelir. Küçük boyutlar küçültülmez, kendi yerleşimiyle çizilir:
16 ve 24 px'te iki kart ve kalın şerit kalır, böylece görev çubuğunda da okunur.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from pervaz.theme.tokens import DARK, blend, parse_hex

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "src" / "pervaz" / "assets" / "icon.ico"
SIZES = [16, 24, 32, 48, 64, 128, 256]
BOX = 64  # yerleşim birimi: ikon 64x64'lük bir kutuda tasarlanır
OVERSAMPLE = 8  # kenarlar yumuşasın diye büyük çizilip küçültülür

BACKGROUND = blend(DARK.ink, DARK.bg, 0.09)
EDGE = blend(DARK.ink, DARK.bg, 0.20)
ACCENT = DARK.accent
CARD_TONES = (DARK.text, DARK.text_soft, DARK.text_dim)


@dataclass(frozen=True)
class Layout:
    """Tüm ölçüler `BOX` biriminde."""

    margin: float  # zeminin ikon kenarına uzaklığı
    radius: float  # zeminin köşe yarıçapı
    strip: float  # şeridin kalınlığı
    strip_inset: float  # şeridin zeminin sağ, üst ve alt kenarına uzaklığı
    card_left: float  # kartların zeminin sol kenarına uzaklığı
    card_gap: float  # kartlar arası boşluk ve kartların şeride uzaklığı
    card_radius: float
    cards: int


LARGE = Layout(2, 13, 6, 8, 9, 5, 3.5, 3)
SMALL = Layout(0, 12, 12, 8, 8, 8, 4, 2)  # 16 ve 24 px: 1 px'lik ayrıntılar kaybolmasın


def draw_icon(size: int) -> Image.Image:
    layout = SMALL if size <= 24 else LARGE
    scale = size * OVERSAMPLE / BOX

    def at(*values: float) -> tuple[float, ...]:
        return tuple(value * scale for value in values)

    canvas = size * OVERSAMPLE
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    outer = BOX - layout.margin
    draw.rounded_rectangle(
        at(layout.margin, layout.margin, outer, outer),
        radius=layout.radius * scale,
        fill=parse_hex(BACKGROUND),
        outline=parse_hex(EDGE),
        width=max(1, round(scale)),
    )

    top = layout.margin + layout.strip_inset
    bottom = outer - layout.strip_inset
    strip_right = outer - layout.strip_inset
    strip_left = strip_right - layout.strip
    draw.rounded_rectangle(
        at(strip_left, top, strip_right, bottom),
        radius=layout.strip / 2 * scale,
        fill=parse_hex(ACCENT),
    )

    left = layout.margin + layout.card_left
    right = strip_left - layout.card_gap
    gaps = (layout.cards - 1) * layout.card_gap
    height = (bottom - top - gaps) / layout.cards
    for index in range(layout.cards):
        y = top + index * (height + layout.card_gap)
        draw.rounded_rectangle(
            at(left, y, right, y + height),
            radius=layout.card_radius * scale,
            fill=parse_hex(CARD_TONES[index]),
        )
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    frames = [draw_icon(size) for size in SIZES]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frames[-1].save(OUTPUT, format="ICO", sizes=[(s, s) for s in SIZES], append_images=frames[:-1])
    print(f"{OUTPUT.relative_to(ROOT)} yazıldı ({', '.join(map(str, SIZES))} px)")


if __name__ == "__main__":
    main()
