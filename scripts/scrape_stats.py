#!/usr/bin/env python3
"""
Powerplay Windsor - team leaders (player stats) collector.

Writes data/stats.json, which the Local Scoreboard's "Stats" tab reads.
Separate from scrape_local.py on purpose: if this script ever breaks, the
schedules and scores are not affected, and the Stats tab simply hides itself
until a good stats.json exists.

Sources (version 1: hockey)
  Windsor Spitfires    HockeyTech feed used by chl.ca (OHL)
  Leamington Flyers    HockeyTech feed used by ojhl.ca
  LaSalle Vipers       HockeyTech feed used by gohl.ca
  Chatham Maroons      HockeyTech feed used by gohl.ca
Not included yet: PJHL clubs (GameSheet), Lancers, Saints, high school.

Standard library only. Runs on GitHub Actions (.github/workflows/stats.yml).

Offline test:  python scripts/scrape_stats.py --fixtures fixtures-stats
  (reads <client>-skaters.json and <client>-goalies.json from that folder)
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

OUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "stats.json")
UA = "Mozilla/5.0 (compatible; PowerplayWindsorFeed/1.0; +https://www.powerplaywindsor.com)"

# ------------------------------------------------------------------ settings
# Same public keys and team numbers as scrape_local.py.
TEAMS = [
    # key used by the widget, club name, league label, HockeyTech client, api key, team id, "league stats" link
    ("spitfires", "Windsor Spitfires", "OHL", "ohl", "f1aa699db3d81487", 17,
     "https://chl.ca/ohl-spitfires/"),
    ("junior", "Leamington Flyers", "OJHL (Jr. A)", "ojhl", "77a0bd73d9d363d3", 19,
     "https://www.ojhl.ca/stats"),
    ("junior", "LaSalle Vipers", "GOHL (Jr. B)", "gojhl", "34b10d4d34d7b59a", 19,
     "https://www.gohl.ca/stats"),
    ("junior", "Chatham Maroons", "GOHL (Jr. B)", "gojhl", "34b10d4d34d7b59a", 20,
     "https://www.gohl.ca/stats"),
]
SKATERS_SHOWN = 5
GOALIES_SHOWN = 3
REQUEST_LIMIT = 500     # ask for plenty; we keep only this team's players
MAX_ROSTER_ROWS = 60    # a team-filtered list is about this size; anything bigger is league-wide

FIXTURES = None


# ------------------------------------------------------------------ helpers
def fetch(url, fixture=None):
    if FIXTURES and fixture:
        path = os.path.join(FIXTURES, fixture)
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, encoding="utf-8") as f:
            return f.read()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,*/*"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8-sig", errors="replace")


def parse_json(text):
    """HockeyTech sometimes wraps its JSON in parentheses or a callback; take the outermost {...} or [...]."""
    text = text.strip()
    try:
        return json.loads(text)
    except ValueError:
        pass
    m = re.search(r"[\{\[]", text)
    if not m:
        raise ValueError("no JSON found")
    end = max(text.rfind("}"), text.rfind("]"))
    return json.loads(text[m.start():end + 1])


def records(payload):
    """Find the list of player rows inside a modulekit response, whatever it's called."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    kit = payload.get("SiteKit", payload) if isinstance(payload, dict) else {}
    for key, val in kit.items():
        if key.lower() == "parameters":
            continue
        if isinstance(val, list) and val and isinstance(val[0], dict):
            return val
    return []


def pick(rec, *names):
    """First non-empty value among several possible field names."""
    for n in names:
        v = rec.get(n)
        if v not in (None, "", "-"):
            return v
    return None


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def whole(v):
    f = num(v)
    return None if f is None else int(f)


def player_name(rec):
    n = pick(rec, "name", "player_name", "full_name")
    if not n:
        n = " ".join(x for x in (pick(rec, "first_name"), pick(rec, "last_name")) if x)
    return " ".join(str(n).split()) if n else ""


def on_team(rec, team_id):
    """True/False when the row says which team it belongs to; None when it doesn't say."""
    for k in ("team_id", "teamId", "current_team_id"):
        if k in rec and rec[k] not in (None, ""):
            return str(rec[k]).strip() == str(team_id)
    return None


def team_rows(rows, team_id):
    flags = [on_team(r, team_id) for r in rows]
    if any(f is not None for f in flags):
        return [r for r, f in zip(rows, flags) if f]
    # Rows carry no team field. That is only safe when the feed already filtered to this team,
    # which gives a roster-sized list. A league-wide list here would put another club's players
    # under this club's name, so refuse it.
    if len(rows) > MAX_ROSTER_ROWS:
        raise RuntimeError(f"feed returned {len(rows)} rows with no team field, so they can't be matched to team {team_id}")
    return rows


