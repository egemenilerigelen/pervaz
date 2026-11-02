"""Kartın konum menüsünde sunulan şehirler."""

from __future__ import annotations

from pervaz.cards.weather.models import Place

DEFAULT_CITY = "Urla"

# Menüdeki konumlar; koordinatlar sabit olduğundan seçimde ağdan konum aranmaz.
PLACES = {
    "Aydın": Place("Aydın", "Aydın", 37.8560, 27.8416),
    "Urla": Place("Urla", "Urla", 38.3222, 26.7647),
    "İzmir": Place("İzmir", "İzmir", 38.4237, 27.1428),
}
