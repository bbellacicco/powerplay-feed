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
import re
import urllib.error
import urllib.request
from html import unescape
from html.parser import HTMLParser
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# ------------------------------------------------------------------ settings
# Edit these in GitHub's web editor if anything needs to change.

# Runs every morning. Keeps a 7-day span centred on the day it runs:
# 3 days before, today, and 3 days after.
DAYS_EACH_SIDE = 3
DAYS_BACK = DAYS_EACH_SIDE + 1    # a little extra room in the HockeyTech request
DAYS_AHEAD = DAYS_EACH_SIDE + 1

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
    "junior": {"name": "Junior Hockey", "short": "Junior Hockey", "league": "OJHL / GOHL / PJHL"},
    "highschool": {"name": "High School (WECSSAA)", "short": "High School", "league": "WECSSAA"},
}

OUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "local-games.json")
TZ = ZoneInfo("America/Toronto")
UA = "PowerplayWindsorFeed/1.0 (+https://www.powerplaywindsor.com)"

# ------------------------------------------------------------------ helpers

FIXTURES = None  # set by --fixtures for offline testing


def fetch(url, fixture=None, allow_404=False):
    if FIXTURES and fixture:
        with open(os.path.join(FIXTURES, fixture), encoding="utf-8") as f:
            return f.read()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/csv,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8-sig", errors="replace")
    except urllib.error.HTTPError as e:
        # wecssaa.com serves its schedule pages with a 404 status even though
        # the page is fine, so read the body anyway
        if allow_404 and e.code == 404:
            return e.read().decode("utf-8", errors="replace")
        raise


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


def _hockeytech_games(client, key, team_id, team, sport, club="", gamecentre="", preseason=()):
    """Games for one team from a HockeyTech league feed (OHL, OJHL, GOHL...)."""
    url = ("https://lscluster.hockeytech.com/feed/?feed=modulekit&view=scorebar"
           f"&key={key}&client_code={client}&team_id={team_id}"
           f"&numberofdaysback={DAYS_BACK}&numberofdaysahead={DAYS_AHEAD}"
           "&season_id=&limit=500&lang_code=en&fmt=json")
    data = json.loads(fetch(url, "spitfires.json" if client == "ohl" else None))
    out = []
    for g in data["SiteKit"]["Scorebar"]:
        home = g["HomeID"] == str(team_id)
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
        season_note = "Preseason" if g.get("SeasonID") in preseason else ""
        venue = ", ".join(x for x in [g.get("venue_name"), g.get("venue_location")] if x)
        gm = game(
            team, sport, start, g.get("TimeTbd") == "1",
            "H" if home else "A",
            g["VisitorLongName"] if home else g["HomeLongName"],
            location=venue, status=status, our=our, opp=opp, result=result,
            note=" · ".join(x for x in [note, season_note] if x),
            links={
                "tickets": g.get("TicketUrl") if status == "upcoming" else "",
                "gamecentre": gamecentre.format(id=g["ID"]) if gamecentre else "",
            },
            gid=f"{client}{g['ID']}",
        )
        if club:
            gm["club"] = club
        out.append(gm)
    return out


def scrape_spitfires():
    return _hockeytech_games("ohl", OHL_KEY, SPITFIRES_TEAM_ID, "spitfires", "Hockey",
                             gamecentre="https://chl.ca/ohl-spitfires/gamecentre/{id}/",
                             preseason=("87",))

# ------------------------------------------------------------------ Junior hockey

# Public keys are the ones each league's own website uses.
JUNIOR_TEAMS = [
    # (short name, league label, source, settings)
    ("Leamington Flyers", "OJHL (Jr. A)", "hockeytech",
     {"client": "ojhl", "key": "77a0bd73d9d363d3", "team_id": 19,
      "gamecentre": "https://www.ojhl.ca/stats/game-center/{id}"}),
    ("LaSalle Vipers", "GOHL (Jr. B)", "hockeytech",
     {"client": "gojhl", "key": "34b10d4d34d7b59a", "team_id": 19,
      "gamecentre": "https://www.gohl.ca/stats/game-center/{id}"}),
    ("Chatham Maroons", "GOHL (Jr. B)", "hockeytech",
     {"client": "gojhl", "key": "34b10d4d34d7b59a", "team_id": 20,
      "gamecentre": "https://www.gohl.ca/stats/game-center/{id}"}),
    # PJHL moved its stats to GameSheet. Season 15133 = 2026-27; update each fall
    # (it's the number in the "Schedule" link on thepjhl.ca).
    ("Lakeshore Canadiens", "PJHL (Jr. C)", "gamesheet", {"season": 15133, "team_id": 522354}),
    ("Essex 73's", "PJHL (Jr. C)", "gamesheet", {"season": 15133, "team_id": 522353}),
    ("Wheatley Sharks", "PJHL (Jr. C)", "gamesheet", {"season": 15133, "team_id": 522357}),
    ("Amherstburg Admirals", "PJHL (Jr. C)", "gamesheet", {"season": 15133, "team_id": 522350}),
]


