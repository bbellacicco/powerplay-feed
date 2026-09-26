#!/usr/bin/env python3
"""
Powerplay Windsor - local schedule & results scraper.

Pulls upcoming games and recent results for Windsor-Essex teams and writes
one combined file: data/local-games.json (read by local-games.html).

Sources
  Windsor Spitfires   HockeyTech feed used by chl.ca (all OHL games: preseason,
                      regular season, playoffs)
  Windsor Lancers     golancers.ca composite calendar (every varsity sport)
  St. Clair Saints    saintsathletics.ca blocks automated requests, so Saints
                      games come from the MANUAL_SHEET_CSV below (optional)

Runs on GitHub Actions (see .github/workflows/local-games.yml). Standard
library only - nothing to install.

Local test without internet:  python scripts/scrape_local.py --fixtures fixtures
"""

import csv
import io
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# ------------------------------------------------------------------ settings
# Edit these in GitHub's web editor if anything needs to change.

# The widget shows two Monday-to-Sunday weeks: "This week" (the week the run
# happens in, so a weekend run still includes that weekend) and "Last week".
DAYS_BACK = 7
DAYS_AHEAD = 13     # extra room so the HockeyTech request covers the whole week

# Spitfires (OHL). Key is the public key chl.ca itself uses. Team 17 = Windsor.
OHL_KEY = "f1aa699db3d81487"
SPITFIRES_TEAM_ID = "17"

# Lancers sports to leave out (SIDEARM "shortname"). Cheer only appears as
# sideline cheer at football games, so it would duplicate those rows.
LANCERS_SKIP_SPORTS = {"cheer"}

# Optional Google Sheet for anything that can't be scraped (St. Clair Saints,
# high schools, etc.). In Google Sheets: File > Share > Publish to web >
# pick the tab > "Comma-separated values (.csv)" > Publish, then paste the
# link here. Columns (header row required):
#   team, sport, date, time, home_away, opponent, location, our_score, opp_score, note, link
# team is a key like "saints"; date is YYYY-MM-DD; time like 7:00 PM (blank = TBA);
# home_away is H, A or N; leave scores blank for upcoming games.
MANUAL_SHEET_CSV = os.environ.get("MANUAL_SHEET_CSV", "")

TEAMS = {
    "spitfires": {"name": "Windsor Spitfires", "short": "Spitfires", "league": "OHL"},
    "lancers": {"name": "Windsor Lancers", "short": "Lancers", "league": "U SPORTS / OUA"},
    "saints": {"name": "St. Clair Saints", "short": "Saints", "league": "OCAA"},
}

OUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "local-games.json")
TZ = ZoneInfo("America/Toronto")
UA = "PowerplayWindsorFeed/1.0 (+https://www.powerplaywindsor.com)"

# ------------------------------------------------------------------ helpers

FIXTURES = None  # set by --fixtures for offline testing


