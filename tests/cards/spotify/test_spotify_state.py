from pervaz.cards.spotify.models import NowPlaying, Track
from pervaz.cards.spotify.state import CommandHold, Hold, PendingVolume

TRACK = Track("Şarkı", "Sanatçı", "Albüm")


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def reading(**kwargs):
    return NowPlaying(
        track=TRACK, playing=True, position=0.0, duration=10.0, taken_at=0.0, **kwargs
    )


def test_hold_is_idle_until_started_then_expires():
    clock = Clock()
    hold = Hold(clock, 2.0)
    assert not hold.active
    hold.start()
    assert hold.active
    clock.now += 1.9
    assert hold.active
    clock.now += 0.1
    assert not hold.active


def test_hold_can_be_extended():
    clock = Clock()
    hold = Hold(clock, 2.0)
    hold.start()
    clock.now += 1.5
    hold.start()
    clock.now += 1.5
    assert hold.active


def test_reading_passes_through_without_a_command():
    np = reading()
    assert CommandHold(Clock()).apply(np) is np


def test_command_overrides_reading_until_it_expires():
    clock = Clock()
    hold = CommandHold(clock, 1.0)
    hold.remember(playing=False)
    assert hold.apply(reading()).playing is False
    clock.now += 1.0
    assert hold.apply(reading()).playing is True


def test_commands_inside_the_window_add_up():
    hold = CommandHold(Clock(), 1.0)
    hold.remember(playing=False)
    hold.remember(shuffle=True)
    held = hold.apply(reading())
    assert held.playing is False
    assert held.shuffle is True


def test_expired_command_does_not_leak_into_the_next_one():
    clock = Clock()
    hold = CommandHold(clock, 1.0)
    hold.remember(playing=False)
    clock.now += 2.0
    hold.remember(shuffle=True)
    held = hold.apply(reading())
    assert held.playing is True
    assert held.shuffle is True


def test_pending_volume_keeps_the_latest_level_and_is_taken_once():
    pending = PendingVolume()
    assert pending.take() is None
    pending.update(0.3, False)
    pending.update(0.4, False)
    assert pending.take() == (0.4, False)
    assert pending.take() is None


def test_unmute_request_survives_later_steps_of_the_same_drag():
    pending = PendingVolume()
    pending.update(0.3, True)
    pending.update(0.4, False)  # kart ilk adımda sesi açık göstermeye başladı
    assert pending.take() == (0.4, True)
    pending.update(0.5, False)
    assert pending.take() == (0.5, False)