def _next_payload_objects(html, marker='{"gameId":'):
    """GameSheet pages embed their data as Next.js 'self.__next_f.push' strings.
    Join those strings back together and pull out every JSON object that
    starts with `marker`."""
    parts = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', html)
    blob = "".join(json.loads(p) for p in parts)
    dec, out, i = json.JSONDecoder(), [], 0
    while True:
        i = blob.find(marker, i)
        if i < 0:
            return out
        try:
            obj, end = dec.raw_decode(blob, i)
            out.append(obj)
            i = end
        except ValueError:
            i += len(marker)


def _gamesheet_games(season, team_id, club, sport, now):
    url = f"https://gamesheetstats.com/seasons/{season}/teams/{team_id}/schedule?configuration=45"
    html = fetch(url, f"pjhl_{team_id}.html" if FIXTURES else None)
    out, seen = [], set()
    for g in _next_payload_objects(html):
        if g.get("gameId") in seen or not isinstance(g.get("home"), dict):
            continue
        seen.add(g["gameId"])
        home = g["home"].get("id") == team_id
        us, them = (g["home"], g["visitor"]) if home else (g["visitor"], g["home"])
        try:
            start = datetime.fromisoformat(g["timeStampZulu"].replace("Z", "+00:00")).astimezone(TZ)
        except (KeyError, ValueError):
            continue
        st = g.get("status", "")
        status, our, opp, result, note = "upcoming", None, None, None, ""
        if st == "final":
            status, our, opp = "final", to_int(us.get("goals")), to_int(them.get("goals"))
            result = {"W": "W", "L": "L", "T": "T", "OTL": "OTL", "SOL": "SOL"}.get(us.get("result"))
            if result is None and our is not None and opp is not None:
                result = "W" if our > opp else "L" if our < opp else "T"
        elif st == "in_progress":
            if now - start > timedelta(hours=4):
                note = "Score not posted yet"
            else:
                status, our, opp = "live", to_int(us.get("goals")), to_int(them.get("goals"))
        elif "postpon" in st:
            status = "postponed"
        elif "cancel" in st:
            status = "cancelled"
        if g.get("gameType") == "exhibition":
            note = " · ".join(x for x in [note, "Exhibition"] if x)
        gm = game("junior", sport, start, False, "H" if home else "A",
                  them.get("title", "TBA"), location=g.get("location", ""), status=status,
                  our=our, opp=opp, result=result, note=note,
                  links={"gamecentre": f"https://gamesheetstats.com/seasons/{season}/games/{g['gameId']}?configuration=45"},
                  gid=f"gs{g['gameId']}")
        gm["club"] = club
        out.append(gm)
    return out


def scrape_junior(now):
    out, errors = [], []
    for club, league, source, cfg in JUNIOR_TEAMS:
        try:
            if source == "hockeytech":
                if FIXTURES:
                    continue  # no offline sample for these leagues
                out += _hockeytech_games(cfg["client"], cfg["key"], cfg["team_id"], "junior",
                                         league, club=club, gamecentre=cfg.get("gamecentre", ""))
            else:
                if FIXTURES and cfg["team_id"] != 522350:
                    continue
                out += _gamesheet_games(cfg["season"], cfg["team_id"], club, league, now)
        except Exception as ex:
            errors.append(f"{club}: {ex}")
            print(f"  junior: {club} FAILED - {ex}", file=sys.stderr)
    if errors and not out:
        raise RuntimeError("; ".join(errors)[:200])
    # a game between two of our teams shows up twice; keep one copy
    uniq = {}
    for g in out:
        k = (g["start"], frozenset([g["club"], g["opponent"]]))
        if k not in uniq or g["home_away"] == "H":
            uniq[k] = g
    return list(uniq.values())

# ------------------------------------------------------------------ Lancers


def scrape_lancers(today):
    base = "https://golancers.ca"
    seen, out = set(), []
    # month view covers a 6-week grid; ask for each month the window touches
    months, d = [], (today - timedelta(days=DAYS_EACH_SIDE)).replace(day=1)
    while d <= today + timedelta(days=DAYS_EACH_SIDE):
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

# ------------------------------------------------------------------ High school (WECSSAA)


class _WecssaaParser(HTMLParser):
    """Turns wecssaa.com's weekly schedule table into a list of table rows,
    each a list of (tag, text) cells, keeping <h3> dates and league headers."""

    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell, self.tag = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell, self.tag = [], tag
        elif tag == "h3" and self.cell is not None:
            self.tag = "h3"

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append((self.tag, " ".join("".join(self.cell).split())))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_entityref(self, name):
        self.handle_data(unescape(f"&{name};"))

    def handle_charref(self, name):
        self.handle_data(unescape(f"&#{name};"))