def fetch(url, fixture=None):
    if FIXTURES and fixture:
        with open(os.path.join(FIXTURES, fixture), encoding="utf-8") as f:
            return f.read()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/csv,*/*"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8-sig")


def to_int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def game(team, sport, start, time_tbd, home_away, opponent, location="",
         status="upcoming", our=None, opp=None, result=None, note="", links=None, gid=""):
    return {
        "id": f"{team}-{gid}",
        "team": team,
        "sport": sport,
        "start": start.isoformat(),
        "time_tbd": bool(time_tbd),
        "home_away": home_away,          # H, A, N
        "opponent": " ".join(str(opponent).split()),
        "location": location or "",
        "status": status,                # upcoming | live | final | postponed | cancelled
        "our_score": our,
        "opp_score": opp,
        "result": result,                # W, L, T, OTL, SOL or None
        "note": note or "",
        "links": {k: v for k, v in (links or {}).items() if v},
    }

# ------------------------------------------------------------------ Spitfires


def scrape_spitfires():
    url = ("https://lscluster.hockeytech.com/feed/?feed=modulekit&view=scorebar"
           f"&key={OHL_KEY}&client_code=ohl&team_id={SPITFIRES_TEAM_ID}"
           f"&numberofdaysback={DAYS_BACK}&numberofdaysahead={DAYS_AHEAD}"
           "&season_id=&lang_code=en&fmt=json")
    data = json.loads(fetch(url, "spitfires.json"))
    out = []
    for g in data["SiteKit"]["Scorebar"]:
        home = g["HomeID"] == SPITFIRES_TEAM_ID
        start = datetime.fromisoformat(g["GameDateISO8601"]).astimezone(TZ)
        hg, vg = to_int(g["HomeGoals"]), to_int(g["VisitorGoals"])
        our, opp = (hg, vg) if home else (vg, hg)
        code = g.get("GameStatus")
        period = to_int(g.get("Period")) or 0
        status, result, note = "upcoming", None, ""
        if code == "4":
            status = "final"
            if period == 4:
                note = "OT"
            elif period >= 5:
                note = "SO"
            if our > opp:
                result = "W"
            else:
                result = {"OT": "OTL", "SO": "SOL"}.get(note, "L")
        elif code in ("2", "3"):
            status = "live"
            note = g.get("GameStatusString", "")
        else:
            our = opp = None
        low = (g.get("GameStatusString") or "").lower()
        if "postpon" in low:
            status = "postponed"
        elif "cancel" in low:
            status = "cancelled"
        season_note = {"87": "Preseason"}.get(g.get("SeasonID"), "")
        venue = ", ".join(x for x in [g.get("venue_name"), g.get("venue_location")] if x)
        out.append(game(
            "spitfires", "Hockey", start, g.get("TimeTbd") == "1",
            "H" if home else "A",
            g["VisitorLongName"] if home else g["HomeLongName"],
            location=venue, status=status, our=our, opp=opp, result=result,
            note=" · ".join(x for x in [note, season_note] if x),
            links={
                "tickets": g.get("TicketUrl") if status == "upcoming" else "",
                "gamecentre": f"https://chl.ca/ohl-spitfires/gamecentre/{g['ID']}/",
            },
            gid=g["ID"],
        ))
    return out

# ------------------------------------------------------------------ Lancers


def scrape_lancers(week_start):
    base = "https://golancers.ca"
    seen, out = set(), []
    # month view covers a 6-week grid; ask for each month the window touches
    months, d = [], (week_start - timedelta(days=7)).replace(day=1)
    while d <= week_start + timedelta(days=6):
        months.append(d)
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    for i, m in enumerate(months):
        url = f"{base}/services/responsive-calendar.ashx?type=month&sport=0&location=all&date={m.month}/1/{m.year}"
        days = json.loads(fetch(url, "lancers_sep.json" if i == 0 else None) if not (FIXTURES and i) else "[]")
        for day in days:
            for e in day.get("events") or []:
                if e["id"] in seen or e["sport"]["shortname"] in LANCERS_SKIP_SPORTS:
                    continue
                seen.add(e["id"])
                start = datetime.fromisoformat(e["date"]).replace(tzinfo=TZ)
                time_tbd = start.hour == 0 and start.minute == 0
                r = e.get("result") or {}
                noplay = (e.get("noplay_text") or "").lower()
                status, result, our, opp = "upcoming", None, None, None
                note_bits = []
                if "postpon" in noplay:
                    status = "postponed"
                elif "cancel" in noplay:
                    status = "cancelled"
                elif e.get("status") == "O" or r.get("status"):
                    status = "final"
                    our, opp = to_int(r.get("team_score")), to_int(r.get("opponent_score"))
                    result = r.get("status") if r.get("status") in ("W", "L", "T") else None
                    if r.get("postscore_info"):
                        note_bits.append(r["postscore_info"].strip("() "))
                if e.get("type") == "S":
                    note_bits.append("Exhibition")
                if e.get("tournament"):
                    note_bits.append(e["tournament"]["title"])
                ha = {"H": "H", "A": "A"}.get(e.get("location_indicator"), "N")
                loc = (e.get("facility") or {}).get("title") or e.get("location") or ""
                links = {}
                for k in ("boxscore", "recap"):
                    u = (r.get(k) or {}).get("url")
                    if u:
                        links[k] = u if u.startswith("http") else base + u
                media = e.get("media") or {}
                if status == "upcoming":
                    links["tickets"] = ((media.get("tickets") or {}).get("url")) or ""
                    links["watch"] = ((media.get("video") or {}).get("url")) or ""
                out.append(game(
                    "lancers", e["sport"]["title"], start, time_tbd, ha,
                    (e.get("opponent") or {}).get("title") or "TBA",
                    location=loc, status=status, our=our, opp=opp, result=result,
                    note=" · ".join(note_bits), links=links, gid=e["id"],
                ))
    return out

# ------------------------------------------------------------------ Manual sheet


def scrape_manual_sheet():
    if not MANUAL_SHEET_CSV:
        return []
    text = fetch(MANUAL_SHEET_CSV, "manual.csv")
    out = []
    for n, row in enumerate(csv.DictReader(io.StringIO(text))):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        team = row.get("team", "").lower()
        if not team or not row.get("date"):
            continue
        t = row.get("time", "")
        try:
            day = datetime.strptime(row["date"], "%Y-%m-%d")
        except ValueError:
            print(f"  manual sheet row {n + 2}: bad date {row['date']!r} (use YYYY-MM-DD)", file=sys.stderr)
            continue
        start, tbd = day, True
        for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M", "%I %p"):
            try:
                tt = datetime.strptime(t.upper(), fmt)
                start, tbd = day.replace(hour=tt.hour, minute=tt.minute), False
                break
            except ValueError:
                pass
        start = start.replace(tzinfo=TZ)
        our, opp = to_int(row.get("our_score")), to_int(row.get("opp_score"))
        note = row.get("note", "")
        status, result = "upcoming", None
        if "postpon" in note.lower():
            status = "postponed"
        elif "cancel" in note.lower():
            status = "cancelled"
        elif our is not None and opp is not None:
            status = "final"
            result = "W" if our > opp else "L" if our < opp else "T"
        out.append(game(
            team, row.get("sport", ""), start, tbd, (row.get("home_away") or "N").upper()[:1],
            row.get("opponent", "TBA"), location=row.get("location", ""), status=status,
            our=our, opp=opp, result=result, note=note,
            links={"link": row.get("link", "")}, gid=f"sheet{n}",
        ))
    return out

# ------------------------------------------------------------------ main


def main():
    global FIXTURES
    if "--fixtures" in sys.argv:
        FIXTURES = sys.argv[sys.argv.index("--fixtures") + 1]
    now = datetime.now(TZ)
    if FIXTURES:
        now = datetime(2026, 9, 26, 12, 0, tzinfo=TZ)  # fixture date
    today = now.date()
    week_start = today - timedelta(days=today.weekday())  # Monday of this week

    games, sources = [], {}
    for key, fn in (("spitfires", scrape_spitfires),
                    ("lancers", lambda: scrape_lancers(week_start)),
                    ("sheet", scrape_manual_sheet)):
        try:
            got = fn()
            games += got
            sources[key] = {"ok": True, "count": len(got)}
            print(f"{key}: {len(got)} games")
        except Exception as ex:  # one source failing shouldn't kill the rest
            sources[key] = {"ok": False, "error": str(ex)[:200]}
            print(f"{key}: FAILED - {ex}", file=sys.stderr)

    lo = datetime.combine(week_start - timedelta(days=7), datetime.min.time(), TZ)
    hi = datetime.combine(week_start + timedelta(days=7), datetime.min.time(), TZ)
    games = [g for g in games if lo <= datetime.fromisoformat(g["start"]) < hi]
    games.sort(key=lambda g: (g["start"], g["team"], g["sport"]))

    # If every source failed, keep the previous file rather than blanking the widget
    if not any(s["ok"] for s in sources.values()):
        print("All sources failed - leaving existing data untouched", file=sys.stderr)
        sys.exit(1)
    if os.path.exists(OUT_FILE):
        try:
            prev = json.load(open(OUT_FILE, encoding="utf-8"))
            for key, s in sources.items():
                if not s["ok"]:  # carry forward the last good data for a failed source
                    team_keys = {"spitfires": {"spitfires"}, "lancers": {"lancers"}}.get(key)
                    games += [g for g in prev.get("games", [])
                              if (g["team"] in team_keys if team_keys else g["id"].split("-")[1].startswith("sheet"))]
            games.sort(key=lambda g: (g["start"], g["team"], g["sport"]))
        except (ValueError, KeyError):
            pass

    payload = {
        "updated": now.isoformat(timespec="seconds"),
        "week_start": week_start.isoformat(),
        "teams": TEAMS,
        "sources": sources,
        "games": games,
    }
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    new = json.dumps(payload, ensure_ascii=False, indent=1)
    # Only rewrite when the games changed
    if os.path.exists(OUT_FILE):
        try:
            old = json.load(open(OUT_FILE, encoding="utf-8"))
            if old.get("games") == games and old.get("sources") == sources:
                print("No changes.")
                return
        except ValueError:
            pass
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"Wrote {len(games)} games to data/local-games.json")


if __name__ == "__main__":
    main()
