import json
import logging
from typing import ClassVar

import pytest

from pervaz.identity import DATA_DIR_ENV
from pervaz.infra.storage import JsonCache, read_json, write_json


class _Numbers(JsonCache[list[int]]):
    file_name = "numbers.json"

    def encode(self, value):
        return {"values": value}

    def decode(self, data):
        return [int(v) for v in data["values"]]


@pytest.fixture
def path(tmp_path):
    return tmp_path / "numbers.json"


def test_write_json_leaves_no_temp_file_and_keeps_turkish_text(tmp_path, path):
    write_json(path, {"ad": "Çiğdem"})
    assert [p.name for p in tmp_path.iterdir()] == ["numbers.json"]
    assert "Çiğdem" in path.read_text(encoding="utf-8")
    assert read_json(path) == {"ad": "Çiğdem"}


def test_read_json_ignores_missing_and_corrupt_files(path):
    assert read_json(path) is None
    path.write_text("bozuk {", encoding="utf-8")
    assert read_json(path) is None


def test_roundtrip(path):
    cache = _Numbers(path)
    cache.save([1, 2])
    assert json.loads(path.read_text(encoding="utf-8")) == {"values": [1, 2]}
    assert _Numbers(path).load() == [1, 2]


def test_default_location_is_the_data_folder(tmp_path, monkeypatch):
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path / "veri"))
    assert _Numbers().path == tmp_path / "veri" / "numbers.json"


def test_missing_file_is_silently_empty(path, caplog):
    assert _Numbers(path).load() is None
    assert not caplog.records


@pytest.mark.parametrize("content", ["bozuk {", "[1, 2]", '"metin"', "null"])
def test_unreadable_or_non_object_content_is_empty(path, content):
    path.write_text(content, encoding="utf-8")
    assert _Numbers(path).load() is None


@pytest.mark.parametrize("content", ['{"yok": 1}', '{"values": 3}', '{"values": ["x"]}'])
def test_invalid_shape_warns_and_is_empty(path, content, caplog):
    path.write_text(content, encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        assert _Numbers(path).load() is None
    assert "geçersiz" in caplog.text


def test_unwritable_location_warns_and_does_not_raise(tmp_path, caplog):
    blocked = tmp_path / "dosya"
    blocked.write_text("x")
    with caplog.at_level(logging.WARNING):
        _Numbers(blocked / "alt" / "numbers.json").save([1])
    assert "yazılamadı" in caplog.text


def test_subclass_can_name_its_own_log_messages(path, caplog):
    class _Named(_Numbers):
        invalid_message: ClassVar[str] = "Sayı önbelleği bozuk: %s"

    path.write_text("{}", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        assert _Named(path).load() is None
    assert "Sayı önbelleği bozuk" in caplog.text


def test_write_can_be_extended(path, tmp_path):
    class _WithExtra(_Numbers):
        def _write(self, value):
            super()._write(value)
            (tmp_path / "ek.bin").write_bytes(bytes(value))

    _WithExtra(path).save([7])
    assert (tmp_path / "ek.bin").read_bytes() == b"\x07"


def test_extra_write_is_skipped_when_the_json_could_not_be_written(tmp_path):
    written = []

    class _WithExtra(_Numbers):
        def _write(self, value):
            super()._write(value)
            written.append(value)

    blocked = tmp_path / "dosya"
    blocked.write_text("x")
    _WithExtra(blocked / "alt" / "numbers.json").save([1])
    assert written == []
