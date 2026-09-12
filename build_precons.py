#!/usr/bin/env python3
"""Build a same-origin Commander precon catalog for Forge Remote Table.

The browser should not depend on the private Commander Forge deployment and
should not need cross-origin MTGJSON reads. This script downloads MTGJSON's
official deck data in GitHub Actions, keeps Commander-style preconstructed
decks, and writes a compact public catalog under data/precons/.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "data" / "precons"
INDEX_PATH = OUTPUT_DIR / "index.json"

DECK_LIST_URLS = (
    "https://mtgjson.com/api/v5/DeckList.json",
    "https://www.mtgjson.com/api/v5/DeckList.json",
    "https://mtgjson.com/api/v5_backup/DeckList.json",
)
ALL_DECK_FILES_URLS = (
    "https://mtgjson.com/api/v5/AllDeckFiles.tar.xz",
    "https://www.mtgjson.com/api/v5/AllDeckFiles.tar.xz",
    "https://mtgjson.com/api/v5_backup/AllDeckFiles.tar.xz",
)
USER_AGENT = "Forge-Remote-Table/1.0 (+GitHub Pages precon builder)"


def download_first(urls: Iterable[str], destination: Path, attempts: int = 3) -> str:
    errors: list[str] = []
    destination.parent.mkdir(parents=True, exist_ok=True)
    for url in urls:
        for attempt in range(1, attempts + 1):
            try:
                request = urllib.request.Request(
                    url,
                    headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
                )
                with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as handle:
                    shutil.copyfileobj(response, handle, length=1024 * 1024)
                if destination.stat().st_size == 0:
                    raise RuntimeError("download was empty")
                print(f"Downloaded {url} -> {destination.name} ({destination.stat().st_size:,} bytes)")
                return url
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, RuntimeError) as exc:
                errors.append(f"{url} attempt {attempt}: {exc}")
                destination.unlink(missing_ok=True)
                if attempt < attempts:
                    time.sleep(min(8, attempt * 2))
    raise RuntimeError("All official MTGJSON downloads failed:\n" + "\n".join(errors[-8:]))


def unwrap(payload: Any) -> Any:
    return payload.get("data") if isinstance(payload, dict) and "data" in payload else payload


def load_index(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = unwrap(payload)
    if not isinstance(rows, list):
        raise ValueError("DeckList.json did not contain a list")
    exact: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        file_name = str(row.get("fileName") or "").strip()
        if not file_name:
            continue
        exact[file_name.lower()] = row
        exact[Path(file_name).stem.lower()] = row
    return exact


def count_value(card: dict[str, Any]) -> int:
    for key in ("count", "quantity", "qty"):
        if key in card:
            try:
                return max(1, int(card[key]))
            except (TypeError, ValueError):
                pass
    return 1


def card_names(board: Any) -> list[str]:
    names: list[str] = []
    if not isinstance(board, list):
        return names
    for card in board:
        if not isinstance(card, dict):
            continue
        name = str(card.get("name") or "").strip()
        if name:
            names.extend([name] * count_value(card))
    return names


def compact_card_entry(card: dict[str, Any]) -> dict[str, Any] | None:
    name = str(card.get("name") or "").strip()
    if not name:
        return None
    identifiers = card.get("identifiers") if isinstance(card.get("identifiers"), dict) else {}
    entry: dict[str, Any] = {"name": name, "count": count_value(card)}
    scryfall_id = str(identifiers.get("scryfallId") or "").strip()
    oracle_id = str(identifiers.get("scryfallOracleId") or "").strip()
    face_name = str(card.get("faceName") or "").strip()
    if scryfall_id:
        entry["scryfallId"] = scryfall_id
    if oracle_id:
        entry["scryfallOracleId"] = oracle_id
    if face_name:
        entry["faceName"] = face_name
    return entry


def merge_card_entries(board: Any) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    if not isinstance(board, list):
        return merged
    for card in board:
        if not isinstance(card, dict):
            continue
        entry = compact_card_entry(card)
        if not entry:
            continue
        key = entry["name"].casefold()
        if key not in merged:
            merged[key] = entry
        else:
            merged[key]["count"] += entry["count"]
            for identifier_key in ("scryfallId", "scryfallOracleId", "faceName"):
                if not merged[key].get(identifier_key) and entry.get(identifier_key):
                    merged[key][identifier_key] = entry[identifier_key]
    return merged


def normalize_deck(payload: Any, meta: dict[str, Any], source_file: str) -> dict[str, Any] | None:
    deck = unwrap(payload)
    if not isinstance(deck, dict):
        return None

    commander_board = deck.get("commander") or deck.get("commanders") or []
    main_board = deck.get("mainBoard") or deck.get("mainboard") or deck.get("main") or deck.get("cards") or []
    side_board = deck.get("sideBoard") or deck.get("sideboard") or []

    commander_names = card_names(commander_board)
    deck_type = str(deck.get("type") or meta.get("type") or "")
    commander_like = bool(commander_names) or any(
        token in deck_type.lower() for token in ("commander", "brawl", "oathbreaker")
    )
    if not commander_like:
        return None

    board = main_board if isinstance(main_board, list) and main_board else side_board
    entries_by_name = merge_card_entries(board)

    commander_entries = merge_card_entries(commander_board)
    for key, commander_entry in commander_entries.items():
        if key not in entries_by_name:
            commander_entry["count"] = 1
            entries_by_name[key] = commander_entry
        else:
            for identifier_key in ("scryfallId", "scryfallOracleId", "faceName"):
                if not entries_by_name[key].get(identifier_key) and commander_entry.get(identifier_key):
                    entries_by_name[key][identifier_key] = commander_entry[identifier_key]

    entries = sorted(entries_by_name.values(), key=lambda item: item["name"].casefold())
    total = sum(int(entry.get("count") or 0) for entry in entries)
    if total < 40 or not entries:
        return None

    name = str(deck.get("name") or meta.get("name") or Path(source_file).stem).strip()
    code = str(deck.get("code") or meta.get("code") or "").strip()
    release_date = str(deck.get("releaseDate") or meta.get("releaseDate") or "").strip()

    return {
        "name": name,
        "entries": entries,
        "commanderNames": list(dict.fromkeys(commander_names)),
        "releaseDate": release_date,
        "type": deck_type,
        "code": code,
        "sourceFile": source_file,
        "cardCount": total,
    }


def safe_file_name(source_file: str) -> str:
    stem = Path(source_file).stem
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._")[:100] or "deck"
    digest = hashlib.sha1(source_file.encode("utf-8")).hexdigest()[:10]
    return f"{slug}-{digest}.json"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUTPUT_DIR.glob("*.json"):
        old.unlink()

    with tempfile.TemporaryDirectory(prefix="forge-remote-precons-") as temp_name:
        temp = Path(temp_name)
        deck_list_path = temp / "DeckList.json"
        archive_path = temp / "AllDeckFiles.tar.xz"
        deck_list_source = download_first(DECK_LIST_URLS, deck_list_path)
        archive_source = download_first(ALL_DECK_FILES_URLS, archive_path)
        meta_lookup = load_index(deck_list_path)

        index: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        processed = 0

        with tarfile.open(archive_path, mode="r:xz") as archive:
            for member in archive:
                if not member.isfile() or not member.name.lower().endswith(".json"):
                    continue
                processed += 1
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                try:
                    payload = json.load(extracted)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

                basename = Path(member.name).name
                meta = meta_lookup.get(basename.lower()) or meta_lookup.get(Path(basename).stem.lower()) or {}
                normalized = normalize_deck(payload, meta, basename)
                if not normalized:
                    continue

                dedupe_key = f"{normalized['name'].lower()}|{normalized['code'].lower()}|{normalized['releaseDate']}"
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)

                local_file = safe_file_name(basename)
                (OUTPUT_DIR / local_file).write_text(
                    json.dumps({"data": normalized}, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8",
                )
                index.append({
                    "name": normalized["name"],
                    "fileName": basename,
                    "code": normalized["code"],
                    "releaseDate": normalized["releaseDate"],
                    "type": normalized["type"],
                    "cardCount": normalized["cardCount"],
                    "commanderNames": normalized["commanderNames"],
                    "localFile": local_file,
                })

    index.sort(key=lambda item: (item.get("releaseDate") or "", item.get("name") or ""), reverse=True)
    result = {
        "meta": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "count": len(index),
            "deckListSource": deck_list_source,
            "archiveSource": archive_source,
            "processedFiles": processed,
        },
        "data": index,
    }
    INDEX_PATH.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Built {len(index):,} Commander-style precons from {processed:,} deck files")
    if not index:
        raise RuntimeError("No Commander precons were generated")


if __name__ == "__main__":
    main()
