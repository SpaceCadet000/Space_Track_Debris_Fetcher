# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# Python Script to download .tle of space debris fom Space_Track.org
# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
"""

Interactively prompts the user for filtering options before downloading
debris TLEs from Space-Track.org's GP class API.

Options:
  - Credentials (env vars or interactive)
  - Include decayed objects?
  - Object type (DEBRIS only, or also ROCKET BODY, UNKNOWN, etc.)
  - Orbital regime (LEO / MEO / GEO / HEO / all)
  - RCS size filter (SMALL / MEDIUM / LARGE / all)
  - Epoch age (only recent TLEs, e.g. last 30 days)
  - Output format (TLE 2-line / 3-line with name / CSV / JSON)
  - Country of origin filter

Usage:
    python space_track_downloader.py

Credentials via env vars (optional):
    export SPACETRACK_USER="your_email"
    export SPACETRACK_PASS="your_password"
"""

import requests
import os
import sys
import time
import json
import getpass
from datetime import datetime, timezone
from pathlib import Path


# ── Constants ───────────────────────────────────────────────────────────────
BASE_URL = "https://www.space-track.org"
LOGIN_URL = f"{BASE_URL}/ajaxauth/login"
QUERY_URL = f"{BASE_URL}/basicspacedata/query"

BATCH_SIZE = 5000
MAX_NORAD_ID = 250000
REQUEST_DELAY_S = 3.0


# ── Interactive prompts ─────────────────────────────────────────────────────
def prompt_choice(prompt_text: str, options: dict, default: str = None) -> str:
    """
    Display a numbered menu and return the user's selection.
    `options` is an OrderedDict-like: {key: description}
    """
    print(f"\n{'─' * 60}")
    print(f"  {prompt_text}")
    print(f"{'─' * 60}")
    keys = list(options.keys())
    for i, (key, desc) in enumerate(options.items(), 1):
        marker = " *" if key == default else ""
        print(f"  [{i}] {desc}{marker}")
    if default:
        print(f"\n  (Press Enter for default: {options[default]})")

    while True:
        raw = input("  > ").strip()
        if raw == "" and default:
            print(f"  → {options[default]}")
            return default
        try:
            idx = int(raw)
            if 1 <= idx <= len(keys):
                chosen = keys[idx - 1]
                print(f"  → {options[chosen]}")
                return chosen
        except ValueError:
            pass
        print(f"  Invalid choice. Enter 1–{len(keys)}.")


def prompt_yes_no(prompt_text: str, default: bool = True) -> bool:
    """Simple yes/no prompt."""
    suffix = "[Y/n]" if default else "[y/N]"
    raw = input(f"\n  {prompt_text} {suffix}: ").strip().lower()
    if raw == "":
        return default
    return raw in ("y", "yes")


def prompt_int(prompt_text: str, default: int = None, min_val: int = None, max_val: int = None) -> int:
    """Prompt for an integer with optional bounds."""
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"\n  {prompt_text}{suffix}: ").strip()
        if raw == "" and default is not None:
            return default
        try:
            val = int(raw)
            if min_val is not None and val < min_val:
                print(f"  Must be >= {min_val}")
                continue
            if max_val is not None and val > max_val:
                print(f"  Must be <= {max_val}")
                continue
            return val
        except ValueError:
            print("  Enter a valid integer.")


def get_credentials() -> tuple:
    """Get Space-Track credentials from env or interactive prompt."""
    print("\n" + "=" * 60)
    print("  SPACE-TRACK.ORG CREDENTIALS")
    print("=" * 60)
    user = os.environ.get("SPACETRACK_USER")
    pw = os.environ.get("SPACETRACK_PASS")
    if user and pw:
        print(f"  Using credentials from environment variables.")
        print(f"  Username: {user}")
        return user, pw
    if user:
        print(f"  Username (from env): {user}")
    else:
        user = input("  Username (email): ").strip()
    pw = getpass.getpass("  Password: ")
    return user, pw