def api_url(client, key, view_type, team_id):
    q = {
        "feed": "modulekit", "view": "statviewtype", "type": view_type,
        "key": key, "fmt": "json", "client_code": client, "lang": "en",
        "league_id": "", "season_id": "", "team_id": team_id,
        "first": 0, "limit": REQUEST_LIMIT,
    }
    return "https://lscluster.hockeytech.com/feed/?" + urllib.parse.urlencode(q)


# ------------------------------------------------------------------ one club
def skater_group(rows):
    out = []
    for r in rows:
        pts, g, a, gp = whole(pick(r, "points")), whole(pick(r, "goals")), whole(pick(r, "assists")), whole(pick(r, "games_played", "gp"))
        name = player_name(r)
        if not name or pts is None:
            continue
        out.append((name, [gp or 0, g or 0, a or 0, pts]))
    out.sort(key=lambda x: (-x[1][3], -x[1][1], x[0]))
    out = out[:SKATERS_SHOWN]
    if not out:
        return None
    return {"title": "Scoring leaders", "cols": ["GP", "G", "A", "PTS"], "key": 3,
            "rows": [{"name": n, "vals": v} for n, v in out]}


def save_pct(v):
    f = num(v)
    if f is None:
        return ""
    if f > 1:
        f = f / 100.0
    return ("%.3f" % f).lstrip("0")


def goalie_group(rows):
    out = []
    for r in rows:
        gp = whole(pick(r, "games_played", "gp"))
        name = player_name(r)
        if not name or not gp:
            continue
        w = whole(pick(r, "wins")) or 0
        gaa = num(pick(r, "goals_against_average", "gaa"))
        sv = pick(r, "save_percentage", "savepct", "sv_pct")
        out.append((name, w, gp, [gp, w, "" if gaa is None else "%.2f" % gaa, save_pct(sv)]))
    out.sort(key=lambda x: (-x[1], -x[2], x[0]))
    out = out[:GOALIES_SHOWN]
    if not out:
        return None
    return {"title": "Goalies", "cols": ["GP", "W", "GAA", "SV%"], "key": 1,
            "rows": [{"name": n, "vals": v} for n, _, _, v in out]}


def scrape_club(entry, now):
    team, club, league, client, key, team_id, link = entry
    groups = []
    # skaters are required; goalies are a bonus
    sk = parse_json(fetch(api_url(client, key, "topscorers", team_id), f"{client}-skaters.json"))
    rows = team_rows(records(sk), team_id)
    g = skater_group(rows)
    if not g:
        raise RuntimeError(f"no skater rows for team {team_id} (feed returned {len(records(sk))} rows; "
                           f"first row keys: {sorted(records(sk)[0].keys()) if records(sk) else 'none'})")
    groups.append(g)
    try:
        go = parse_json(fetch(api_url(client, key, "topgoalies", team_id), f"{client}-goalies.json"))
        gg = goalie_group(team_rows(records(go), team_id))
        if gg:
            groups.append(gg)
    except Exception as ex:      # goalies are optional
        print(f"  {club}: goalies skipped - {ex}", file=sys.stderr)
    return {"team": team, "club": club, "league": league, "link": link,
            "updated": now.isoformat(), "groups": groups}


# ------------------------------------------------------------------ main
def load_previous_file():
    try:
        with open(OUT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_previous():
    return {(t["team"], t["club"]): t for t in load_previous_file().get("teams", [])}


def without_times(teams):
    """The teams with their 'updated' stamps removed, so an unchanged table doesn't count as a change."""
    return [{k: v for k, v in t.items() if k != "updated"} for t in teams]


def main():
    global FIXTURES
    if "--fixtures" in sys.argv:
        FIXTURES = sys.argv[sys.argv.index("--fixtures") + 1]
    now = datetime.now(timezone.utc)
    previous, teams, failed = load_previous(), [], []
    for entry in TEAMS:
        club = entry[1]
        try:
            teams.append(scrape_club(entry, now))
            print(f"  {club}: ok")
        except Exception as ex:
            failed.append(club)
            print(f"::warning::Stats for {club} failed: {ex}")
            old = previous.get((entry[0], club))
            if old:                       # keep the last good numbers rather than dropping the club
                teams.append(old)
    if not teams:
        print("::warning::No stats collected; leaving data/stats.json as it was.")
        return 0
    if without_times(teams) == without_times(load_previous_file().get("teams", [])):
        print("Stats unchanged; not rewriting data/stats.json.")
        return 0
    out = {"updated": now.isoformat(), "teams": teams}
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"Wrote {len(teams)} clubs" + (f"; failed this run: {', '.join(failed)}" if failed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
