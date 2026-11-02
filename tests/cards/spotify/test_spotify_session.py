"""Çalma oturumu: Qt'siz, sahte saat ve sahte önbellekle."""

from dataclasses import replace

import pytest

from pervaz.cards.spotify.models import AudioOutput, NowPlaying, Reading, Repeat, Track, Volume
from pervaz.cards.spotify.session import PlaybackSession
from pervaz.cards.spotify.state import HOLD_SECONDS, VOLUME_HOLD_SECONDS

TRACK = Track("Ara Beni Lütfen", "Kenan Doğulu", "Festival")
DEFAULT_VOLUME = Volume(0.7, False)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Store:
    def __init__(self, loaded=None):
        self.loaded = loaded
        self.saved = []

    def load(self):
        return self.loaded

    def save(self, now_playing):
        self.saved.append(now_playing)


def playing(clock, **kwargs):
    fields = {
        "track": TRACK,
        "playing": True,
        "position": 10.0,
        "duration": 200.0,
        "taken_at": clock.now,
    }
    return NowPlaying(**{**fields, **kwargs})


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def store():
    return Store()


@pytest.fixture
def session(clock, store):
    return PlaybackSession(clock, store)


def go_live(session, clock, volume=DEFAULT_VOLUME, **kwargs):
    session.apply(Reading(playing(clock, **kwargs), volume))


def test_starts_with_the_last_remembered_track_but_not_live(clock):
    last = playing(clock, playing=False)
    session = PlaybackSession(clock, Store(last))

    assert session.now_playing == last
    assert not session.live
    assert session.controllable() is None


def test_live_session_is_controllable_and_ticks_only_while_playing(session, clock):
    go_live(session, clock)
    assert session.controllable() is session.now_playing
    assert session.ticking

    go_live(session, clock, playing=False)
    assert not session.ticking


def test_position_advances_only_while_live_and_playing(session, clock):
    go_live(session, clock, position=10.0)
    clock.now += 5
    assert session.position() == 15.0

    session.apply(Reading(None, None))  # Spotify kapandı: konum donar
    clock.now += 5
    assert session.position() == 10.0


def test_a_new_track_is_saved_once(session, clock, store):
    go_live(session, clock)
    go_live(session, clock)
    assert len(store.saved) == 1

    go_live(session, clock, track=Track("Başka", "Biri", "Albüm"))
    assert len(store.saved) == 2


def test_closing_spotify_saves_the_last_position(session, clock, store):
    go_live(session, clock, position=10.0)
    clock.now += 7
    session.apply(Reading(None, None))

    assert store.saved[-1].position == 17.0


def test_remember_if_live_does_nothing_when_not_live(session, store):
    session.remember_if_live()
    assert store.saved == []


def test_toggle_playing_shows_the_change_and_freezes_the_position(session, clock):
    go_live(session, clock, position=10.0)
    clock.now += 3

    assert session.toggle_playing() is False
    assert session.now_playing.playing is False
    assert session.now_playing.position == 13.0


def test_stale_reading_does_not_undo_a_fresh_command(session, clock):
    go_live(session, clock)
    session.toggle_playing()

    go_live(session, clock)  # Spotify henüz eski durumu bildiriyor
    assert session.now_playing.playing is False

    clock.now += HOLD_SECONDS + 0.1
    go_live(session, clock)  # süre doldu: Spotify'ın dediği geçerli
    assert session.now_playing.playing is True


def test_commands_do_nothing_when_spotify_is_not_live(session):
    assert session.toggle_playing() is None
    assert session.toggle_shuffle() is None
    assert session.cycle_repeat() is None
    assert session.seek(30.0) is False


def test_shuffle_and_repeat_return_the_new_value(session, clock):
    go_live(session, clock, shuffle=False, repeat=Repeat.OFF)

    assert session.toggle_shuffle() is True
    assert session.cycle_repeat() is Repeat.LIST
    assert session.now_playing.shuffle is True
    assert session.now_playing.repeat is Repeat.LIST


def test_seek_moves_the_position_immediately(session, clock):
    go_live(session, clock)

    assert session.seek(90.0) is True
    assert session.position() == 90.0


def test_dragging_the_volume_holds_against_readings(session, clock):
    go_live(session, clock, volume=Volume(0.7, False))

    assert session.drag_volume(0.3) == Volume(0.3, False)
    go_live(session, clock, volume=Volume(0.7, False))
    assert session.volume == Volume(0.3, False)

    clock.now += VOLUME_HOLD_SECONDS + 0.1
    go_live(session, clock, volume=Volume(0.7, False))
    assert session.volume == Volume(0.7, False)


def test_dragging_while_muted_also_unmutes(session, clock):
    go_live(session, clock, volume=Volume(0.5, True))

    session.drag_volume(0.2)

    assert session.take_pending_volume() == (0.2, True)
    assert session.take_pending_volume() is None


def test_volume_commands_need_a_known_volume(session):
    assert session.drag_volume(0.5) is None
    assert session.toggle_mute() is None


def test_toggle_mute_keeps_the_level(session, clock):
    go_live(session, clock, volume=Volume(0.4, False))

    assert session.toggle_mute() is True
    assert session.volume == Volume(0.4, True)


def test_selected_output_holds_against_stale_readings(session, clock):
    old = AudioOutput("a", "Hoparlör", True)
    new = AudioOutput("b", "Kulaklık", False)
    session.apply(Reading(playing(clock), Volume(0.5, False), old))

    session.select_output(new)
    assert session.output == replace(new, is_default=True)

    session.apply(Reading(playing(clock), Volume(0.5, False), old))
    assert session.output.id == "b"

    clock.now += HOLD_SECONDS + 0.1
    session.apply(Reading(playing(clock), Volume(0.5, False), old))
    assert session.output.id == "a"
