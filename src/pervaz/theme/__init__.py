"""Tema katmanı: belirteçler, stil sayfası ve ayarlardan çözümlenen `Look`."""

from __future__ import annotations

from dataclasses import dataclass

from pervaz.theme.stylesheet import build_stylesheet
from pervaz.theme.tokens import DENSITIES, THEMES, Metrics, Theme


@dataclass(frozen=True)
class Look:
    """Bir görünümün tamamı: tema renkleri + yoğunluk/yazı ölçeği + cam ayarı."""

    theme: Theme
    metrics: Metrics

    @property
    def stylesheet(self) -> str:
        return build_stylesheet(self.theme, self.metrics)


def resolve_look(
    theme_name: str,
    density: str,
    font_scale: float,
    accent: str | None = None,
    glass_opacity: float | None = None,
) -> Look:
    theme = THEMES.get(theme_name, THEMES["dark"])
    if accent:
        theme = theme.with_accent(accent)
    if glass_opacity is not None:
        theme = theme.with_glass_opacity(glass_opacity)
    metrics = Metrics(spacing=DENSITIES.get(density, 1.0), font=font_scale)
    return Look(theme=theme, metrics=metrics)


__all__ = ["Look", "Metrics", "Theme", "resolve_look"]