def _hs_sport(league):
    """'Junior Girls Basketball-Tier 1' -> ('Junior Girls Basketball', 'Tier 1')
       '2A Senior Boys Football'        -> ('Senior Boys Football', '2A')"""
    league = " ".join(league.split())
    m = re.search(r"\b(Junior|Senior|Varsity)\s+(Boys|Girls|Co-Ed)\s+([A-Za-z]+)", league)
    if not m:
        return league, ""
    extra = " ".join(x.strip(" -") for x in (league[:m.start()], league[m.end():]) if x.strip(" -"))
    return m.group(0), extra


def scrape_wecssaa(today):
    """Every WECSSAA league, from the site's weekly (Sunday-Saturday) schedule."""
    base = "https://wecssaa.com"
    weeks = sorted({today - timedelta(days=DAYS_EACH_SIDE), today + timedelta(days=DAYS_EACH_SIDE)})
    out, seen = [], set()
    for i, day in enumerate(weeks):
        url = f"{base}/weeklySchedule.php?schoolid=ALL&date={day.isoformat()}&leagueid=ALL&divisionid=ALL"
        fixture = ["wecssaa_2026-09-25.html", "wecssaa_2026-09-29.html"][min(i, 1)]
        p = _WecssaaParser()
        p.feed(fetch(url, fixture, allow_404=True))
        date = league = visitor = pending = None
        for row in p.rows:
            first_tag, first = row[0]
            if first_tag == "h3" or re.match(r"^(Sun|Mon|Tues|Wednes|Thurs|Fri|Satur)day, \w+ \d+, \d{4}$", first):
                try:
                    date = datetime.strptime(first, "%A, %B %d, %Y").date()
                except ValueError:
                    pass
                continue
            if first_tag == "th" and len(row) == 1 and first:
                league = first
                continue
            if first == "Visitor:" and len(row) >= 3:
                visitor = row
                continue
            if first == "Home:" and visitor and len(row) >= 2:
                visitor, pending = None, (visitor, row)
                continue
            if first.startswith("Location:") and date and league and pending:
                v, h = pending
                pending = None
                notes = row[1][1][len("Notes:"):].strip() if len(row) > 1 and row[1][1].startswith("Notes:") else ""
                location = first[len("Location:"):].replace("Map", "").strip()
                v_name, h_name = v[1][1], h[1][1]
                v_cell = v[2][1] if len(v) > 2 else ""
                h_cell = h[2][1] if len(h) > 2 else ""
                vs, hs = to_int(v_cell), to_int(h_cell)
                start, tbd = datetime.combine(date, datetime.min.time()), True
                for fmt in ("%I:%M %p", "%I:%M%p"):
                    try:
                        tt = datetime.strptime(v_cell.upper(), fmt)
                        start, tbd = start.replace(hour=tt.hour, minute=tt.minute), False
                        break
                    except ValueError:
                        pass
                start = start.replace(tzinfo=TZ)
                status = "final" if vs is not None and hs is not None else "upcoming"
                low = notes.lower()
                if "postpon" in low:
                    status = "postponed"
                elif "cancel" in low:
                    status = "cancelled"
                sport, level = _hs_sport(league)
                key = (date, league, v_name, h_name, v_cell)
                if key in seen:
                    continue
                seen.add(key)
                g = game("highschool", sport, start, tbd, "N", h_name, location=location,
                         status=status, our=vs if status == "final" else None,
                         opp=hs if status == "final" else None,
                         note=" · ".join(x for x in [level, notes.rstrip(".")] if x
                                         and x.lower() != "regular season"),
                         links={"standings": f"{base}/viewScores.php"},
                         gid=f"{date.isoformat()}-{len(out)}")
                g["away"], g["home"] = v_name, h_name   # neutral matchup, no "our" team
                out.append(g)
    return out

# ------------------------------------------------------------------ St. Clair Saints football (CJFL)

# St. Clair's own site blocks automated tools, but the CJFL site (cjfl.org)
# carries the Saints football schedule. Any season's schedule page works as a
# starting point: the script reads its season menu and follows the newest year.
CJFL_START = "https://www.cjfl.org/schedule/team_instance/10466301?subseason=958344"


def _strip_tags(html):
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", html)).split())


