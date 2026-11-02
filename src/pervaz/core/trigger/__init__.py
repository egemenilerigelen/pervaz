"""Tetikleyici seçimi. Yeni bir tür eklemek için `TRIGGER_KINDS`'a bir satır yeterli."""

from __future__ import annotations

from pervaz.core.trigger.base import Trigger
from pervaz.core.trigger.handle import HandleTrigger

TRIGGER_KINDS: dict[str, type[Trigger]] = {"handle": HandleTrigger}


def create_trigger(kind: str) -> Trigger:
    return TRIGGER_KINDS.get(kind, HandleTrigger)()


__all__ = ["TRIGGER_KINDS", "HandleTrigger", "Trigger", "create_trigger"]