def gather_options() -> dict:
    """Interactively collect all query options from the user."""
    opts = {}

    print("\n" + "=" * 60)
    print("  SPACE-TRACK DEBRIS TLE DOWNLOADER")
    print("  Configure your query options below.")
    print("=" * 60)

    # ── 1. Object type ──────────────────────────────────────────────
    opts["object_types"] = prompt_choice(
        "What object types do you want to download?",
        {
            "debris_only":      "Debris only",
            "debris_rb":        "Debris + Rocket bodies",
            "debris_rb_unk":    "Debris + Rocket bodies + Unknown",
            "all":              "All object types (Payload, Debris, R/B, Unknown)",
        },
        default="debris_only"
    )

    # ── 2. Decayed objects ──────────────────────────────────────────
    opts["include_decayed"] = prompt_choice(
        "Include decayed (re-entered) objects?",
        {
            "no":           "No — only objects currently in orbit",
            "yes":          "Yes — include decayed objects too",
            "decayed_only": "Decayed only — objects that have re-entered",
        },
        default="no"
    )

    # ── 3. Orbital regime ───────────────────────────────────────────
    opts["orbit_regime"] = prompt_choice(
        "Filter by orbital regime?",
        {
            "all":  "All orbits",
            "leo":  "LEO  — Low Earth Orbit (perigee < 2,000 km)",
            "meo":  "MEO  — Medium Earth Orbit (2,000–35,586 km)",
            "geo":  "GEO  — Geosynchronous (period ~1436 min)",
            "heo":  "HEO  — Highly Elliptical (eccentricity > 0.25)",
        },
        default="all"
    )

    # ── 4. RCS size ─────────────────────────────────────────────────
    opts["rcs_size"] = prompt_choice(
        "Filter by Radar Cross Section (RCS) size?",
        {
            "all":    "All sizes",
            "large":  "Large  (> 1.0 m²)",
            "medium": "Medium (0.1 – 1.0 m²)",
            "small":  "Small  (< 0.1 m²)",
        },
        default="all"
    )

    # ── 5. Epoch freshness ──────────────────────────────────────────
    opts["epoch_days"] = prompt_choice(
        "Filter by epoch age (how recent the TLE is)?",
        {
            "all":    "All epochs (no filter)",
            "30":     "Last 30 days only",
            "90":     "Last 90 days only",
            "180":    "Last 180 days only",
            "365":    "Last 365 days only",
        },
        default="all"
    )

    # ── 6. Country/owner ────────────────────────────────────────────
    opts["country"] = prompt_choice(
        "Filter by country/owner (COUNTRY_CODE)?",
        {
            "all":  "All countries",
            "US":   "United States",
            "CIS":  "Commonwealth of Independent States (Russia)",
            "PRC":  "People's Republic of China",
            "ISS":  "International Space Station partners",
            "IND":  "India",
            "JPN":  "Japan",
            "ESA":  "European Space Agency",
            "custom": "Enter a custom country code",
        },
        default="all"
    )
    if opts["country"] == "custom":
        opts["country"] = input("  Enter country code (e.g., FR, UK, IT): ").strip().upper()

    # ── 7. Output format ────────────────────────────────────────────
    opts["format"] = prompt_choice(
        "Output format?",
        {
            "tle":  "2-line TLE (standard, compatible with SGP4)",
            "3le":  "3-line TLE (includes object name on line 0)",
            "csv":  "CSV (all GP fields, good for analysis)",
            "json": "JSON (all GP fields, structured)",
        },
        default="tle"
    )

    # ── 8. Summary & confirm ────────────────────────────────────────
    print_summary(opts)
    if not prompt_yes_no("Proceed with this query?", default=True):
        print("  Aborted.")
        sys.exit(0)

    return opts


def print_summary(opts: dict):
    """Print a summary of the selected options."""
    type_labels = {
        "debris_only":   "DEBRIS",
        "debris_rb":     "DEBRIS, ROCKET BODY",
        "debris_rb_unk": "DEBRIS, ROCKET BODY, UNKNOWN",
        "all":           "ALL (PAYLOAD, DEBRIS, ROCKET BODY, UNKNOWN)",
    }
    decay_labels = {
        "no":           "On-orbit only (exclude decayed)",
        "yes":          "Include decayed",
        "decayed_only": "Decayed only",
    }
    regime_labels = {
        "all": "All", "leo": "LEO (<2000 km)", "meo": "MEO (2000–35586 km)",
        "geo": "GEO (~1436 min)", "heo": "HEO (ecc>0.25)",
    }
    rcs_labels = {"all": "All", "large": "Large", "medium": "Medium", "small": "Small"}
    epoch_labels = {"all": "All", "30": "30 days", "90": "90 days", "180": "180 days", "365": "365 days"}
    fmt_labels = {"tle": "2-line TLE", "3le": "3-line TLE", "csv": "CSV", "json": "JSON"}

    print(f"\n{'=' * 60}")
    print(f"  QUERY SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Object types : {type_labels.get(opts['object_types'], opts['object_types'])}")
    print(f"  Decayed      : {decay_labels.get(opts['include_decayed'], opts['include_decayed'])}")
    print(f"  Orbit regime : {regime_labels.get(opts['orbit_regime'], opts['orbit_regime'])}")
    print(f"  RCS size     : {rcs_labels.get(opts['rcs_size'], opts['rcs_size'])}")
    print(f"  Epoch age    : {epoch_labels.get(opts['epoch_days'], opts['epoch_days'])}")
    print(f"  Country      : {opts['country'] if opts['country'] != 'all' else 'All'}")
    print(f"  Format       : {fmt_labels.get(opts['format'], opts['format'])}")
    print(f"{'=' * 60}")