def _cjfl_rows(html, year, today):
    out = []
    for gid, row in re.findall(r'<tr id="game_list_row_(\d+)"[^>]*>(.*?)</tr>', html, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 5:
            continue
        date_txt, result_txt, opp_txt, loc_txt = (_strip_tags(c) for c in cells[:4])
        status_html = cells[4]
        try:
            day = datetime.strptime(f"{date_txt} {year}", "%a %b %d %Y")
        except ValueError:
            continue
        opp_txt = opp_txt.strip()
        away = opp_txt.startswith("@")
        opponent = opp_txt.lstrip("@ ").strip() or "TBA"
        status_txt = _strip_tags(status_html)
        alt = " ".join(re.findall(r'alt="([^"]*)"', status_html)).upper()
        start, tbd = day, True
        m = re.search(r"(\d{1,2}:\d{2}\s*[AP]M)", status_txt, re.I)
        if m:
            tt = datetime.strptime(m.group(1).upper().replace(" ", ""), "%I:%M%p")
            start, tbd = day.replace(hour=tt.hour, minute=tt.minute), False
        start = start.replace(tzinfo=TZ)
        status, our, opp, result = "upcoming", None, None, None
        sm = re.match(r"^([WLT])\s+(\d+)\s*-\s*(\d+)", result_txt)
        if sm:
            status, result = "final", sm.group(1)
            our, opp = int(sm.group(2)), int(sm.group(3))
        low = (status_txt + " " + alt).lower()
        if "postpon" in low:
            status = "postponed"
        elif "cancel" in low:
            status = "cancelled"
        out.append(game("saints", "Football", start, tbd, "A" if away else "H", opponent,
                        location=loc_txt, status=status, our=our, opp=opp, result=result,
                        note="CJFL",
                        links={"gamecentre": f"https://www.cjfl.org/game/show/{gid}"},
                        gid=f"cjfl{gid}"))
    return out


def scrape_cjfl_saints(today):
    first = fetch(CJFL_START, "cjfl.html" if FIXTURES else None)
    # season menu: <optgroup label="2026"> <option value="/schedule/...">...</option>
    groups = re.findall(r'<optgroup label="(\d{4})\*?">(.*?)</optgroup>', first, re.S)
    pages = []
    if groups:
        year, body = max(groups, key=lambda g: int(g[0]))
        pages = [(int(year), "https://www.cjfl.org" + unescape(v))
                 for v in re.findall(r'<option value="([^"]+)"', body)]
    if not pages:
        pages = [(today.year, CJFL_START)]
    out = []
    for year, url in pages:
        html = first if (FIXTURES or url == CJFL_START) else fetch(url)
        out += _cjfl_rows(html, year, today)
        if FIXTURES:
            break
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

    games, sources = [], {}
    for key, fn in (("spitfires", scrape_spitfires),
                    ("lancers", lambda: scrape_lancers(today)),
                    ("junior", lambda: scrape_junior(now)),
                    ("saints", lambda: scrape_cjfl_saints(today)),
                    ("highschool", lambda: scrape_wecssaa(today)),
                    ("sheet", scrape_manual_sheet)):
        try:
            got = fn()
            games += got
            sources[key] = {"ok": True, "count": len(got)}
            print(f"{key}: {len(got)} games")
        except Exception as ex:  # one source failing shouldn't kill the rest
            sources[key] = {"ok": False, "error": str(ex)[:200]}
            print(f"{key}: FAILED - {ex}", file=sys.stderr)


    # If every source failed, keep the previous file rather than blanking the widget
    if not any(s["ok"] for s in sources.values()):
        print("All sources failed - leaving existing data untouched", file=sys.stderr)
        sys.exit(1)
    if os.path.exists(OUT_FILE):
        try:
            prev = json.load(open(OUT_FILE, encoding="utf-8"))
            for key, s in sources.items():
                if not s["ok"]:  # carry forward the last good data for a failed source
                    team_keys = {"spitfires": {"spitfires"}, "lancers": {"lancers"},
                                 "highschool": {"highschool"}, "junior": {"junior"},
                                 "saints": {"saints"}}.get(key)
                    games += [g for g in prev.get("games", [])
                              if (g["team"] in team_keys if team_keys else g["id"].split("-")[1].startswith("sheet"))]
        except (ValueError, KeyError):
            pass

    lo = datetime.combine(today - timedelta(days=DAYS_EACH_SIDE), datetime.min.time(), TZ)
    hi = datetime.combine(today + timedelta(days=DAYS_EACH_SIDE + 1), datetime.min.time(), TZ)
    games = [g for g in games if lo <= datetime.fromisoformat(g["start"]) < hi]
    games.sort(key=lambda g: (g["start"], g["team"], g["sport"]))

    payload = {
        "updated": now.isoformat(timespec="seconds"),
        "today": today.isoformat(),
        "range": [(today - timedelta(days=DAYS_EACH_SIDE)).isoformat(),
                  (today + timedelta(days=DAYS_EACH_SIDE)).isoformat()],
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
            if old.get("games") == games and old.get("sources") == sources and old.get("today") == payload["today"]:
                print("No changes.")
                return
        except ValueError:
            pass
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"Wrote {len(games)} games to data/local-games.json")


if __name__ == "__main__":
    main()
