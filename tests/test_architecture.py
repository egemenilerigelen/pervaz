"""Katman kuralları: bağımlılık yalnızca aşağıya doğru olabilir.

    app  ->  cards/<özellik>  ->  core  ->  infra, theme

- `identity` (uygulamanın kimliği) hiçbir şeyi bilmez, herkes onu okuyabilir.
- `theme` ve `infra` hiçbir üst katmanı bilmez.
- `core` (panel iskeleti) hiçbir karta ve `app`'e bağımlı olmaz; kartlar çekirdeğe yalnızca
  `CardSpec` aracılığıyla takılır.
- Her kart özelliği (`cards/weather`, `cards/finance`...) yalnızca kendi paketini, `core`,
  `infra` ve `theme`'i kullanır; kartlar birbirini bilmez.
- `core/platform` (Windows'a özgü kod) yalnızca kendi paketini ve `identity`'yi kullanır.
- Yalnızca `app` (birleştirme noktası) her şeyi bilebilir; kimse `app`'i import etmez.
- Paket içinde döngüsel import yoktur.
- `cards/` altındaki her paket bir `SPEC` dışa aktarır ve `CARDS` içinde kayıtlıdır.

Yeni bir bağımlılık bu kurallara aykırıysa test düşer; kuralı gevşetmek yerine bağımlılığı
doğru katmana taşımak gerekir.
"""

import ast
import importlib
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
ROOT = "pervaz"


def _modules():
    for path in sorted((SRC / ROOT).rglob("*.py")):
        parts = list(path.relative_to(SRC).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        yield ".".join(parts), path


def _imports(path, known):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
    resolved = set()
    for name in found:
        # `from paket import isim`: isim modül değil nitelikse (ör. __version__) pakete indirgenir.
        while name not in known and "." in name:
            name = name.rsplit(".", 1)[0]
        if name == ROOT or name.startswith(ROOT + "."):
            resolved.add(name)
    return resolved


def _layer(module):
    """Modülün katmanı: identity, theme, infra, core, core.platform, cards, cards.<özellik>, app."""
    parts = module.split(".")[1:]
    if not parts:
        return "root"
    if parts[0] == "cards":
        return "cards" if len(parts) == 1 else f"cards.{parts[1]}"
    if parts[0] == "core" and len(parts) > 1 and parts[1] == "platform":
        return "core.platform"
    return parts[0]


def _allowed(layer, target_layer):
    if target_layer in ("identity", layer):
        return True  # kimlik sabitleri ve kendi katmanı
    if layer in ("identity", "core.platform"):
        return False
    if target_layer == "root":
        return True  # paket kökü (__version__)
    if layer in ("theme", "infra"):
        return False
    if layer == "core":
        return target_layer in ("theme", "infra", "core.platform")
    if layer == "cards":  # kart kayıt defteri: özellikleri toplar
        return target_layer.startswith("cards.") or target_layer in ("core", "core.platform")
    if layer.startswith("cards."):  # tek bir kart özelliği
        return target_layer in ("core", "theme", "infra")
    return layer in ("app", "__main__")


KNOWN = {module for module, _ in _modules()}
VIOLATIONS = []
for module, path in _modules():
    for target in _imports(path, KNOWN):
        if not _allowed(_layer(module), _layer(target)):
            VIOLATIONS.append(f"{module} -> {target}")


def test_layering_rules_hold():
    assert not VIOLATIONS, "Katman kuralı ihlalleri:\n  " + "\n  ".join(VIOLATIONS)


@pytest.mark.parametrize(
    ("module", "layer"),
    [
        ("pervaz.core.panel.window", "core"),
        ("pervaz.core.cards.base", "core"),
        ("pervaz.core.platform.hotkey", "core.platform"),
        ("pervaz.cards.weather.card", "cards.weather"),
        ("pervaz.cards", "cards"),
        ("pervaz.infra.http", "infra"),
        ("pervaz.identity", "identity"),
        ("pervaz.app.controller", "app"),
        ("pervaz", "root"),
    ],
)
def test_layer_detection(module, layer):
    assert _layer(module) == layer


def test_rules_reject_forbidden_directions():
    assert not _allowed("core", "cards.weather")
    assert not _allowed("cards.weather", "cards.finance")
    assert not _allowed("cards.weather", "app")
    assert not _allowed("infra", "core")
    assert not _allowed("theme", "infra")
    assert not _allowed("core", "app")
    assert not _allowed("core.platform", "core")
    assert not _allowed("core.platform", "theme")
    assert not _allowed("core.platform", "root")
    assert not _allowed("identity", "root")
    assert not _allowed("identity", "infra")
    assert _allowed("cards.weather", "core")
    assert _allowed("app", "cards.weather")
    assert _allowed("core.platform", "identity")
    assert _allowed("theme", "identity")
    assert _allowed("infra", "root")


def _module_edges(path, known):
    """Modülün gerçek bağımlılıkları: `from paket import modül` yalnızca modülü sayar; paketin
    kendisini de saymak, `__init__`'i kart modülünü dışa aktaran her pakette sahte döngü verirdi."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    edges = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for alias in node.names:
                name = f"{node.module}.{alias.name}"
                edges.add(name if name in known else node.module)
        elif isinstance(node, ast.Import):
            edges.update(alias.name for alias in node.names)
    return edges & known


def _find_cycle(graph):
    """Bağımlılık grafiğindeki ilk döngüyü (modül listesi) döndürür; döngü yoksa None."""
    done = set()

    def visit(node, trail):
        if node in trail:
            return [*trail[trail.index(node) :], node]
        if node in done:
            return None
        for target in sorted(graph.get(node, ())):
            cycle = visit(target, [*trail, node])
            if cycle:
                return cycle
        done.add(node)
        return None

    for node in sorted(graph):
        cycle = visit(node, [])
        if cycle:
            return cycle
    return None


def test_no_circular_imports():
    graph = {module: _module_edges(path, KNOWN) for module, path in _modules()}
    cycle = _find_cycle(graph)
    assert cycle is None, "Döngüsel import: " + " -> ".join(cycle or [])


def test_cycle_detection_finds_cycles():
    assert _find_cycle({"a": {"b"}, "b": {"c"}, "c": {"a"}}) == ["a", "b", "c", "a"]
    assert _find_cycle({"a": {"b", "c"}, "b": {"c"}, "c": set()}) is None
    assert _find_cycle({"a": {"a"}}) == ["a", "a"]


def _card_packages():
    cards = SRC / ROOT / "cards"
    return sorted(p.parent.name for p in cards.glob("*/__init__.py"))


def test_card_packages_are_found():
    assert "weather" in _card_packages()


@pytest.mark.parametrize("name", _card_packages())
def test_card_package_exports_spec_and_is_registered(name):
    from pervaz.cards import CARDS
    from pervaz.core.cards.base import CardSpec

    package = importlib.import_module(f"{ROOT}.cards.{name}")
    assert isinstance(package.SPEC, CardSpec)
    assert "SPEC" in package.__all__
    assert package.SPEC in CARDS, f"{name} kartı CARDS listesine eklenmemiş"


def test_nothing_else_is_registered():
    from pervaz.cards import CARDS

    assert len(CARDS) == len(_card_packages())
