# Setup guide: Lake Champlain Drift Buoy Tracker

This project has three moving pieces:

1. **`scripts/pull_sheet_data.py`** — reads new rows from your Google Sheet
2. **`.github/workflows/pull-buoy-data.yml`** — runs that script every 20 minutes for free, using GitHub Actions
3. **`index.html`** — a Leaflet map that reads `data/buoy_track.json` and shows buoy position + drift trail + water temp

No server to maintain. GitHub does the scheduled pulling; GitHub Pages hosts the map.

---

## 1. Match the script to your sheet's columns

Open `scripts/pull_sheet_data.py` and check the "DIALS" section near the top:

```python
COL_BUOY_ID = "buoy_id"
COL_GPS_TIME = "gps_time"
COL_LAT = "latitude"
COL_LON = "longitude"
COL_TEMP_C = "temperature_c"
WORKSHEET_NAME = "Sheet1"
```

Change these strings to match the actual header row in your spreadsheet, and set `WORKSHEET_NAME` to the tab your data lives on. If you only have one buoy, you can leave `buoy_id` out of the sheet entirely — the script will fall back to naming it `"buoy_1"`.

## 2. Create a Google service account (read-only key)

This lets the script read the sheet without using your personal login.

1. Go to [console.cloud.google.com](https://console.cloud.google.com), create (or pick) a project.
2. **APIs & Services → Library** → enable the **Google Sheets API**.
3. **APIs & Services → Credentials → Create Credentials → Service Account**. Name it anything (e.g. `buoy-reader`).
4. Open the new service account → **Keys → Add Key → Create new key → JSON**. This downloads a `.json` file — keep it private, don't commit it to the repo.
5. Copy the service account's email address (looks like `buoy-reader@your-project.iam.gserviceaccount.com`).
6. In your Google Sheet, click **Share** and share it with that email address as a **Viewer**.

## 3. Create the GitHub repo

1. Create a new repository on GitHub (public or private both work; public is required for free GitHub Pages unless you have GitHub Pro/Team).
2. Upload all the files in this project, preserving the folder structure (`scripts/`, `.github/workflows/`, `data/`, `index.html`).

## 4. Add repo secrets

In your repo: **Settings → Secrets and variables → Actions → New repository secret**. Add two:

| Secret name | Value |
|---|---|
| `SHEET_ID` | The long ID from your sheet's URL: `docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Paste the *entire contents* of the JSON key file you downloaded in step 2 |

## 5. Turn on GitHub Pages

**Settings → Pages** → Source: "Deploy from a branch" → Branch: `main`, folder `/ (root)`. Save. GitHub will give you a URL like `https://yourusername.github.io/repo-name/`.

## 6. Test it

Go to the **Actions** tab in your repo → select "Pull buoy data from Google Sheet" → **Run workflow** to trigger it manually the first time, instead of waiting for the schedule. Check that:

- The job finishes green
- `data/buoy_track.json` in the repo now has real coordinates in it (refresh the file view on GitHub)
- Your Pages URL shows the buoy marker and (once there are 2+ points) a drift trail

After that, it runs automatically every 20 minutes.

---

## Notes and caveats

- **Schedule timing isn't exact.** GitHub Actions cron jobs are queued, not guaranteed-instant — during high load on GitHub's infrastructure, a run can be delayed by a few minutes. Fine for a drift buoy; not fine for anything safety-critical.
- **Inactive repos pause schedules.** GitHub disables scheduled workflows after 60 days with no commits to the repo. A manual "Run workflow" click re-enables it.
- **The JSON data file is public** once Pages is on (public repo). That's normal for this kind of project — the buoy telemetry is the point of the site — but don't put anything sensitive in that sheet.
- **Multiple buoys** work automatically: just make sure every row has a `buoy_id`, and each buoy gets its own colored trail and marker.
