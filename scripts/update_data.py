#!/usr/bin/env python3
"""Fetch public Tirumala information and publish a timestamped snapshot.

Sources are public TTD pages and Open-Meteo. This script does not log in,
submit forms, access booking accounts, bypass CAPTCHA, or read private systems.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

IST = ZoneInfo("Asia/Kolkata")
TTD_CURRENT = "https://tirumala.org/Current_Booking.aspx"
TTD_BREAKING = "https://news.tirumala.org/category/breaking-news/"
TTD_NEWS = "https://news.tirumala.org/"
TTD_ROOM_GUIDE = "https://news.tirumala.org/%E0%B0%A4%E0%B0%BF%E0%B0%B0%E0%B1%81%E0%B0%AE%E0%B0%B2%E0%B0%B2%E0%B1%8B-%E0%B0%AD%E0%B0%95%E0%B1%8D%E0%B0%A4%E0%B1%81%E0%B0%B2%E0%B0%95%E0%B1%81-%E0%B0%89%E0%B0%AA-%E0%B0%B5%E0%B0%BF%E0%B0%9A/"
TTD_LOCKER_GUIDE = "https://news.tirumala.org/%E0%B0%AD%E0%B0%95%E0%B1%8D%E0%B0%A4%E0%B1%81%E0%B0%B2-%E0%B0%B2%E0%B0%97%E0%B1%87%E0%B0%9C%E0%B1%80-%E0%B0%AD%E0%B0%A6%E0%B1%8D%E0%B0%B0%E0%B0%A4%E0%B0%95%E0%B1%81-%E0%B0%9F%E0%B1%80%E0%B0%9F/"
ROOM_FALLBACK = "https://news.tirumala.org/"
LOCKER_FALLBACK = "https://news.tirumala.org/"
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=13.6833&longitude=79.3470"
    "&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
    "&timezone=Asia%2FKolkata"
)
USER_AGENT = "TirumalaLiveInfo/1.0 (+https://github.com/; public information checker; 15-minute interval)"


def now_ist() -> datetime:
    return datetime.now(IST)


def iso_now() -> str:
    return now_ist().isoformat(timespec="seconds")


def normalized_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "noscript", "svg"]):
        node.decompose()
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).replace("\xa0", " ").strip()


def fetch(url: str, timeout: int = 25) -> tuple[str | None, str | None]:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"},
            timeout=timeout,
        )
        response.raise_for_status()
        if len(response.content) > 8_000_000:
            return None, "Source response exceeded the 8 MB safety limit."
        return response.text, None
    except requests.RequestException as exc:
        return None, f"Fetch failed: {type(exc).__name__}: {exc}"


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return value


def parse_ttd_current_booking(html: str) -> dict[str, Any]:
    text = normalized_text(html)
    slot = re.search(r"Running\s+Slot\s*:\s*(\d+)\s+on\s+(\d{1,2}-[A-Za-z]{3}-\d{4})", text, re.I)
    balance = re.search(r"Balance\s+tickets\s+for\s+(\d{1,2}-[A-Za-z]{3}-\d{4})\s*:\s*([\d,]+)", text, re.I)
    out: dict[str, Any] = {"sourceUrl": TTD_CURRENT, "observedAt": iso_now()}
    if slot:
        out["runningSlot"] = int(slot.group(1))
        out["date"] = parse_date(slot.group(2))
    if balance:
        out["balanceTickets"] = int(balance.group(2).replace(",", ""))
        out.setdefault("date", parse_date(balance.group(1)))
    if not slot and not balance:
        raise ValueError("TTD current-booking page fetched, but the expected Running Slot / Balance tickets text was not found.")
    out["note"] = "TTD states that live ticket status can change before a pilgrim reaches the physical counter; tickets are issued first-come-first-served."
    return out


def parse_breaking_news(html: str) -> dict[str, Any]:
    text = normalized_text(html)
    out: dict[str, Any] = {"sourceUrl": TTD_BREAKING, "observedAt": iso_now()}

    # The latest TTD Breaking News post includes the previous day's footfall and
    # a separately dated current queue status. Accept known TTD spelling variants.
    footfall = re.search(
        r"Total\s+pilgrims\s+who\s+had\s+darshan\s+on\s+(\d{1,2}[./-]\d{1,2}[./-]\d{4})\s*:\s*([\d,]+)",
        text,
        re.I,
    )
    if footfall:
        out["pilgrimsYesterday"] = int(footfall.group(2).replace(",", ""))
        out["pilgrimsDate"] = parse_date(footfall.group(1))

    present = re.search(
        r"Present\s+Situation\s+on\s+(\d{1,2}[./-]\d{1,2}[./-]\d{4})\s*:\s*Waiting\s+compartments?\s*(.*?)\s*Approx\.?\s*Dar(?:s|sh)an\s*time\s*for\s*Sarvadarshanam\s*\(\s*with\s*out\s*SSD\s*Tokens?\s*\)\s*[.…:]*\s*([0-9]+(?:\s*[-–]\s*[0-9]+)?\s*H(?:r|rs|our|ours)?\.?)",
        text,
        re.I,
    )
    if present:
        queue_raw = present.group(2).strip(" .,:;…-–")
        wait_raw = re.sub(r"\s+", "", present.group(3)).upper().rstrip(".")
        out["reportedFor"] = parse_date(present.group(1))
        out["approxWaitText"] = wait_raw
        out["queuePosition"] = queue_raw or "Not specified in the latest TTD post"
        numeric_compartments = re.search(r"(?:^|\D)(\d{1,3})(?:\D|$)", queue_raw)
        if numeric_compartments and not re.search(r"outside|line|silathoranam|guest house|krishna teja", queue_raw, re.I):
            out["waitingCompartments"] = int(numeric_compartments.group(1))
            out["waitingCompartmentsText"] = str(out["waitingCompartments"])
        else:
            out["waitingCompartments"] = None
            out["waitingCompartmentsText"] = queue_raw or "Not numerically reported"
    else:
        # If a status text was published without the full pattern, do not invent it.
        wait_only = re.search(
            r"Approx\.?\s*Dar(?:s|sh)an\s*time\s*for\s*Sarvadarshanam\s*\(\s*with\s*out\s*SSD\s*Tokens?\s*\)\s*[.…:]*\s*([0-9]+(?:\s*[-–]\s*[0-9]+)?\s*H(?:r|rs|our|ours)?\.?)",
            text,
            re.I,
        )
        if wait_only:
            out["approxWaitText"] = re.sub(r"\s+", "", wait_only.group(1)).upper().rstrip(".")

    if not any(k in out for k in ("approxWaitText", "pilgrimsYesterday")):
        raise ValueError("TTD Breaking News page fetched, but no recognised current darshan or daily footfall fields were found.")
    return out


def extract_news(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    containers = soup.find_all("article")
    if not containers:
        containers = soup.select(".post, .type-post")

    for container in containers:
        heading = container.find(["h1", "h2", "h3"])
        if not heading:
            continue
        anchor = heading.find("a", href=True) or container.find("a", href=True)
        if not anchor:
            continue
        title = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True)).strip()
        url = anchor.get("href", "").strip()
        if not title or not url.startswith("https://news.tirumala.org/") or url in seen:
            continue
        seen.add(url)
        time_el = container.find("time")
        date_value = time_el.get("datetime", "")[:10] if time_el and time_el.get("datetime") else ""
        if not date_value and time_el:
            date_match = re.search(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b", time_el.get_text(" ", strip=True))
            if date_match:
                try:
                    date_value = datetime.strptime(date_match.group(0), "%B %d, %Y").date().isoformat()
                except ValueError:
                    pass
        excerpt_el = container.select_one(".entry-content, .entry-summary, .post-excerpt, .excerpt")
        summary = excerpt_el.get_text(" ", strip=True) if excerpt_el else ""
        summary = re.sub(r"\s+", " ", summary)[:360]
        items.append({"title": title[:180], "url": url, "date": date_value, "summary": summary})
        if len(items) >= 12:
            break

    # Fallback for markup without article nodes.
    if not items:
        for heading in soup.find_all(["h2", "h3"]):
            anchor = heading.find("a", href=True)
            if not anchor:
                continue
            title, url = anchor.get_text(" ", strip=True), anchor.get("href", "")
            if title and url.startswith("https://news.tirumala.org/") and url not in seen:
                seen.add(url)
                items.append({"title": title[:180], "url": url, "date": "", "summary": ""})
            if len(items) >= 12:
                break
    return items


def parse_weather(payload: dict[str, Any]) -> dict[str, Any]:
    current = payload.get("current") or {}
    code = current.get("weather_code")
    descriptions = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Drizzle",
        55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Rain showers",
        81: "Moderate rain showers", 82: "Violent rain showers", 95: "Thunderstorm",
        96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
    }
    return {
        "place": "Tirumala",
        "temperatureC": current.get("temperature_2m"),
        "feelsLikeC": current.get("apparent_temperature"),
        "humidityPercent": current.get("relative_humidity_2m"),
        "precipitationMm": current.get("precipitation"),
        "windKmh": current.get("wind_speed_10m"),
        "weatherCode": code,
        "condition": descriptions.get(code, "Current conditions"),
        "observedAt": current.get("time") or iso_now(),
        "sourceUrl": "https://open-meteo.com/",
    }


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def merge_missing_fields(target: dict[str, Any], defaults: dict[str, Any]) -> None:
    """Fill absent keys without overwriting existing values, including nulls."""
    for key, default_value in defaults.items():
        if key not in target:
            target[key] = deepcopy(default_value)
        elif isinstance(target[key], dict) and isinstance(default_value, dict):
            merge_missing_fields(target[key], default_value)


def merge_v6_sections(
    payload: dict[str, Any],
    seed_payload: dict[str, Any],
) -> None:
    """Add V6 reference sections while preserving existing snapshot data."""
    for section in ("statistics", "weeklyStats", "panchang", "rooms", "lockers"):
        seed_section = seed_payload.get(section)
        if not isinstance(seed_section, dict):
            continue

        current_section = payload.get(section)
        if not isinstance(current_section, dict):
            payload[section] = deepcopy(seed_section)
        else:
            merge_missing_fields(current_section, seed_section)

    payload["schemaVersion"] = max(
        int(payload.get("schemaVersion", 1)),
        int(seed_payload.get("schemaVersion", 1)),
    )


def source_status(
    name: str,
    ok: bool,
    url: str,
    previous_sources: dict[str, Any],
    note: str | None = None,
) -> dict[str, Any]:
    """Record this check while retaining the last known successful check time."""
    checked_at = iso_now()
    old = previous_sources.get(name) if isinstance(previous_sources, dict) else None
    old = old if isinstance(old, dict) else {}
    last_success = checked_at if ok else old.get("lastSuccessfulAt") or (old.get("checkedAt") if old.get("ok") else None)
    record: dict[str, Any] = {
        "ok": ok,
        "url": url,
        "checkedAt": checked_at,
        "lastSuccessfulAt": last_success,
    }
    if note:
        record["note"] = note[:500]
    return record


def get_supabase_headers(key: str) -> dict[str, str]:
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def get_previous_supabase(url: str, key: str) -> dict[str, Any] | None:
    endpoint = url.rstrip("/") + "/rest/v1/live_snapshots?select=payload&id=eq.latest"
    response = requests.get(endpoint, headers=get_supabase_headers(key), timeout=20)
    response.raise_for_status()
    rows = response.json()
    return rows[0].get("payload") if rows else None


def publish_supabase(url: str, key: str, payload: dict[str, Any]) -> None:
    endpoint = url.rstrip("/") + "/rest/v1/live_snapshots?on_conflict=id"
    headers = get_supabase_headers(key)
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    response = requests.post(endpoint, headers=headers, json={"id": "latest", "payload": payload, "updated_at": iso_now()}, timeout=20)
    response.raise_for_status()


def changed_alerts(old: dict[str, Any] | None, new: dict[str, Any]) -> list[str]:
    if not old:
        return []
    alerts: list[str] = []
    old_d, new_d = old.get("darshan", {}), new.get("darshan", {})
    if new_d.get("approxWaitText") and new_d.get("approxWaitText") != old_d.get("approxWaitText"):
        alerts.append(f"Sarva Darshan waiting estimate updated: {new_d['approxWaitText']} (without SSD tokens).")
    if new_d.get("queuePosition") and new_d.get("queuePosition") != old_d.get("queuePosition"):
        alerts.append(f"Queue location update: {new_d['queuePosition']}.")
    old_s, new_s = old.get("ssd", {}), new.get("ssd", {})
    if new_s.get("balanceTickets") is not None and new_s.get("balanceTickets") != old_s.get("balanceTickets"):
        alerts.append(f"SSD balance tickets changed: {new_s['balanceTickets']} for {new_s.get('date', 'the displayed date')}.")
    if new_s.get("runningSlot") is not None and (new_s.get("runningSlot"), new_s.get("date")) != (old_s.get("runningSlot"), old_s.get("date")):
        alerts.append(f"SSD running slot update: slot {new_s['runningSlot']} for {new_s.get('date', 'the displayed date')}.")
    if new_d.get("pilgrimsYesterday") is not None and new_d.get("pilgrimsYesterday") != old_d.get("pilgrimsYesterday"):
        alerts.append(f"TTD daily pilgrim count updated: {new_d['pilgrimsYesterday']:,} for {new_d.get('pilgrimsDate', 'the reported date')}.")
    # Notify once when a source changes state; do not repeatedly alert while it stays down.
    old_sources, new_sources = old.get("sources", {}), new.get("sources", {})
    for key, label in (("ttdCurrentBooking", "TTD Current Booking"), ("ttdBreakingNews", "TTD Breaking News"), ("ttdNews", "TTD News"), ("weather", "Tirumala weather")):
        was_ok = (old_sources.get(key) or {}).get("ok")
        is_ok = (new_sources.get(key) or {}).get("ok")
        if was_ok is True and is_ok is False:
            alerts.append(f"{label} source is temporarily unavailable; the app is keeping the last successful data.")
        elif was_ok is False and is_ok is True:
            alerts.append(f"{label} source has recovered and is updating again.")
    old_news = {item.get("url") for item in old.get("news", []) if item.get("url")}
    for item in new.get("news", []):
        if item.get("url") and item["url"] not in old_news:
            alerts.append("New TTD announcement: " + item.get("title", "Official update"))
            if len(alerts) >= 4:
                break
    old_w, new_w = old.get("weather"), new.get("weather")
    if isinstance(old_w, dict) and isinstance(new_w, dict):
        old_code, new_code = old_w.get("weatherCode"), new_w.get("weatherCode")
        if new_code != old_code and new_w.get("condition"):
            alerts.append(f"Tirumala weather update: {new_w['condition']}.")
        old_temp, new_temp = old_w.get("temperatureC"), new_w.get("temperatureC")
        try:
            if old_temp is not None and new_temp is not None and abs(float(new_temp) - float(old_temp)) >= 4:
                alerts.append(f"Tirumala temperature changed to {new_temp}°C.")
        except (TypeError, ValueError):
            pass
    return alerts[:6]


def send_fcm_notifications(service_account_json: str, supabase_url: str, supabase_key: str, messages: list[str]) -> int:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request

    info = json.loads(service_account_json)
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/firebase.messaging"]
    )
    credentials.refresh(Request())
    project_id = info.get("project_id")
    if not project_id:
        raise ValueError("Firebase service-account JSON is missing project_id.")

    endpoint = supabase_url.rstrip("/") + "/rest/v1/push_subscriptions?select=id,fcm_token"
    response = requests.get(endpoint, headers=get_supabase_headers(supabase_key), timeout=20)
    response.raise_for_status()
    subscriptions = response.json()
    if not subscriptions:
        print("No devices have enabled push notifications yet.")
        return 0

    body = "\n".join(f"• {m}" for m in messages[:3])
    if len(messages) > 3:
        body += f"\n• +{len(messages) - 3} more update(s)"
    fcm_url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    app_url = os.getenv("PUBLIC_APP_URL", "").strip()
    sent = 0
    for sub in subscriptions:
        token = sub.get("fcm_token")
        if not token:
            continue
        message: dict[str, Any] = {
            "token": token,
            "notification": {"title": "Tirumala Live Info · New updates", "body": body[:950]},
        }
        if app_url.startswith("https://"):
            message["webpush"] = {"fcm_options": {"link": app_url}}
        data = {"message": message}
        r = requests.post(fcm_url, headers={"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}, json=data, timeout=20)
        if r.ok:
            sent += 1
        elif r.status_code in (400, 404) and any(term in r.text for term in ("UNREGISTERED", "registration-token-not-registered", "INVALID_ARGUMENT")):
            # Purge expired/invalid device token from the private registry.
            delete_url = supabase_url.rstrip("/") + "/rest/v1/push_subscriptions?fcm_token=eq." + quote(token, safe="")
            requests.delete(delete_url, headers=get_supabase_headers(supabase_key), timeout=15)
        else:
            print(f"FCM send failed ({r.status_code}): {r.text[:250]}", file=sys.stderr)
    return sent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/live.json", help="Write a local snapshot JSON file")
    args = parser.parse_args()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    previous_file = load_json_file(out_path)

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    previous_db = None
    if supabase_url and supabase_key:
        try:
            previous_db = get_previous_supabase(supabase_url, supabase_key)
        except Exception as exc:
            print(f"Supabase previous snapshot could not be read: {exc}", file=sys.stderr)

    # Prefer the remote latest snapshot over the checked-in seed file. GitHub
    # checks out the seed on every run, whereas Supabase holds the prior run.
    previous = previous_db or previous_file or None
    payload: dict[str, Any] = deepcopy(previous_db or previous_file or {})

    # Merge V6 reference sections into older snapshots without replacing
    # existing live values. The checked-in V6 seed must be deployed with this code.
    seed_path = Path(__file__).resolve().parents[1] / "data" / "live.json"
    seed_payload = load_json_file(seed_path)
    merge_v6_sections(payload, seed_payload)
    previous_sources = payload.get("sources", {}) if isinstance(payload.get("sources"), dict) else {}
    if payload.get("isReferenceSnapshot"):
        # Seed snapshots are dated examples, not successful automatic checks.
        previous_sources = {}
    payload.setdefault("schemaVersion", 1)
    payload.setdefault("darshan", {})
    payload.setdefault("ssd", {})
    payload.setdefault("rooms", {
        "availability": None,
        "availabilityStatus": "not_published_as_public_live_feed",
        "publishedGuidance": "Current room vacancy counts are displayed on TTD counter boards, not through a public live inventory feed.",
        "sourceUrl": "https://www.tirumala.org/Downloads/MoreFaqs.pdf",
    })
    payload.setdefault("lockers", {
        "availability": None,
        "availabilityStatus": "not_published_as_public_live_feed",
        "locations": [],
        "sourceUrl": TTD_LOCKER_GUIDE,
    })
    payload.setdefault("news", [])
    payload.setdefault("sources", {})

    source_records: dict[str, dict[str, Any]] = {}

    # Official TTD current booking page: SSD running slot and balance tickets.
    html, error = fetch(TTD_CURRENT)
    if html:
        try:
            payload["ssd"].update(parse_ttd_current_booking(html))
            source_records["ttdCurrentBooking"] = source_status("ttdCurrentBooking", True, TTD_CURRENT, previous_sources)
        except Exception as exc:
            source_records["ttdCurrentBooking"] = source_status("ttdCurrentBooking", False, TTD_CURRENT, previous_sources, str(exc))
    else:
        source_records["ttdCurrentBooking"] = source_status("ttdCurrentBooking", False, TTD_CURRENT, previous_sources, error)

    # TTD Breaking News: official queue location, approximate no-SSD wait, daily footfall.
    html, error = fetch(TTD_BREAKING)
    if html:
        try:
            parsed = parse_breaking_news(html)
            for field in ("approxWaitText", "queuePosition", "waitingCompartments", "waitingCompartmentsText", "reportedFor", "pilgrimsYesterday", "pilgrimsDate"):
                if field in parsed:
                    payload["darshan"][field] = parsed[field]
            payload["darshan"]["sourceUrl"] = TTD_BREAKING
            payload["darshan"]["observedAt"] = parsed["observedAt"]
            source_records["ttdBreakingNews"] = source_status("ttdBreakingNews", True, TTD_BREAKING, previous_sources)
        except Exception as exc:
            source_records["ttdBreakingNews"] = source_status("ttdBreakingNews", False, TTD_BREAKING, previous_sources, str(exc))
    else:
        source_records["ttdBreakingNews"] = source_status("ttdBreakingNews", False, TTD_BREAKING, previous_sources, error)

    # TTD News homepage: new official notices. Keep only links on the official news domain.
    html, error = fetch(TTD_NEWS)
    if html:
        news = extract_news(html)
        if news:
            payload["news"] = news
            source_records["ttdNews"] = source_status("ttdNews", True, TTD_NEWS, previous_sources)
        else:
            source_records["ttdNews"] = source_status("ttdNews", False, TTD_NEWS, previous_sources, "No official article cards were recognised; previous news list retained.")
    else:
        source_records["ttdNews"] = source_status("ttdNews", False, TTD_NEWS, previous_sources, error)

    # Weather has no key requirement; coordinates are for Tirumala.
    try:
        response = requests.get(WEATHER_URL, headers={"User-Agent": USER_AGENT}, timeout=20)
        response.raise_for_status()
        payload["weather"] = parse_weather(response.json())
        source_records["weather"] = source_status("weather", True, "https://open-meteo.com/", previous_sources)
    except Exception as exc:
        source_records["weather"] = source_status("weather", False, "https://open-meteo.com/", previous_sources, f"Weather fetch failed: {type(exc).__name__}: {exc}")

    any_source_ok = any(record.get("ok") for record in source_records.values())
    payload["lastCheckedAt"] = iso_now()
    payload["isReferenceSnapshot"] = bool(previous.get("isReferenceSnapshot", False)) and not any_source_ok if previous else not any_source_ok
    payload["isStale"] = not any_source_ok and not payload["isReferenceSnapshot"]
    payload["sources"] = source_records
    payload["disclaimer"] = (
        "Independent information service. Darshan estimates reflect the latest TTD-published report and are not guarantees. "
        "TTD does not expose room or locker vacancy counts in the public pages used by this updater. "
        "Always confirm critical decisions through official TTD channels."
    )
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote snapshot: {out_path} ({out_path.stat().st_size} bytes)")

    if supabase_url and supabase_key:
        try:
            publish_supabase(supabase_url, supabase_key, payload)
            print("Published latest snapshot to Supabase.")
        except Exception as exc:
            print(f"ERROR: Could not publish snapshot to Supabase: {exc}", file=sys.stderr)
            return 2
    else:
        print("Supabase secrets are not configured; this run only wrote the local JSON snapshot.")

    firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if supabase_url and supabase_key and firebase_json:
        alerts = changed_alerts(previous, payload)
        if alerts:
            try:
                sent = send_fcm_notifications(firebase_json, supabase_url, supabase_key, alerts)
                print(f"Sent update alert to {sent} device(s).")
            except Exception as exc:
                print(f"Push notifications were not sent: {exc}", file=sys.stderr)
        else:
            print("No material change detected; no push alert sent.")
    elif not firebase_json:
        print("Firebase service-account secret is not configured; push delivery is disabled until configured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