# ── Query construction ──────────────────────────────────────────────────────
def build_query_filters(opts: dict) -> str:
    """Build the Space-Track API URL filter path from options."""
    filters = []

    # Object type
    type_map = {
        "debris_only":   "DEBRIS",
        "debris_rb":     "DEBRIS,ROCKET BODY",
        "debris_rb_unk": "DEBRIS,ROCKET BODY,UNKNOWN",
    }
    if opts["object_types"] in type_map:
        filters.append(f"/OBJECT_TYPE/{type_map[opts['object_types']]}")
    # "all" = no OBJECT_TYPE filter

    # Decay filter
    if opts["include_decayed"] == "no":
        filters.append("/DECAY_DATE/null-val")
    elif opts["include_decayed"] == "decayed_only":
        filters.append("/DECAY_DATE/<>null-val")

    # Orbital regime (using derived perigee/apogee/period/eccentricity)
    regime = opts["orbit_regime"]
    if regime == "leo":
        filters.append("/PERIGEE/<2000")
    elif regime == "meo":
        filters.append("/PERIGEE/2000--35586")
    elif regime == "geo":
        filters.append("/PERIOD/1430--1450")
    elif regime == "heo":
        filters.append("/ECCENTRICITY/>0.25")

    # RCS size
    if opts["rcs_size"] != "all":
        rcs_map = {"large": "LARGE", "medium": "MEDIUM", "small": "SMALL"}
        filters.append(f"/RCS_SIZE/{rcs_map[opts['rcs_size']]}")

    # Epoch freshness
    if opts["epoch_days"] != "all":
        filters.append(f"/EPOCH/>now-{opts['epoch_days']}")

    # Country
    if opts["country"] != "all":
        filters.append(f"/COUNTRY_CODE/{opts['country']}")

    return "".join(filters)


def build_format_suffix(opts: dict) -> str:
    """Return the format part of the query URL."""
    return f"/format/{opts['format']}"


def get_file_extension(fmt: str) -> str:
    """Return the appropriate file extension for the output format."""
    return {"tle": ".tle", "3le": ".tle", "csv": ".csv", "json": ".json"}[fmt]


# ── Download logic ──────────────────────────────────────────────────────────
def login(session: requests.Session, user: str, pw: str):
    resp = session.post(LOGIN_URL, data={"identity": user, "password": pw})
    resp.raise_for_status()
    if "Failed" in resp.text or "Login" in resp.text:
        raise RuntimeError(f"Login failed. Check credentials.\nResponse: {resp.text[:300]}")
    print("\n[+] Logged in to Space-Track.")


def fetch_batch(session: requests.Session, filters: str, fmt_suffix: str,
                norad_start: int, norad_end: int) -> str:
    """Fetch a batch of objects by NORAD ID range."""
    query = (
        f"{QUERY_URL}"
        f"/class/gp"
        f"{filters}"
        f"/NORAD_CAT_ID/{norad_start}--{norad_end}"
        f"/orderby/NORAD_CAT_ID"
        f"{fmt_suffix}"
    )
    resp = session.get(query, timeout=180)
    resp.raise_for_status()
    return resp.text


def try_bulk_download(session: requests.Session, filters: str, fmt_suffix: str) -> str | None:
    """Try a single bulk query first. Returns None on timeout/error."""
    query = (
        f"{QUERY_URL}"
        f"/class/gp"
        f"{filters}"
        f"/orderby/NORAD_CAT_ID"
        f"{fmt_suffix}"
    )
    print("[*] Attempting bulk download (single request)...")
    try:
        resp = session.get(query, timeout=300)
        resp.raise_for_status()
        return resp.text
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        print(f"[!] Bulk download timed out: {e}")
        print("[*] Falling back to batched download...")
        return None


