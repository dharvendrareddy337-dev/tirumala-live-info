"""Experimental free Panchangam astronomy for Tirumala.

This module is intentionally NOT wired into the production snapshot yet.
It uses Skyfield (MIT) with the public JPL DE421 ephemeris. Values must pass
TTD-calendar comparison before the caller enables them in the live app.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any

IST = ZoneInfo("Asia/Kolkata")
LATITUDE = 13.6833
LONGITUDE = 79.3470
ELEVATION_M = 900
TITHI_NAMES = (
    "Shukla Pratipada", "Shukla Dwitiya", "Shukla Tritiya", "Shukla Chaturthi",
    "Shukla Panchami", "Shukla Shashthi", "Shukla Saptami", "Shukla Ashtami",
    "Shukla Navami", "Shukla Dashami", "Shukla Ekadashi", "Shukla Dwadashi",
    "Shukla Trayodashi", "Shukla Chaturdashi", "Purnima",
    "Krishna Pratipada", "Krishna Dwitiya", "Krishna Tritiya", "Krishna Chaturthi",
    "Krishna Panchami", "Krishna Shashthi", "Krishna Saptami", "Krishna Ashtami",
    "Krishna Navami", "Krishna Dashami", "Krishna Ekadashi", "Krishna Dwadashi",
    "Krishna Trayodashi", "Krishna Chaturdashi", "Amavasya",
)
NAKSHATRA_NAMES = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
)

# Segment number (1-8) for weekday order Monday through Sunday.
RAHU_SEGMENT = (2, 7, 5, 6, 4, 3, 8)
YAMA_SEGMENT = (4, 3, 2, 1, 7, 6, 5)
GULIKA_SEGMENT = (6, 5, 4, 3, 2, 1, 7)


def normalize_degrees(value: float) -> float:
    return value % 360.0


def angular_index(longitude: float, divisions: int) -> int:
    """Return the zero-based equal-arc segment containing a longitude."""
    if divisions <= 0:
        raise ValueError("divisions must be positive")
    return int(normalize_degrees(longitude) / (360.0 / divisions)) % divisions


def tithi_index(moon_longitude: float, sun_longitude: float) -> int:
    """Tithi is based on the geocentric Moon-Sun elongation."""
    return angular_index(moon_longitude - sun_longitude, 30)


def lahiri_ayanamsa_degrees(year: float) -> float:
    """Approximate Lahiri ayanamsa, suitable only for the validation prototype.

    This linear approximation is deliberately marked provisional. It must be
    replaced or calibrated against an authoritative Lahiri implementation
    before the Panchangam is released.
    """
    return 23.8530556 + (year - 2000.0) * (50.290966 / 3600.0)


def weekday_segment(day: int, table: tuple[int, ...]) -> int:
    """Return the traditional 1-8 daytime segment for Python weekday (Mon=0)."""
    return table[day]


def segment_interval(start: datetime, end: datetime, segment: int) -> tuple[datetime, datetime]:
    if end <= start or not 1 <= segment <= 8:
        raise ValueError("invalid day interval or segment")
    duration = (end - start) / 8
    return start + duration * (segment - 1), start + duration * segment


def format_interval(interval: tuple[datetime, datetime] | None) -> str | None:
    if interval is None:
        return None
    return " – ".join(x.astimezone(IST).strftime("%I:%M %p").lstrip("0") for x in interval)


def format_time(value: datetime | None) -> str | None:
    return value.astimezone(IST).strftime("%I:%M %p").lstrip("0") if value else None


def _load_skyfield(ephemeris_path: str | Path):
    try:
        from skyfield.api import load, wgs84
        from skyfield import almanac
    except ImportError as exc:
        raise RuntimeError("Install the free Skyfield dependency to calculate Panchangam.") from exc

    path = Path(ephemeris_path)
    if not path.exists():
        raise FileNotFoundError(f"JPL ephemeris file not found: {path}")
    ts = load.timescale()
    eph = load(str(path))
    location = wgs84.latlon(LATITUDE, LONGITUDE, elevation_m=ELEVATION_M)
    return ts, eph, location, almanac


def calculate_solar_events(day: date, ephemeris_path: str | Path) -> dict[str, datetime | None]:
    """Find Tirumala sunrise, sunset and moonrise for the local civil date."""
    ts, eph, location, almanac = _load_skyfield(ephemeris_path)
    local_start = datetime.combine(day, time.min, tzinfo=IST)
    local_end = local_start + timedelta(days=1)
    t0 = ts.from_datetime(local_start.astimezone(timezone.utc))
    t1 = ts.from_datetime(local_end.astimezone(timezone.utc))

    events: dict[str, datetime | None] = {"sunrise": None, "sunset": None, "moonrise": None}
    f_sun = almanac.sunrise_sunset(eph, location)
    times, states = almanac.find_discrete(t0, t1, f_sun)
    for moment, state in zip(times, states):
        local = moment.utc_datetime().astimezone(IST)
        key = "sunrise" if bool(state) else "sunset"
        if local.date() == day:
            events[key] = local

    f_moon = almanac.risings_and_settings(eph, eph["moon"], location)
    times, states = almanac.find_discrete(t0, t1, f_moon)
    for moment, state in zip(times, states):
        local = moment.utc_datetime().astimezone(IST)
        if bool(state) and local.date() == day:
            events["moonrise"] = local
            break
    return events


def calculate_sidereal_longitudes(moment: datetime, ephemeris_path: str | Path) -> dict[str, float]:
    """Return geocentric apparent sidereal longitudes using provisional Lahiri ayanamsa."""
    ts, eph, _location, _almanac = _load_skyfield(ephemeris_path)
    t = ts.from_datetime(moment.astimezone(timezone.utc))
    earth = eph["earth"]
    sun = earth.at(t).observe(eph["sun"]).apparent()
    moon = earth.at(t).observe(eph["moon"]).apparent()
    sun_lon = sun.ecliptic_latlon(epoch="date")[1].degrees
    moon_lon = moon.ecliptic_latlon(epoch="date")[1].degrees
    ayanamsa = lahiri_ayanamsa_degrees(moment.year + (moment.timetuple().tm_yday - 1) / 365.2425)
    return {
        "sun": normalize_degrees(sun_lon - ayanamsa),
        "moon": normalize_degrees(moon_lon - ayanamsa),
        "elongation": normalize_degrees(moon_lon - sun_lon),
    }


def find_next_angular_transition(
    start: datetime,
    longitude_at,
    divisions: int,
    *,
    max_hours: int = 48,
    step_minutes: int = 10,
    tolerance_seconds: float = 1.0,
) -> datetime | None:
    """Find the next equal-arc segment boundary using a bracket and bisection.

    longitude_at(moment) must return a continuously advancing angular value
    in degrees (it may wrap at 360). This returns the first transition after
    start, to approximately tolerance_seconds.
    """
    if divisions <= 0 or max_hours <= 0 or step_minutes <= 0:
        raise ValueError("divisions, max_hours and step_minutes must be positive")

    current_index = angular_index(longitude_at(start), divisions)
    left = start
    limit = start + timedelta(hours=max_hours)
    step = timedelta(minutes=step_minutes)

    while left < limit:
        right = min(left + step, limit)
        if angular_index(longitude_at(right), divisions) != current_index:
            # Bisection is safe because the bracket is short enough that the
            # angle cannot cross and return to the same segment.
            while (right - left).total_seconds() > tolerance_seconds:
                middle = left + (right - left) / 2
                if angular_index(longitude_at(middle), divisions) == current_index:
                    left = middle
                else:
                    right = middle
            return right
        left = right
    return None


def calculate_transition_times(
    sunrise: datetime,
    ephemeris_path: str | Path,
) -> dict[str, datetime | None]:
    """Calculate next Tithi and Nakshatra boundaries after Tirumala sunrise."""
    def positions(moment: datetime) -> dict[str, float]:
        return calculate_sidereal_longitudes(moment, ephemeris_path)

    at_sunrise = positions(sunrise)
    tithi_end = find_next_angular_transition(
        sunrise,
        lambda moment: positions(moment)["elongation"],
        30,
    )
    nakshatra_end = find_next_angular_transition(
        sunrise,
        lambda moment: positions(moment)["moon"],
        27,
    )
    return {
        "tithiEndAt": tithi_end,
        "nakshatraEndAt": nakshatra_end,
    }


def calculate_day_periods(day: date, sunrise: datetime, sunset: datetime) -> dict[str, str | None]:
    """Calculate sunrise-based weekday and standard eight-part daytime intervals."""
    if sunrise.date() != day or sunset.date() != day or sunset <= sunrise:
        raise ValueError("sunrise and sunset must belong to the requested local date")
    weekday = day.weekday()
    rahu = segment_interval(sunrise, sunset, weekday_segment(weekday, RAHU_SEGMENT))
    yama = segment_interval(sunrise, sunset, weekday_segment(weekday, YAMA_SEGMENT))
    gulika = segment_interval(sunrise, sunset, weekday_segment(weekday, GULIKA_SEGMENT))
    brahma_start = sunrise - timedelta(minutes=96)
    brahma_end = sunrise - timedelta(minutes=48)
    day_duration = sunset - sunrise
    muhurta = day_duration / 15
    abhijit_mid = sunrise + day_duration / 2
    abhijit = (abhijit_mid - muhurta / 2, abhijit_mid + muhurta / 2)
    return {
        "rahuKalam": format_interval(rahu),
        "yamagandam": format_interval(yama),
        "gulikaKalam": format_interval(gulika),
        "brahmaMuhurta": format_interval((brahma_start, brahma_end)),
        "abhijitMuhurta": format_interval(abhijit),
    }


def calculate_daily_base(day: date, ephemeris_path: str | Path) -> dict[str, Any]:
    """Calculate a conservative subset; no unverified auspicious windows are invented."""
    events = calculate_solar_events(day, ephemeris_path)
    sunrise = events["sunrise"]
    sunset = events["sunset"]
    if sunrise is None or sunset is None:
        raise RuntimeError("Could not determine both sunrise and sunset for Tirumala.")
    positions = calculate_sidereal_longitudes(sunrise, ephemeris_path)
    transitions = calculate_transition_times(sunrise, ephemeris_path)
    ti = tithi_index(positions["moon"], positions["sun"])
    ni = angular_index(positions["moon"], 27)
    yi = angular_index(positions["sun"] + positions["moon"], 27)
    periods = calculate_day_periods(day, sunrise, sunset)
    return {
        "date": day.isoformat(),
        "observedAt": datetime.now(IST).isoformat(timespec="seconds"),
        "vara": day.strftime("%A"),
        "tithi": TITHI_NAMES[ti],
        "tithiEnd": format_time(transitions["tithiEndAt"]),
        "tithiEndAt": transitions["tithiEndAt"].isoformat(timespec="seconds") if transitions["tithiEndAt"] else None,
        "nakshatra": NAKSHATRA_NAMES[ni],
        "nakshatraEnd": format_time(transitions["nakshatraEndAt"]),
        "nakshatraEndAt": transitions["nakshatraEndAt"].isoformat(timespec="seconds") if transitions["nakshatraEndAt"] else None,
        "yogaIndex": yi + 1,
        "karana": None,
        "sunrise": format_time(sunrise),
        "sunset": format_time(sunset),
        "moonrise": format_time(events["moonrise"]),
        **periods,
        "amritaKalam": None,
        "varjyam": None,
        "durmuhurtham": None,
        "calculation": {
            "engine": "Skyfield + JPL DE421",
            "ayanamsa": "Lahiri approximation (provisional; not release-validated)",
            "location": {"latitude": LATITUDE, "longitude": LONGITUDE, "elevationM": ELEVATION_M},
            "timezone": "Asia/Kolkata",
        },
    }
