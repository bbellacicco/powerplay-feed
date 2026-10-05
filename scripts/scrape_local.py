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
import time
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
UA = "Mozilla/5.0 (compatible; PowerplayWindsorFeed/1.0; +https://www.powerplaywindsor.com)"

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


CJFL_STANDINGS = "https://www.cjfl.org/standings/show/9362372?subseason=958344"


def _cjfl_standings():
    """CJFL Ontario Conference standings (St. Clair's conference)."""
    html = fetch(CJFL_STANDINGS, "cjfl_standings.html" if FIXTURES else None)
    groups = []
    for m in re.finditer(r'<table class="statTable">(.*?)</table>', html, re.S):
        tbl = m.group(1)
        before = html[max(0, m.start() - 4000):m.start()]
        heads = re.findall(r"<h3[^>]*>(.*?)</h3>", before, re.S)
        title = re.sub(r"\s*-\s*\d{4}.*$", "", _strip_tags(heads[-1])) if heads else ""
        if "conference" not in title.lower():
            title = "Ontario Conference"
        cols = [_strip_tags(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", tbl.split("</thead>")[0], re.S)]
        cols = [c for c in cols if c and c != "Team"]
        teams = []
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", tbl.split("</thead>")[-1], re.S):
            name = re.search(r'class="teamName"[^>]*>(.*?)</a>', row, re.S)
            cells = [_strip_tags(c) for c in re.findall(r"<td(?![^>]*\bname\b)[^>]*>(.*?)</td>", row, re.S)]
            if name and cells:
                teams.append({"name": _strip_tags(name.group(1)), "stats": cells[:len(cols)]})
        if teams:
            groups.append({"group": "CJFL " + title, "cols": cols, "teams": teams})
    return groups


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

# ------------------------------------------------------------------ CFL (for the pro widget)

# ESPN's CFL data is out of date, so CFL comes from cfl.ca's own schedule page.
# The pro widget gets NFL / NHL / NBA live from ESPN in the browser.


def _nuxt_value(arr, i, depth=0):
    """Nuxt pages store data as one flat list where objects point to other
    positions in the list. Follow the pointers for one value."""
    if not isinstance(i, int) or isinstance(i, bool) or depth > 8 or i < 0 or i >= len(arr):
        return i
    v = arr[i]
    if isinstance(v, list):
        if v and isinstance(v[0], str) and v[0] in ("Reactive", "ShallowReactive", "Ref", "ShallowRef", "Date"):
            return v[1] if v[0] == "Date" else _nuxt_value(arr, v[1], depth + 1)
        return [_nuxt_value(arr, x, depth + 1) for x in v]
    if isinstance(v, dict):
        return {k: _nuxt_value(arr, x, depth + 1) for k, x in v.items()}
    return v


def scrape_cfl(today):
    html = fetch("https://www.cfl.ca/schedule/", "cfl.html" if FIXTURES else None)
    m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("cfl.ca schedule data not found")
    arr = json.loads(m.group(1))
    teams, venues, games = {}, {}, []
    for v in arr:
        if not isinstance(v, dict) or "ID" not in v:
            continue
        if "abbreviation" in v and "region_label" in v:
            t = {k: _nuxt_value(arr, v[k]) for k in ("ID", "abbreviation", "region_label", "name")}
            region = str(t["region_label"]).title().replace("B.c.", "B.C.")
            teams[t["ID"]] = {"abbr": t["abbreviation"], "name": f"{region} {t['name']}".strip()}
        elif "capacity" in v and "name" in v:
            venues[_nuxt_value(arr, v["ID"])] = _nuxt_value(arr, v["name"])
        elif "home_team_id" in v:
            games.append({k: _nuxt_value(arr, x) for k, x in v.items()
                          if k not in ("contentfulMatch", "metadata", "genius")})
    out = []
    for g in games:
        h, a = teams.get(g.get("home_team_id")), teams.get(g.get("away_team_id"))
        if not h or not a or not g.get("start_at"):
            continue
        start = datetime.fromisoformat(str(g["start_at"])).astimezone(TZ)
        hs, as_ = to_int(g.get("home_team_score")), to_int(g.get("away_team_score"))
        st = str(g.get("game_status") or "").lower()
        status = "upcoming"
        if st in ("finished", "final", "complete", "completed") or (hs is not None and as_ is not None and start < datetime.now(TZ) - timedelta(hours=4)):
            status = "final"
        elif st in ("in progress", "live", "in_progress"):
            status = "live"
        elif "postpon" in st:
            status = "postponed"
        elif "cancel" in st:
            status = "cancelled"
        gm = game("cfl", "CFL", start, False, "N", h["name"], location=venues.get(g.get("venue_id"), ""),
                  status=status,
                  our=as_ if status in ("final", "live") else None,
                  opp=hs if status in ("final", "live") else None,
                  note="Preseason" if to_int(g.get("week")) is not None and to_int(g.get("week")) < 1 else "",
                  links={"gamecentre": "https://www.cfl.ca/schedule/"},
                  gid=f"cfl{g.get('ID')}")
        gm["away"], gm["home"] = a["name"], h["name"]
        gm["away_abbr"], gm["home_abbr"] = a["abbr"], h["abbr"]
        out.append(gm)
    return out

def _iso_date(val):
    """cfl.ca mixes date strings and millisecond timestamps; return ISO text."""
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return datetime.fromtimestamp(val / 1000, TZ).isoformat(timespec="seconds")
    try:
        return datetime.fromisoformat(str(val)).astimezone(TZ).isoformat(timespec="seconds")
    except ValueError:
        return ""


# ------------------------------------------------------------------ Standings
# HockeyTech leagues (same public keys the leagues' own sites use)
STANDINGS_LEAGUES = {
    "ohl": ("ohl", OHL_KEY),
    "ojhl": ("ojhl", "77a0bd73d9d363d3"),
    "gohl": ("gojhl", "34b10d4d34d7b59a"),
    "pwhl": ("pwhl", "446521baf8c38984"),
}


def _streak(v):
    """Turn '2-0-0-0' (HockeyTech) or 'Won 6' (GameSheet) into 'W2' / 'W6'."""
    v = (v or "").strip()
    m = re.fullmatch(r"(\d+)-(\d+)-(\d+)-(\d+)", v)
    if m:
        for n, tag in zip(m.groups(), ("W", "L", "OTL", "SOL")):
            if int(n):
                return f"{tag}{n}"
        return ""
    m = re.fullmatch(r"(Won|Lost|Tied|W|L|T)\s*(\d+)", v, re.I)
    if m:
        return m.group(1)[0].upper() + m.group(2)
    return v


def _hockeytech_standings(client, key):
    url = ("https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=teams&groupTeamsBy=division"
           f"&context=overall&site_id=0&season=&special=false&key={key}&client_code={client}&league_code=&lang=en&fmt=json")
    raw = fetch(url, f"standings_{client}.json" if FIXTURES else None).strip()
    if raw.startswith("(") and raw.endswith(")"):
        raw = raw[1:-1]
    groups = []
    for sec in json.loads(raw)[0]["sections"]:
        title = (((sec.get("headers") or {}).get("name") or {}).get("properties") or {}).get("title") or ""
        teams = []
        for d in sec.get("data", []):
            r = d.get("row", {})
            otl = (to_int(r.get("ot_losses")) or 0) + (to_int(r.get("shootout_losses")) or 0)
            if client == "pwhl":        # PWHL: 3 pts regulation win, 2 OT/SO win, 1 OT/SO loss
                w = (to_int(r.get("regulation_wins")) or 0) + (to_int(r.get("non_reg_wins")) or 0)
                otl = to_int(r.get("non_reg_losses")) or 0
            else:
                w = to_int(r.get("wins"))
            teams.append({"name": r.get("name", ""), "abbr": r.get("team_code", ""),
                          "gp": to_int(r.get("games_played")), "w": w, "l": to_int(r.get("losses")),
                          "otl": otl, "pts": to_int(r.get("points")),
                          "gf": to_int(r.get("goals_for")), "ga": to_int(r.get("goals_against")),
                          "strk": _streak(r.get("streak") or r.get("streak_wl"))})
        if teams:
            groups.append({"group": title, "teams": teams})
    return groups


def _pjhl_standings(season):
    """PJHL (GameSheet): the division our Jr. C clubs play in (West - Stobbs).
    The league-wide standings page is behind a bot check, but each team's own
    standings page isn't. On a team's page that team's stats are a reference
    instead of numbers, so two clubs' pages are read and merged."""
    ours = [cfg["team_id"] for _, _, src, cfg in JUNIOR_TEAMS if src == "gamesheet"]
    rows = {}
    for n, tid in enumerate(ours[:2]):
        if n:
            time.sleep(2)
        html = fetch(f"https://gamesheetstats.com/seasons/{season}/teams/{tid}/standings?configuration=45",
                     "pjhl_team_standings.html" if FIXTURES else None)
        for o in _next_payload_objects(html, marker='{"division":'):
            if o.get("gameType") != "overall" or not isinstance(o.get("team"), dict):
                continue
            tm, st = o["team"], o.get("stats")
            key = (o["division"].get("title", ""), tm.get("id"))
            if not isinstance(st, dict):
                rows.setdefault(key, None)
                continue
            rows[key] = {"rank": o.get("rank") or 99, "name": tm.get("title", ""), "abbr": tm.get("abbreviation", ""),
                         "gp": st.get("GP"), "w": st.get("W"), "l": st.get("L"),
                         "otl": (st.get("OTL") or 0) + (st.get("SOL") or 0), "pts": st.get("PTS"),
                         "gf": st.get("GF"), "ga": st.get("GA"), "strk": _streak(st.get("STK"))}
        if FIXTURES:
            break
    divs = {}
    for (div, tid), r in rows.items():
        if r:
            divs.setdefault(div, []).append(r)
    out = []
    for title, teams in divs.items():
        teams.sort(key=lambda t: (t["rank"], -(t["pts"] or 0)))
        for t in teams:
            t.pop("rank", None)
        out.append({"group": "PJHL " + title.replace(" - ", " "), "teams": teams})
    return out


def scrape_standings():
    out, errors = {}, {}
    for name, (client, key) in STANDINGS_LEAGUES.items():
        try:
            out[name] = _hockeytech_standings(client, key)
        except Exception as ex:
            errors[name] = str(ex)[:200]
    try:
        season = next(cfg["season"] for _, _, src, cfg in JUNIOR_TEAMS if src == "gamesheet")
        out["pjhl"] = _pjhl_standings(season)
        if not out["pjhl"]:
            raise RuntimeError("no PJHL standings found on the team pages")
    except Exception as ex:
        errors["pjhl"] = str(ex)[:200]
    try:
        out["cjfl"] = _cjfl_standings()
    except Exception as ex:
        errors["cjfl"] = str(ex)[:200]
    return out, errors


def scrape_pwhl(today):
    """Every PWHL game from 3 days back to 3 days ahead, for the Pro Hub (ESPN doesn't carry the PWHL)."""
    client, key = STANDINGS_LEAGUES["pwhl"]
    url = ("https://lscluster.hockeytech.com/feed/?feed=modulekit&view=scorebar"
           f"&key={key}&client_code={client}&numberofdaysback={DAYS_BACK}&numberofdaysahead={DAYS_AHEAD}"
           "&season_id=&limit=500&lang_code=en&fmt=json")
    data = json.loads(fetch(url, "pwhl.json" if FIXTURES else None))
    out = []
    for g in data["SiteKit"]["Scorebar"]:
        start = datetime.fromisoformat(g["GameDateISO8601"]).astimezone(TZ)
        code, period = g.get("GameStatus"), to_int(g.get("Period")) or 0
        hg, vg = to_int(g["HomeGoals"]), to_int(g["VisitorGoals"])
        status, note = "upcoming", ""
        if code == "4":
            status = "final"
            note = "OT" if period == 4 else "SO" if period >= 5 else ""
        elif code in ("2", "3"):
            status, note = "live", g.get("GameStatusString", "")
        else:
            hg = vg = None
        low = (g.get("GameStatusString") or "").lower()
        if "postpon" in low:
            status = "postponed"
        out.append({"league": "pwhl", "start": start.isoformat(), "status": status,
                    "home": g["HomeLongName"], "away": g["VisitorLongName"],
                    "home_abbr": g.get("HomeCode", ""), "away_abbr": g.get("VisitorCode", ""),
                    "our_score": vg, "opp_score": hg,          # same layout as the CFL games: away, home
                    "location": g.get("venue_name", ""), "note": note, "time_tbd": g.get("TimeTbd") == "1",
                    "link": f"https://www.thepwhl.com/en/stats/game-center/{g['ID']}"})
    return out


CFL_NAMES = {"BC": "BC Lions", "CGY": "Calgary Stampeders", "EDM": "Edmonton Elks", "SSK": "Saskatchewan Roughriders",
             "WPG": "Winnipeg Blue Bombers", "HAM": "Hamilton Tiger-Cats", "TOR": "Toronto Argonauts",
             "OTT": "Ottawa Redblacks", "MTL": "Montreal Alouettes"}


def scrape_cfl_standings(today):
    """CFL standings from the league's stats site (ESPN's CFL standings are empty)."""
    j = json.loads(fetch(f"https://api.stats.cfl.ca/standings/{today.year}", "cfl_standings.json" if FIXTURES else None))
    out = []
    for key in ("west", "east"):
        rows = (((j.get("data") or {}).get("divisions") or {}).get(key) or {}).get("standings") or []
        teams = []
        for r in sorted(rows, key=lambda r: r.get("place_override") or r.get("place") or 99):
            ab = r.get("abbreviation", "")
            teams.append({"abbr": ab, "name": CFL_NAMES.get(ab, ab), "gp": r.get("games_played"), "w": r.get("wins"),
                          "l": r.get("losses"), "t": r.get("ties"), "pts": r.get("points"),
                          "pf": r.get("points_for"), "pa": r.get("points_against"), "flags": r.get("flags") or ""})
        if teams:
            out.append({"group": key.title() + " Division", "teams": teams})
    if not out:
        raise RuntimeError("no CFL standings in response")
    return out


def scrape_cfl_news(limit=30):
    """Latest stories from the cfl.ca home page (headline, short summary, photo, link)."""
    html = fetch("https://www.cfl.ca/", "cfl_home.html" if FIXTURES else None)
    m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("cfl.ca story data not found")
    arr = json.loads(m.group(1))
    out, seen = [], set()
    for v in arr:
        if not (isinstance(v, dict) and "headline" in v and "slug" in v and "isVideo" in v):
            continue
        slug = _nuxt_value(arr, v["slug"])
        if not slug or slug in seen:
            continue
        seen.add(slug)
        img = ""
        hero = _nuxt_value(arr, v.get("heroImage")) if "heroImage" in v else None
        if isinstance(hero, dict):
            url = ((hero.get("file") or {}).get("url") or "")
            if url:
                img = ("https:" + url if url.startswith("//") else url) + "?w=640&fm=jpg&q=70"
        teams = _nuxt_value(arr, v["relatedTeams"]) if "relatedTeams" in v else []
        summary = _nuxt_value(arr, v["summary"]) if "summary" in v else ""
        out.append({
            "league": "cfl",
            "headline": str(_nuxt_value(arr, v["headline"]) or "").strip(),
            "summary": str(summary or "").strip(),
            "published": _iso_date(_nuxt_value(arr, v["publishedDate"]) if "publishedDate" in v else ""),
            "image": img,
            "video": bool(_nuxt_value(arr, v["isVideo"])),
            "teams": [t.get("teamName") for t in teams if isinstance(t, dict)] if isinstance(teams, list) else [],
            "url": f"https://www.cfl.ca/article/{slug}",
            "source": "CFL.ca",
        })
    out.sort(key=lambda a: a["published"] or "", reverse=True)
    return out[:limit]


# ------------------------------------------------------------------ Sportsnet + club sites (Pro Feed)

# The Pro Feed's own teams: league, Sportsnet's abbreviation, full name
OUR_PRO = [("nhl", "DET", "Detroit Red Wings"), ("nhl", "TOR", "Toronto Maple Leafs"), ("nhl", "MTL", "Montreal Canadiens"),
           ("nba", "DET", "Detroit Pistons"), ("nba", "TOR", "Toronto Raptors"),
           ("nfl", "DET", "Detroit Lions"), ("nfl", "BUF", "Buffalo Bills"),
           ("mlb", "DET", "Detroit Tigers"), ("mlb", "TOR", "Toronto Blue Jays")]
# club sites: (league, team, kind, url)
CLUB_SITES = [
    ("nhl", "Detroit Red Wings", "nhl", "https://www.nhl.com/redwings/news/"),
    ("nhl", "Toronto Maple Leafs", "nhl", "https://www.nhl.com/mapleleafs/news/"),
    ("nhl", "Montreal Canadiens", "nhl", "https://www.nhl.com/canadiens/news/"),
    ("nfl", "Detroit Lions", "rss", "https://www.detroitlions.com/rss/news"),
    ("nfl", "Buffalo Bills", "rss", "https://www.buffalobills.com/rss/news"),
    ("mlb", "Detroit Tigers", "rss", "https://www.mlb.com/tigers/feeds/news/rss.xml"),
    ("mlb", "Toronto Blue Jays", "rss", "https://www.mlb.com/bluejays/feeds/news/rss.xml"),
]
SN_LEAGUES = {"NHL": "nhl", "NFL": "nfl", "NBA": "nba", "MLB": "mlb", "CFL": "cfl", "PWHL": "pwhl"}


def _rss_date(v):
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(v.strip()).astimezone(TZ).isoformat(timespec="minutes")
    except (TypeError, ValueError, IndexError):
        return ""


def _tag(block, name):
    m = re.search(rf"<{name}\b[^>]*>(.*?)</{name}>", block, re.S)
    if not m:
        return ""
    v = m.group(1).strip()
    v = re.sub(r"^<!\[CDATA\[(.*)\]\]>$", r"\1", v, flags=re.S)
    return unescape(v).strip()


def scrape_sportsnet(limit=40):
    """Sportsnet's main feed: articles only (no game cards, videos or collections)."""
    xml = fetch("https://www.sportsnet.ca/feed/", "sportsnet.xml" if FIXTURES else None)
    out = []
    for item in re.findall(r"<item\b.*?</item>", xml, re.S):
        url = _tag(item, "link")
        if "/article/" not in url:
            continue
        lg = SN_LEAGUES.get(_strip_tags(_tag(item, "leagues")).split(" ")[0] if _tag(item, "leagues") else "", "")
        abbrs = re.findall(r"<team\b[^>]*>([A-Z]{2,4})</team>", item)
        teams = [name for l, a, name in OUR_PRO if l == lg and a in abbrs]
        img = re.search(r'<media:content\b[^>]*\burl="([^"]+)"', item)
        out.append({"league": lg or "other", "headline": _strip_tags(_tag(item, "title")),
                    "summary": _strip_tags(_tag(item, "description"))[:220],
                    "published": _rss_date(_tag(item, "pubDate")), "image": img.group(1) if img else "",
                    "video": False, "teams": teams, "sn_team_count": len(abbrs), "sport": _strip_tags(_tag(item, "sports")),
                    "url": url, "source": "Sportsnet"})
    return out[:limit]


def _club_rss(league, team, url):
    xml = fetch(url)
    out = []
    for item in re.findall(r"<item\b.*?</item>", xml, re.S)[:15]:
        img = re.search(r'<media:(?:content|thumbnail)\b[^>]*\burl="([^"]+)"', item) or re.search(r'<image\b[^>]*\bhref="([^"]+)"', item)
        out.append({"league": league, "headline": _strip_tags(_tag(item, "title")),
                    "summary": _strip_tags(_tag(item, "description"))[:220],
                    "published": _rss_date(_tag(item, "pubDate")), "image": img.group(1) if img else "",
                    "video": False, "teams": [team], "url": _tag(item, "link"), "source": "Team site"})
    return out


def _club_nhl(league, team, url):
    html = fetch(url)
    out, seen = [], set()
    for m in re.finditer(r'<a class="nhl-c-card-wrap -story" href="([^"]+)".*?</a>', html, re.S):
        href, card = m.group(1), m.group(0)
        if href in seen:
            continue
        seen.add(href)
        title = re.search(r'<h3 class="fa-text__title">(.*?)</h3>', card, re.S)
        when = re.search(r'<time datetime="([0-9T:\-]+)"', card)
        img = re.search(r'<img[^>]*\bsrc="(https://media\.d3\.nhle\.com/[^"]+)"', card)
        published = ""
        if when:
            published = datetime.fromisoformat(when.group(1)).replace(tzinfo=timezone.utc).astimezone(TZ).isoformat(timespec="minutes")
        out.append({"league": league, "headline": _strip_tags(title.group(1)) if title else "", "summary": "",
                    "published": published, "image": img.group(1) if img else "", "video": False,
                    "teams": [team], "url": "https://www.nhl.com" + href if href.startswith("/") else href, "source": "Team site"})
        if len(out) >= 15:
            break
    return out


def scrape_club_news():
    """Official team sites for the Pro Feed's Our Teams. One failing site doesn't stop the rest."""
    out, errors = [], {}
    for league, team, kind, url in CLUB_SITES:
        try:
            out += (_club_nhl if kind == "nhl" else _club_rss)(league, team, url)
        except Exception as ex:
            errors[team] = str(ex)[:120]
        time.sleep(1)
    return [s for s in out if s["headline"] and s["url"]], errors


def _pwhl_title(t):
    t = unescape(t).strip()
    if t.isupper():                  # the PWHL writes headlines in capitals
        t = re.sub(r"[A-Za-z]+('[A-Za-z]+)?", lambda m: m.group(0).capitalize() if len(m.group(0)) > 3 or m.start() == 0
                   else m.group(0).lower() if m.group(0).lower() in ("and", "to", "for", "of", "the", "at", "in", "on", "a", "an", "vs")
                   else m.group(0).capitalize(), t.lower())
    t = re.sub(r"\b(Pwhl|Nhl|Ncaa|Usa|Ot)\b", lambda m: m.group(0).upper(), t)
    t = re.sub(r"\b(O|Mc|D)'([a-z])", lambda m: m.group(1) + "'" + m.group(2).upper(), t)   # O'Brien
    return t


def scrape_pwhl_news(limit=30):
    """Latest stories from thepwhl.com's news page (league and team stories)."""
    html = fetch("https://www.thepwhl.com/en/news", "pwhl_news.html" if FIXTURES else None)
    months = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                          "august", "september", "october", "november", "december"], 1)}
    out, seen = [], set()
    for m in re.finditer(r'<a[^>]+href="(/en/(?:teams/([a-z0-9-]+)/)?news/(\d{4})/([a-z]+)/(\d{1,2})/([a-z0-9-]+))"[^>]*>(.*?)</a>', html, re.S):
        path, team, y, mon, d, slug, body = m.groups()
        if path in seen or mon not in months:
            continue
        seen.add(path)
        h = re.search(r"<h[1-4][^>]*>(.*?)</h[1-4]>", body, re.S)
        title = _pwhl_title(re.sub(r"<[^>]+>", "", h.group(1)) if h else slug.replace("-", " ").upper())
        # cloudinary urls contain commas, so take the first srcset entry up to whitespace
        src = re.search(r'srcSet="\s*(https://res\.cloudinary\.com/\S+?),?\s', body)
        img = src
        t = re.search(r'dateTime="([^"]+)"', body)
        published = t.group(1).replace("Z", "+00:00") if t else f"{y}-{months[mon]:02d}-{int(d):02d}T12:00:00+00:00"
        out.append({"league": "pwhl", "headline": title, "summary": "", "published": published,
                    "image": img.group(1) if img else "", "video": False,
                    "teams": [team.replace("-", " ").title()] if team else [],
                    "url": "https://www.thepwhl.com" + path, "source": "thepwhl.com"})
    out.sort(key=lambda a: a["published"], reverse=True)
    return out[:limit]

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

    pro_games = []
    try:
        pro_games = [g for g in scrape_cfl(today)
                     if lo <= datetime.fromisoformat(g["start"]) < hi]
        sources["cfl"] = {"ok": True, "count": len(pro_games)}
        print(f"cfl: {len(pro_games)} games")
    except Exception as ex:
        sources["cfl"] = {"ok": False, "error": str(ex)[:200]}
        print(f"cfl: FAILED - {ex}", file=sys.stderr)
        try:
            pro_games = json.load(open(OUT_FILE, encoding="utf-8")).get("pro_games", [])
        except (OSError, ValueError):
            pass

    pro_news = []
    try:
        pro_news = scrape_cfl_news()
        sources["cfl_news"] = {"ok": True, "count": len(pro_news)}
        print(f"cfl news: {len(pro_news)} stories")
    except Exception as ex:
        sources["cfl_news"] = {"ok": False, "error": str(ex)[:200]}
        print(f"cfl news: FAILED - {ex}", file=sys.stderr)
        try:
            pro_news = json.load(open(OUT_FILE, encoding="utf-8")).get("pro_news", [])
        except (OSError, ValueError):
            pass

    standings, st_err = scrape_standings()
    for k in ("ohl", "ojhl", "gohl", "pjhl", "pwhl", "cjfl"):
        if k in st_err:
            sources["standings_" + k] = {"ok": False, "error": st_err[k]}
            print(f"standings {k}: FAILED - {st_err[k]}", file=sys.stderr)
        else:
            sources["standings_" + k] = {"ok": True, "count": sum(len(g["teams"]) for g in standings.get(k, []))}
    if st_err:     # keep the last good copy of anything that failed
        try:
            old_st = json.load(open(OUT_FILE, encoding="utf-8")).get("standings", {})
            for k in st_err:
                if k in old_st:
                    standings[k] = old_st[k]
        except (OSError, ValueError):
            pass
    try:
        pwhl = [g for g in scrape_pwhl(today) if lo <= datetime.fromisoformat(g["start"]) < hi]
        pro_games = pro_games + pwhl
        sources["pwhl"] = {"ok": True, "count": len(pwhl)}
        print(f"pwhl: {len(pwhl)} games")
    except Exception as ex:
        sources["pwhl"] = {"ok": False, "error": str(ex)[:200]}
        print(f"pwhl: FAILED - {ex}", file=sys.stderr)

    cfl_standings = []
    try:
        cfl_standings = scrape_cfl_standings(today)
        sources["cfl_standings"] = {"ok": True, "count": sum(len(d["teams"]) for d in cfl_standings)}
        print(f"cfl standings: {len(cfl_standings)} divisions")
    except Exception as ex:
        sources["cfl_standings"] = {"ok": False, "error": str(ex)[:200]}
        print(f"cfl standings: FAILED - {ex}", file=sys.stderr)
        try:
            cfl_standings = json.load(open(OUT_FILE, encoding="utf-8")).get("cfl_standings", [])
        except (OSError, ValueError):
            pass

    try:
        pw_news = scrape_pwhl_news()
        pro_news = [n for n in pro_news if n.get("league") != "pwhl"] + pw_news
        sources["pwhl_news"] = {"ok": True, "count": len(pw_news)}
        print(f"pwhl news: {len(pw_news)} stories")
    except Exception as ex:
        sources["pwhl_news"] = {"ok": False, "error": str(ex)[:200]}
        print(f"pwhl news: FAILED - {ex}", file=sys.stderr)
        try:
            pro_news += [n for n in json.load(open(OUT_FILE, encoding="utf-8")).get("pro_news", []) if n.get("league") == "pwhl"]
        except (OSError, ValueError):
            pass

    # Sportsnet and the clubs' own sites (Pro Feed); keep the last good copy if one fails
    try:
        old_extra = json.load(open(OUT_FILE, encoding="utf-8")).get("more_news", [])
    except (OSError, ValueError):
        old_extra = []
    more_news = []
    try:
        sn = scrape_sportsnet()
        sources["sportsnet"] = {"ok": True, "count": len(sn)}
        print(f"sportsnet: {len(sn)} stories")
    except Exception as ex:
        sn = [n for n in old_extra if n.get("source") == "Sportsnet"]
        sources["sportsnet"] = {"ok": False, "error": str(ex)[:200]}
        print(f"sportsnet: FAILED - {ex}", file=sys.stderr)
    clubs, club_err = scrape_club_news()
    for team in club_err:
        clubs += [n for n in old_extra if n.get("source") == "Team site" and team in (n.get("teams") or [])]
    sources["club_news"] = {"ok": not club_err, "count": len(clubs), **({"errors": club_err} if club_err else {})}
    print(f"club news: {len(clubs)} stories" + (f" (failed: {', '.join(club_err)})" if club_err else ""))
    more_news = sn + clubs

    payload = {
        "updated": now.isoformat(timespec="seconds"),
        "today": today.isoformat(),
        "range": [(today - timedelta(days=DAYS_EACH_SIDE)).isoformat(),
                  (today + timedelta(days=DAYS_EACH_SIDE)).isoformat()],
        "teams": TEAMS,
        "sources": sources,
        "games": games,
        "pro_games": pro_games,   # CFL, used by pro-games.html
        "pro_news": pro_news,     # CFL and PWHL stories, used by news-feed.html
        "more_news": more_news,   # Sportsnet + club-site stories, used by news-feed.html
        "cfl_standings": cfl_standings,   # used by the Standings view in pro-games.html
        "standings": standings,           # OHL, OJHL, GOHL, PJHL, CJFL (Local Hub) and PWHL (Pro Hub)
    }
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    new = json.dumps(payload, ensure_ascii=False, indent=1)
    # Only rewrite when the games changed
    if os.path.exists(OUT_FILE):
        try:
            old = json.load(open(OUT_FILE, encoding="utf-8"))
            if (old.get("games") == games and old.get("sources") == sources
                    and old.get("today") == payload["today"] and old.get("pro_games") == pro_games
                    and old.get("pro_news") == pro_news and old.get("more_news") == more_news and old.get("cfl_standings") == cfl_standings
                    and old.get("standings") == standings):
                print("No changes.")
                return
        except ValueError:
            pass
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"Wrote {len(games)} games to data/local-games.json")


if __name__ == "__main__":
    main()