def count_objects(text: str, fmt: str) -> int:
    """Count the number of objects in the response."""
    if not text or not text.strip():
        return 0
    if fmt in ("tle", "3le"):
        lines = [l for l in text.strip().split("\n") if l.strip()]
        divisor = 2 if fmt == "tle" else 3
        return len(lines) // divisor
    elif fmt == "json":
        try:
            data = json.loads(text)
            return len(data) if isinstance(data, list) else 0
        except json.JSONDecodeError:
            return 0
    elif fmt == "csv":
        lines = text.strip().split("\n")
        return max(0, len(lines) - 1)  # subtract header
    return 0


def download_data(session: requests.Session, opts: dict) -> tuple:
    """Download the data, returns (text_content, object_count)."""
    filters = build_query_filters(opts)
    fmt_suffix = build_format_suffix(opts)

    print(f"\n[*] Query filters: {filters}")
    print(f"[*] Format: {opts['format']}")

    # Try bulk first
    result = try_bulk_download(session, filters, fmt_suffix)
    if result and result.strip():
        n = count_objects(result, opts["format"])
        if n > 0:
            print(f"[+] Bulk download succeeded: {n} objects")
            return result, n

    # Fall back to batched
    print(f"[*] Batched download: scanning NORAD IDs 1–{MAX_NORAD_ID} in chunks of {BATCH_SIZE}")
    all_chunks = []
    total = 0
    consecutive_empty = 0
    found_any = False

    for start in range(1, MAX_NORAD_ID + 1, BATCH_SIZE):
        end = start + BATCH_SIZE - 1
        print(f"  NORAD {start:>6d}–{end:>6d} ... ", end="", flush=True)

        try:
            chunk = fetch_batch(session, filters, fmt_suffix, start, end)
        except requests.exceptions.RequestException as e:
            print(f"ERROR: {e}")
            time.sleep(REQUEST_DELAY_S * 2)
            consecutive_empty += 1
            continue

        n = count_objects(chunk, opts["format"])
        if n > 0:
            found_any = True
            consecutive_empty = 0

            # For CSV, strip header from subsequent chunks
            if opts["format"] == "csv" and all_chunks:
                lines = chunk.strip().split("\n")
                chunk = "\n".join(lines[1:])  # remove header row

            all_chunks.append(chunk.strip())
            total += n
            print(f"{n:>5d} objects  (total: {total})")
        else:
            print("     0")
            if found_any:
                consecutive_empty += 1

        # Early stop: if we've found data and then hit 5 consecutive empty
        # batches, we're past the populated range
        if found_any and consecutive_empty >= 5:
            print(f"[*] 5 consecutive empty batches — stopping early.")
            break

        time.sleep(REQUEST_DELAY_S)

    combined = "\n".join(all_chunks) if all_chunks else ""
    return combined, total


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    user, pw = get_credentials()
    opts = gather_options()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ext = get_file_extension(opts["format"])
    out_data = Path(f"spacetrack_debris_{timestamp}{ext}")
    out_meta = Path(f"spacetrack_debris_{timestamp}_meta.json")

    session = requests.Session()
    login(session, user, pw)

    data_text, n_objects = download_data(session, opts)

    if n_objects == 0:
        print("\n[!] No objects matched your query. Try broader filters.")
        sys.exit(1)

    # Write data file
    out_data.write_text(data_text.strip() + "\n", encoding="utf-8")
    print(f"\n[+] Wrote {n_objects} objects → {out_data}")

    # Write metadata
    meta = {
        "source": "space-track.org",
        "api_class": "gp",
        "timestamp_utc": timestamp,
        "num_objects": n_objects,
        "output_file": str(out_data),
        "options": opts,
        "query_filters": build_query_filters(opts),
    }
    out_meta.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[+] Metadata  → {out_meta}")

    # Preview
    if opts["format"] in ("tle", "3le"):
        lines = [l for l in data_text.strip().split("\n") if l.strip()]
        preview_n = 6 if opts["format"] == "tle" else 9
        print(f"\n── First few TLE sets ──")
        for line in lines[:preview_n]:
            print(line)
    elif opts["format"] == "csv":
        lines = data_text.strip().split("\n")
        print(f"\n── CSV header ──")
        print(lines[0])
        print(f"── First row ──")
        if len(lines) > 1:
            print(lines[1])

    print(f"\n{'=' * 60}")
    print(f"  DONE — {n_objects} objects downloaded.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()