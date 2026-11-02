"""Hava durumunun veri modelleri: konum, günlük tahmin ve anlık durum."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class Place:
    query: str  # kullanıcının yazdığı ad; önbellek geçerliliği için
    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class DayForecast:
    day: date
    temp_min: float
    temp_max: float
    code: int


@dataclass(frozen=True)
class Weather:
    place: str
    temperature: float
    apparent: float
    humidity: int
    wind_kmh: float
    precipitation_mm: float
    code: int
    days: tuple[DayForecast, ...]
    fetched_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "place": self.place,
            "temperature": self.temperature,
            "apparent": self.apparent,
            "humidity": self.humidity,
            "wind_kmh": self.wind_kmh,
            "precipitation_mm": self.precipitation_mm,
            "code": self.code,
            "fetched_at": self.fetched_at.isoformat(),
            "days": [
                {"day": d.day.isoformat(), "min": d.temp_min, "max": d.temp_max, "code": d.code}
                for d in self.days
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Weather:
        return cls(
            place=data["place"],
            temperature=float(data["temperature"]),
            apparent=float(data["apparent"]),
            humidity=int(data["humidity"]),
            wind_kmh=float(data["wind_kmh"]),
            precipitation_mm=float(data["precipitation_mm"]),
            code=int(data["code"]),
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            days=tuple(
                DayForecast(
                    day=date.fromisoformat(d["day"]),
                    temp_min=float(d["min"]),
                    temp_max=float(d["max"]),
                    code=int(d["code"]),
                )
                for d in data["days"]
            ),
        )
