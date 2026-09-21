#!/usr/bin/env python3
"""Maintain the repository's structured travel library."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PREFERENCES = ROOT / "data" / "preferences.json"
TRIPS = ROOT / "trips"
OUTPUT = ROOT / "assets" / "library-data.js"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TRIP_STATUSES = {"planned", "recorded", "idea"}
PREFERENCE_STATUSES = {"confirmed", "context", "inferred", "wishlist"}
ENTRY_TYPES = {"observation", "reflection", "note"}
LINK_KINDS = {"plan", "review", "notes"}


class TravelError(Exception):
    pass


def read_json(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise TravelError(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise TravelError(
            f"invalid JSON in {path.relative_to(ROOT)}: line {exc.lineno}, column {exc.colno}"
        ) from exc


def expect_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TravelError(f"{label} must be an object")
    return value


def expect_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise TravelError(f"{label} must be an array")
    return value


def expect_string(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise TravelError(f"{label} must be a non-empty string")
    return value


def parse_date(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    text = expect_string(value, label)
    try:
        parsed = dt.date.fromisoformat(text)
    except ValueError as exc:
        raise TravelError(f"{label} must be a valid YYYY-MM-DD date") from exc
    if parsed.isoformat() != text:
        raise TravelError(f"{label} must be a valid YYYY-MM-DD date")
    return text


def validate_slug(slug: str) -> str:
    if not SLUG_RE.fullmatch(slug):
        raise TravelError("slug must contain only lowercase letters, digits, and single hyphens")
    return slug


def ensure_keys(obj: dict[str, Any], required: set[str], label: str) -> None:
    missing = sorted(required - obj.keys())
    if missing:
        raise TravelError(f"{label} is missing: {', '.join(missing)}")


def resolve_local_path(raw_path: Any, label: str) -> Path:
    text = expect_string(raw_path, label)
    base, _, fragment = text.partition("#")
    if (
        not base
        or "\\" in base
        or "?" in base
        or any(ord(char) < 32 or ord(char) == 127 for char in text)
        or urlsplit(base).scheme
    ):
        raise TravelError(f"{label} must be a safe repository-relative path")
    try:
        decoded = unquote(base, errors="strict")
    except UnicodeError as exc:
        raise TravelError(f"{label} must be a safe repository-relative path") from exc
    if (
        "\\" in decoded
        or "?" in decoded
        or urlsplit(decoded).scheme
        or any(ord(char) < 32 or ord(char) == 127 for char in decoded)
    ):
        raise TravelError(f"{label} must be a safe repository-relative path")
    pure = PurePosixPath(decoded)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise TravelError(f"{label} must be a safe repository-relative path")
    if fragment and any(char.isspace() for char in fragment):
        raise TravelError(f"{label} has an invalid fragment")
    root = ROOT.resolve()
    target = ROOT.joinpath(*pure.parts).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise TravelError(f"{label} must stay inside the repository") from exc
    if not target.exists():
        raise TravelError(f"{label} does not exist: {decoded}")
    return target


def validate_source(source: Any, label: str) -> None:
    source = expect_object(source, label)
    expect_string(source.get("label"), f"{label}.label")
    if "path" in source:
        resolve_local_path(source["path"], f"{label}.path")
    if "tripId" in source:
        trip_id = expect_string(source["tripId"], f"{label}.tripId")
        validate_slug(trip_id)
        if not (TRIPS / trip_id / "trip.json").exists():
            raise TravelError(f"{label}.tripId does not exist: {trip_id}")


def validate_preferences(preferences: Any) -> dict[str, Any]:
    preferences = expect_object(preferences, "preferences.json")
    ensure_keys(preferences, {"updatedAt", "items"}, "preferences.json")
    parse_date(preferences["updatedAt"], "preferences.updatedAt")
    seen: set[str] = set()
    for index, item in enumerate(expect_list(preferences["items"], "preferences.items")):
        label = f"preferences.items[{index}]"
        item = expect_object(item, label)
        ensure_keys(item, {"id", "category", "label", "detail", "status", "source"}, label)
        item_id = expect_string(item["id"], f"{label}.id")
        if item_id in seen:
            raise TravelError(f"duplicate preference id: {item_id}")
        seen.add(item_id)
        expect_string(item["category"], f"{label}.category")
        expect_string(item["label"], f"{label}.label")
        expect_string(item["detail"], f"{label}.detail")
        if item["status"] not in PREFERENCE_STATUSES:
            raise TravelError(f"{label}.status must be one of {sorted(PREFERENCE_STATUSES)}")
        validate_source(item["source"], f"{label}.source")
    return preferences


def validate_trip(slug: str, trip: Any, journal: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    trip = expect_object(trip, f"trips/{slug}/trip.json")
    required = {
        "id", "title", "status", "dateLabel", "startDate", "endDate", "dateNote",
        "summary", "tags", "route", "highlights", "links", "updatedAt",
    }
    ensure_keys(trip, required, f"trips/{slug}/trip.json")
    if trip["id"] != slug:
        raise TravelError(f"trip id {trip.get('id')!r} does not match directory {slug!r}")
    validate_slug(slug)
    expect_string(trip["title"], f"trip {slug}.title")
    if trip["status"] not in TRIP_STATUSES:
        raise TravelError(f"trip {slug}.status must be one of {sorted(TRIP_STATUSES)}")
    for field in ("dateLabel", "dateNote", "summary"):
        expect_string(trip[field], f"trip {slug}.{field}", allow_empty=True)
    start = parse_date(trip["startDate"], f"trip {slug}.startDate", nullable=True)
    end = parse_date(trip["endDate"], f"trip {slug}.endDate", nullable=True)
    if (start is None) != (end is None):
        raise TravelError(f"trip {slug} must set both startDate and endDate, or neither")
    if start and end and start > end:
        raise TravelError(f"trip {slug} startDate must not be after endDate")
    parse_date(trip["updatedAt"], f"trip {slug}.updatedAt")
    for field in ("tags", "route", "highlights"):
        values = expect_list(trip[field], f"trip {slug}.{field}")
        for index, value in enumerate(values):
            expect_string(value, f"trip {slug}.{field}[{index}]")
    for index, link in enumerate(expect_list(trip["links"], f"trip {slug}.links")):
        label = f"trip {slug}.links[{index}]"
        link = expect_object(link, label)
        ensure_keys(link, {"label", "path", "kind"}, label)
        expect_string(link["label"], f"{label}.label")
        if link["kind"] not in LINK_KINDS:
            raise TravelError(f"{label}.kind must be one of {sorted(LINK_KINDS)}")
        resolve_local_path(link["path"], f"{label}.path")

    journal = expect_object(journal, f"trips/{slug}/journal.json")
    ensure_keys(journal, {"entries"}, f"trips/{slug}/journal.json")
    entries = expect_list(journal["entries"], f"trip {slug}.journal.entries")
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"trip {slug}.journal.entries[{index}]"
        entry = expect_object(entry, label)
        ensure_keys(entry, {"id", "date", "title", "text", "type", "source", "media"}, label)
        entry_id = expect_string(entry["id"], f"{label}.id")
        if entry_id in seen:
            raise TravelError(f"duplicate journal entry id in {slug}: {entry_id}")
        seen.add(entry_id)
        parse_date(entry["date"], f"{label}.date", nullable=True)
        expect_string(entry["title"], f"{label}.title")
        expect_string(entry["text"], f"{label}.text")
        if entry["type"] not in ENTRY_TYPES:
            raise TravelError(f"{label}.type must be one of {sorted(ENTRY_TYPES)}")
        validate_source(entry["source"], f"{label}.source")
        expect_list(entry["media"], f"{label}.media")
    return trip, entries


def load_library() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    preferences = validate_preferences(read_json(PREFERENCES))
    if not TRIPS.exists():
        raise TravelError("missing directory: trips")
    trips: list[dict[str, Any]] = []
    for directory in sorted(path for path in TRIPS.iterdir() if path.is_dir()):
        slug = directory.name
        validate_slug(slug)
        trip, entries = validate_trip(
            slug,
            read_json(directory / "trip.json"),
            read_json(directory / "journal.json"),
        )
        built = dict(trip)
        built["journal"] = entries
        trips.append(built)
    return preferences, trips


def library_updated_at(preferences: dict[str, Any], trips: list[dict[str, Any]]) -> str:
    dates = [preferences["updatedAt"]]
    dates.extend(trip["updatedAt"] for trip in trips)
    return max(dates)


def javascript_json(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        text.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def build() -> None:
    preferences, trips = load_library()
    payload = {
        "updatedAt": library_updated_at(preferences, trips),
        "preferences": preferences,
        "trips": trips,
    }
    atomic_write(OUTPUT, f"window.travelLibrary = {javascript_json(payload)};\n")


def check() -> None:
    load_library()


def default_date_label(start: str | None, end: str | None) -> str:
    if not start:
        return "日期待定"
    return start if start == end else f"{start} — {end}"


def write_new_trip(slug: str, title: str, start: str | None, end: str | None) -> None:
    validate_slug(slug)
    title = expect_string(title, "title")
    if (start is None) != (end is None):
        raise TravelError("--start and --end must be provided together")
    start = parse_date(start, "--start", nullable=True)
    end = parse_date(end, "--end", nullable=True)
    if start and end and start > end:
        raise TravelError("--start must not be after --end")
    destination = TRIPS / slug
    if destination.exists():
        raise TravelError(f"trip already exists: {slug}")

    load_library()
    updated = dt.date.today().isoformat()
    trip = {
        "id": slug,
        "title": title,
        "status": "planned" if start else "idea",
        "dateLabel": default_date_label(start, end),
        "startDate": start,
        "endDate": end,
        "dateNote": "",
        "summary": "",
        "tags": [],
        "route": [],
        "highlights": [],
        "links": [
            {"label": "行程计划", "path": f"trips/{slug}/plan.md", "kind": "plan"},
            {"label": "旅行复盘", "path": f"trips/{slug}/review.md", "kind": "review"},
        ],
        "updatedAt": updated,
    }
    journal = {"entries": []}
    destination.mkdir(parents=True)
    created: list[Path] = []
    try:
        files = {
            destination / "trip.json": json.dumps(trip, ensure_ascii=False, indent=2) + "\n",
            destination / "journal.json": json.dumps(journal, ensure_ascii=False, indent=2) + "\n",
            destination / "plan.md": (
                f"# {title} · 行程计划\n\n"
                "## 目标与同行人\n\n待补充。\n\n"
                "## 路线与每日安排\n\n待补充。\n\n"
                "## 住宿与交通\n\n待补充。\n\n"
                "## 预约与出发准备\n\n待补充。\n"
            ),
            destination / "review.md": (
                f"# {title} · 旅行复盘\n\n"
                "## 实际路线\n\n待旅行后补充。\n\n"
                "## 最值得的体验\n\n待旅行后补充。\n\n"
                "## 避坑与调整\n\n待旅行后补充。\n\n"
                "## 下次会怎么走\n\n待旅行后补充。\n"
            ),
        }
        for path, content in files.items():
            atomic_write(path, content)
            created.append(path)
        build()
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        try:
            destination.rmdir()
        except OSError:
            pass
        raise


def next_entry_id(entries: list[dict[str, Any]], date: str) -> str:
    prefix = f"note-{date}"
    used = {entry["id"] for entry in entries}
    if prefix not in used:
        return prefix
    counter = 2
    while f"{prefix}-{counter}" in used:
        counter += 1
    return f"{prefix}-{counter}"


def add_note(slug: str, date: str, title: str, text: str) -> None:
    validate_slug(slug)
    date = parse_date(date, "--date")  # type: ignore[assignment]
    title = expect_string(title, "--title")
    text = expect_string(text, "--text")
    load_library()
    directory = TRIPS / slug
    if not directory.is_dir():
        raise TravelError(f"unknown trip: {slug}")
    trip_path = directory / "trip.json"
    journal_path = directory / "journal.json"
    trip, entries = validate_trip(slug, read_json(trip_path), read_json(journal_path))
    updated_entries = list(entries)
    updated_entries.append({
        "id": next_entry_id(entries, date),
        "date": date,
        "title": title,
        "text": text,
        "type": "note",
        "source": {"label": "用户新增记录"},
        "media": [],
    })
    updated_trip = dict(trip)
    updated_trip["updatedAt"] = dt.date.today().isoformat()
    validate_trip(slug, updated_trip, {"entries": updated_entries})
    original_trip = trip_path.read_text(encoding="utf-8")
    original_journal = journal_path.read_text(encoding="utf-8")
    try:
        atomic_write(trip_path, json.dumps(updated_trip, ensure_ascii=False, indent=2) + "\n")
        atomic_write(journal_path, json.dumps({"entries": updated_entries}, ensure_ascii=False, indent=2) + "\n")
        build()
    except Exception:
        atomic_write(trip_path, original_trip)
        atomic_write(journal_path, original_journal)
        raise


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    sub = command.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="validate data and regenerate assets/library-data.js")
    sub.add_parser("check", help="validate preferences and trip archives")
    new = sub.add_parser("new", help="create a new trip archive")
    new.add_argument("slug")
    new.add_argument("--title", required=True)
    new.add_argument("--start")
    new.add_argument("--end")
    note = sub.add_parser("note", help="append a user-provided travel note")
    note.add_argument("slug")
    note.add_argument("--date", required=True)
    note.add_argument("--title", required=True)
    note.add_argument("--text", required=True)
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "build":
            build()
        elif args.command == "check":
            check()
        elif args.command == "new":
            write_new_trip(args.slug, args.title, args.start, args.end)
        elif args.command == "note":
            add_note(args.slug, args.date, args.title, args.text)
    except TravelError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
