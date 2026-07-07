"""
pull_sheet_data.py

Pulls buoy telemetry rows from a Google Sheet and merges any new rows into
a JSON file (data/buoy_track.json) that the live map (index.html) reads.

Meant to be run on a schedule by GitHub Actions
(.github/workflows/pull-buoy-data.yml), but it works fine run locally too:

    export SHEET_ID="your-sheet-id"
    export GOOGLE_SERVICE_ACCOUNT_JSON="$(cat service-account.json)"
    python scripts/pull_sheet_data.py

------------------------------------------------------------------------
DIALS -- the settings you'll most likely need to change for your sheet
------------------------------------------------------------------------
"""

import os
import json
import datetime
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

# ---- DIALS ---------------------------------------------------------------

# Column headers exactly as they appear in row 1 of the Google Sheet.
# Change these to match whatever your buoy firmware / Adafruit IO export
# actually names its columns.
COL_BUOY_ID = "Buoy #"        # which buoy this row belongs to (e.g. "buoy_5")
COL_GPS_TIME = "timestamp"      # ISO 8601 UTC timestamp from the GPS fix
COL_LAT = "lat"
COL_LON = "lon"
COL_TEMP_C = "temp_c"

# Name of the worksheet (tab) inside the spreadsheet to read from.
WORKSHEET_NAME = "All Data"

# Where the accumulated track data gets written (read by index.html).
OUTPUT_PATH = Path("data/buoy_track.json")

# ---------------------------------------------------------------------------


def get_sheet_rows():
    """Authenticate with a service account and return all rows as dicts."""
    sheet_id = os.environ["SHEET_ID"]
    creds_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

    creds_info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).worksheet(WORKSHEET_NAME)
    return sheet.get_all_records()  # list of dicts, keyed by the header row


def load_existing_data():
    """Load whatever track data we've already saved, or start fresh."""
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            return json.load(f)
    return {"buoys": {}, "last_updated": None}


def try_float(value):
    """Convert a sheet cell to a float, or return None if it's blank,
    'N/A', or anything else that isn't a valid number."""
    if value in ("", None):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def merge_new_rows(data, rows):
    """Add rows we haven't seen before. A row is identified by its
    (buoy_id, gps_time) pair, so re-running this script never creates
    duplicate points even if the sheet still contains old rows."""
    added = 0
    for row in rows:
        buoy_id = str(row.get(COL_BUOY_ID, "buoy_1")).strip() or "buoy_1"
        gps_time = str(row.get(COL_GPS_TIME, "")).strip()

        lat = try_float(row.get(COL_LAT))
        lon = try_float(row.get(COL_LON))
        temp_c = try_float(row.get(COL_TEMP_C))

        if not gps_time or lat is None or lon is None:
            continue  # skip rows with no timestamp or no valid GPS fix (e.g. "N/A")

        buoy = data["buoys"].setdefault(
            buoy_id, {"name": buoy_id, "history": []}
        )
        already_have = any(pt["gps_time"] == gps_time for pt in buoy["history"])
        if already_have:
            continue

        buoy["history"].append({
            "gps_time": gps_time,
            "lat": lat,
            "lon": lon,
            "temp_c": temp_c,  # None is fine here -- the map just shows "—"
        })
        added += 1

    # Keep each buoy's history in chronological order for a clean drift trail.
    for buoy in data["buoys"].values():
        buoy["history"].sort(key=lambda pt: pt["gps_time"])

    data["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
    return added


def main():
    rows = get_sheet_rows()
    data = load_existing_data()
    added = merge_new_rows(data, rows)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Pulled {len(rows)} rows from the sheet, added {added} new point(s).")


if __name__ == "__main__":
    main()
