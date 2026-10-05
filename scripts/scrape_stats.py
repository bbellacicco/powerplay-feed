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
  Windsor Lancers      football: totals added up from this season's box scores on golancers.ca
                       (the school's own season-totals page currently mixes 2025 and 2026, so it
                       can't be used as-is)
  PJHL clubs           GameSheet's player/goalie export (CSV). GameSheet's pages load their numbers after the
                       page opens and its rules disallow automated access, so these are not scraped:
                       data/pjhl-players.csv (and optionally data/pjhl-goalies.csv) are uploaded by hand
                       from the Export button on gamesheetstats.com/seasons/15133/players and /goalies.
Not included yet: Saints, other Lancers sports, high school.

Standard library only. Runs on GitHub Actions (.github/workflows/stats.yml).

Offline test:  python scripts/scrape_stats.py --fixtures fixtures-stats
  (reads <client>-skaters.json and <client>-goalies.json from that folder, plus
   football-results.html and boxscore-<id>.html for the Lancers)
"""

import csv
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

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



# ------------------------------------------------------------------ Lancers football
# golancers.ca (SIDEARM). Each game has a box score page with clean per-game tables for both teams.
# We add up Windsor's rows from every box score dated this calendar year.
LANCERS_BASE = "https://golancers.ca"
TZ = ZoneInfo("America/Toronto")
FB_PASS_SHOWN, FB_RUSH_SHOWN, FB_REC_SHOWN, FB_TKL_SHOWN = 3, 5, 5, 5
FB_LINK = "https://golancers.ca/sports/football/stats"


class TableScanner(HTMLParser):
    """Collects every table: its caption, the text just before it, and each row's cells (text + links)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self._depth = 0
        self._table = None
        self._row = None
        self._cell = None
        self._in_caption = False
        self._cap = []
        self._head_tag = None
        self._head = []
        self.last_heading = ""
        self._outside = []          # text nodes seen outside tables since the last table closed

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self._depth += 1
            if self._depth == 1:
                before = self._outside[-1] if self._outside else ""
                self._table = {"caption": "", "before": before, "heading": self.last_heading, "rows": []}
                self.tables.append(self._table)
            return
        if self._depth == 0:
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                self._head_tag, self._head = tag, []
            return
        if self._depth > 1:
            return
        if tag == "caption":
            self._in_caption, self._cap = True, []
        elif tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = {"text": [], "hrefs": []}
        elif tag == "a" and self._cell is not None and a.get("href"):
            self._cell["hrefs"].append(a["href"])

    def handle_endtag(self, tag):
        if tag == "table":
            if self._depth:
                self._depth -= 1
            if self._depth == 0:
                self._table, self._row, self._cell = None, None, None
                self._outside = []
            return
        if self._depth == 0:
            if tag == self._head_tag:
                self.last_heading = " ".join("".join(self._head).split())
                self._head_tag = None
            return
        if self._depth > 1:
            return
        if tag == "caption" and self._in_caption:
            self._in_caption = False
            if self._table is not None:
                self._table["caption"] = " ".join("".join(self._cap).split())
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append({"text": collapse(" ".join("".join(self._cell["text"]).split())), "hrefs": self._cell["hrefs"]})
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row:
                self._table["rows"].append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._depth == 0:
            if self._head_tag:
                self._head.append(data)
            t = " ".join(data.split())
            if t:
                self._outside.append(t)
            return
        if self._in_caption:
            self._cap.append(data)
        if self._cell is not None:
            self._cell["text"].append(data)


def collapse(text):
    """'Kareame Cotton Kareame Cotton' (a screen-reader duplicate) -> 'Kareame Cotton'."""
    tok = text.split()
    n = len(tok)
    if n >= 2 and n % 2 == 0 and tok[:n // 2] == tok[n // 2:]:
        return " ".join(tok[:n // 2])
    return text


def norm_header(c):
    return re.sub(r"[^a-z0-9/%]", "", c["text"].lower())


def table_kind(header):
    h = set(header)
    if {"cmp", "att", "yds", "td"} <= h and "gain" not in h:
        return "passing"
    if {"att", "gain", "net"} <= h:
        return "rushing"
    if {"rec", "yds", "td"} <= h and "att" not in h:
        return "receiving"
    if {"solo", "ast", "tot"} <= h:
        return "defense"
    return None


def is_windsor(tbl):
    title = (tbl["caption"] or tbl["before"] or tbl["heading"]).lower()
    return "wsr" in title or "windsor" in title


def rp_id(cell):
    for h in cell["hrefs"]:
        m = re.search(r"rp_id=(\d+)|/roster/[^/]+/(\d+)", h)
        if m:
            return m.group(1) or m.group(2)
    return None


def box_tables(html):
    """{'passing': [rows], ...} for Windsor, where a row is (player key, name, {header: cell text})."""
    sc = TableScanner()
    sc.feed(html)
    found = {}
    for tbl in sc.tables:
        hi, header, kind = None, None, None
        for i, r in enumerate(tbl["rows"][:3]):
            hd = [norm_header(c) for c in r]
            k = table_kind(hd)
            if k:
                hi, header, kind = i, hd, k
                break
        if not kind:
            continue
        if hi and not tbl["caption"]:      # a title row sat above the column headings
            tbl["caption"] = " ".join(c["text"] for c in tbl["rows"][0])
        tbl["header_row"] = hi
        if not is_windsor(tbl):
            continue
        found.setdefault(kind, []).append((tbl, header))
    out = {}
    for kind, tbls in found.items():
        if len(tbls) != 1:       # two tables claiming to be Windsor's: don't guess which
            print(f"::warning::{len(tbls)} Windsor '{kind}' tables in one box score; skipping that table", file=sys.stderr)
            continue
        tbl, header = tbls[0]
        rows = []
        for r in tbl["rows"][tbl["header_row"] + 1:]:
            if len(r) != len(header):
                continue
            name = r[0]["text"]
            low = name.lower()
            if not name or low.startswith("total") or low in ("team", "tm"):
                continue
            rows.append((rp_id(r[0]) or "n:" + low, name, dict(zip(header, [c["text"] for c in r]))))
        out[kind] = rows
    return out, sc.tables


def fnum(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def fb_game_ids(html, year):
    """Box score ids from a results table, for rows dated in `year`."""
    sc = TableScanner()
    sc.feed(html)
    ids = {}
    for tbl in sc.tables:
        for r in tbl["rows"]:
            m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", r[0]["text"])
            if not m or int(m.group(3)) != year:
                continue
            for cell in r:
                for h in cell["hrefs"]:
                    g = re.search(r"boxscore(?:\.aspx\?id=|/)(\d+)", h)
                    if g:
                        ids[g.group(1)] = f"{int(m.group(3)):04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return ids


def nice_total(v):
    return str(int(v)) if float(v).is_integer() else "%.1f" % v


def scrape_lancers_football(now):
    year = now.astimezone(TZ).year
    ids = {}
    for y in (year, year - 1):    # this season's games are filed under whichever year the site uses
        try:
            html = fetch(f"{LANCERS_BASE}/sports/football/stats/{y}", "football-results.html")
        except Exception as ex:
            print(f"  football results page {y}: {ex}", file=sys.stderr)
            continue
        ids.update(fb_game_ids(html, year))
        if FIXTURES:
            break
    if not ids:
        raise RuntimeError(f"no {year} football box scores found on golancers.ca yet")
    players = {}          # key -> {"names": Counter, pass/rush/rec/def totals}
    games_used, last_page = [], None
    for gid, day in sorted(ids.items(), key=lambda kv: kv[1]):
        try:
            page = fetch(f"{LANCERS_BASE}/boxscore.aspx?id={gid}&path=football", f"boxscore-{gid}.html")
            kinds, tables = box_tables(page)
            last_page = tables
        except Exception as ex:
            print(f"  football box score {gid}: skipped - {ex}", file=sys.stderr)
            continue
        if not kinds:
            continue
        games_used.append(day)
        for kind, rows in kinds.items():
            for key, name, c in rows:
                p = players.setdefault(key, {"names": Counter(), "cmp": 0, "pa": 0, "py": 0, "ptd": 0, "pint": 0,
                                             "ra": 0, "ry": 0, "rtd": 0, "rec": 0, "cy": 0, "ctd": 0,
                                             "tkl": 0, "solo": 0, "ast": 0, "sack": 0.0})
                p["names"][name] += 1
                if kind == "passing":
                    p["cmp"] += fnum(c.get("cmp")); p["pa"] += fnum(c.get("att")); p["py"] += fnum(c.get("yds"))
                    p["ptd"] += fnum(c.get("td")); p["pint"] += fnum(c.get("int"))
                elif kind == "rushing":
                    p["ra"] += fnum(c.get("att")); p["ry"] += fnum(c.get("net")); p["rtd"] += fnum(c.get("td"))
                elif kind == "receiving":
                    p["rec"] += fnum(c.get("rec")); p["cy"] += fnum(c.get("yds")); p["ctd"] += fnum(c.get("td"))
                elif kind == "defense":
                    p["tkl"] += fnum(c.get("tot")); p["solo"] += fnum(c.get("solo")); p["ast"] += fnum(c.get("ast"))
                    p["sack"] += fnum(c.get("sacks"))
    if not games_used:
        desc = [(t["caption"] or t["before"], [c["text"] for c in t["rows"][0]][:6]) for t in (last_page or [])[:10] if t["rows"]]
        raise RuntimeError(f"found {len(ids)} box scores but no Windsor stat tables in them; tables seen: {desc}")

    def nm(p):
        return p["names"].most_common(1)[0][0]

    def top(field, n, minimum_field=None):
        rows = [p for p in players.values() if p[field] > 0 and (minimum_field is None or p[minimum_field] > 0)]
        rows.sort(key=lambda p: (-p[field], nm(p)))
        return rows[:n]

    groups = []
    g = top("py", FB_PASS_SHOWN, "pa")
    if g:
        groups.append({"title": "Passing", "cols": ["C/A", "YDS", "TD", "INT"], "key": 1,
                       "rows": [{"name": nm(p), "vals": ["%d/%d" % (p["cmp"], p["pa"]), int(p["py"]), int(p["ptd"]), int(p["pint"])]} for p in g]})
    g = top("ry", FB_RUSH_SHOWN, "ra")
    if g:
        groups.append({"title": "Rushing", "cols": ["ATT", "YDS", "AVG", "TD"], "key": 1,
                       "rows": [{"name": nm(p), "vals": [int(p["ra"]), int(p["ry"]), "%.1f" % (p["ry"] / p["ra"]), int(p["rtd"])]} for p in g]})
    g = top("cy", FB_REC_SHOWN, "rec")
    if g:
        groups.append({"title": "Receiving", "cols": ["REC", "YDS", "AVG", "TD"], "key": 1,
                       "rows": [{"name": nm(p), "vals": [int(p["rec"]), int(p["cy"]), "%.1f" % (p["cy"] / p["rec"]), int(p["ctd"])]} for p in g]})
    g = top("tkl", FB_TKL_SHOWN)
    if g:
        groups.append({"title": "Tackles", "cols": ["TKL", "SOLO", "AST", "SACK"], "key": 0,
                       "rows": [{"name": nm(p), "vals": [nice_total(p["tkl"]), int(p["solo"]), int(p["ast"]), nice_total(p["sack"])]} for p in g]})
    if not groups:
        raise RuntimeError("box scores parsed but no player totals came out")
    n = len(games_used)

    def pretty(d):
        t = datetime.strptime(d, "%Y-%m-%d")
        return t.strftime("%b ") + str(t.day)
    note = (f"Season totals added up from the {n} Lancers box score{'s' if n != 1 else ''} on golancers.ca "
            f"({pretty(games_used[0])} to {pretty(games_used[-1])}). Refreshed every hour.")
    return {"team": "lancers", "club": "Windsor Lancers", "league": "OUA football", "link": FB_LINK, "note": note,
            "updated": now.isoformat(), "groups": groups}


# ------------------------------------------------------------------ PJHL (hand-uploaded GameSheet exports)
PJHL_CLUBS = ["Lakeshore Canadiens", "Essex 73's", "Wheatley Sharks", "Amherstburg Admirals"]
PJHL_LEAGUE = "PJHL (Jr. C)"
PJHL_LINK = "https://gamesheetstats.com/seasons/15133/players"
PJHL_PLAYERS_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "pjhl-players.csv")
PJHL_GOALIES_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "pjhl-goalies.csv")
PJHL_NOTE = "From GameSheet's PJHL export, updated whenever a new export is added."


def alnum(t):
    return re.sub(r"[^a-z0-9]", "", str(t).lower())


def tidy_name(n):
    n = " ".join(str(n).split())
    if "," in n:                                   # "Graham, Colton" -> "Colton Graham"
        last, _, first = n.partition(",")
        n = f"{first.strip()} {last.strip()}"
    if n.isupper() or n.islower():                 # "COLTON GRAHAM" -> "Colton Graham"
        def word(w):
            w = "-".join(p.capitalize() for p in w.split("-"))
            w = re.sub(r"(?<![A-Za-z])(O'|D')([a-z])", lambda m: m.group(1) + m.group(2).upper(), w)
            return re.sub(r"^(Mc)([a-z])", lambda m: m.group(1) + m.group(2).upper(), w)
        n = " ".join(word(w) for w in n.split())
    return n


def read_export(path):
    """(header map, rows) from a GameSheet CSV export, or None when the file isn't there."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8-sig", newline="") as f:
        text = f.read()
    rows = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
    for i, r in enumerate(rows):                  # the header is the first row that names a player and GP
        names = [re.sub(r"[^a-z0-9%]", "", c.lower()) for c in r]
        if ("player" in names or "name" in names) and "gp" in names:
            hdr = {}
            for j, nme in enumerate(names):
                hdr.setdefault(nme, j)
            return hdr, rows[i + 1:]
    raise RuntimeError(f"{os.path.basename(path)}: couldn't find a header row with PLAYER and GP; "
                       f"first row is {rows[0][:8] if rows else 'empty'}")


def pick_col(hdr, *names):
    for n in names:
        if n in hdr:
            return hdr[n]
    return None


def cell(row, idx):
    return row[idx].strip() if idx is not None and idx < len(row) else ""


def scrape_pjhl(now):
    ex = read_export(PJHL_PLAYERS_CSV)
    if ex is None:
        raise FileNotFoundError("no data/pjhl-players.csv yet (export it from GameSheet and upload it to the data folder)")
    hdr, rows = ex
    c_name = pick_col(hdr, "player", "name")
    c_team, c_pos = pick_col(hdr, "team", "teamname"), pick_col(hdr, "pos", "position")
    c_gp, c_g, c_a = pick_col(hdr, "gp"), pick_col(hdr, "g", "goals"), pick_col(hdr, "a", "assists")
    c_pts = pick_col(hdr, "pts", "points", "p")
    if None in (c_name, c_team, c_gp) or (c_pts is None and (c_g is None or c_a is None)):
        raise RuntimeError(f"pjhl-players.csv is missing a column I need; columns are {sorted(hdr)}")
    goalies = None
    try:
        gx = read_export(PJHL_GOALIES_CSV)
        if gx:
            goalies = gx
    except Exception as ex2:
        print(f"  PJHL goalies skipped - {ex2}", file=sys.stderr)

    out, missing, teams_seen = [], [], sorted({cell(r, c_team) for r in rows if cell(r, c_team)})
    for club in PJHL_CLUBS:
        key = alnum(club)
        skaters = []
        for r in rows:
            if alnum(cell(r, c_team)) != key:
                continue
            if cell(r, c_pos).upper() in ("G", "GK", "GOALIE"):
                continue
            g, a = whole(cell(r, c_g)) or 0, whole(cell(r, c_a)) or 0
            pts = whole(cell(r, c_pts)) if c_pts is not None else None
            skaters.append((tidy_name(cell(r, c_name)), [whole(cell(r, c_gp)) or 0, g, a, g + a if pts is None else pts]))
        skaters.sort(key=lambda x: (-x[1][3], -x[1][1], x[0]))
        groups = []
        if skaters[:SKATERS_SHOWN]:
            groups.append({"title": "Scoring leaders", "cols": ["GP", "G", "A", "PTS"], "key": 3,
                           "rows": [{"name": n, "vals": v} for n, v in skaters[:SKATERS_SHOWN]]})
        if goalies:
            gh, grows = goalies
            gn, gt = pick_col(gh, "player", "name"), pick_col(gh, "team", "teamname")
            gg, gw = pick_col(gh, "gp"), pick_col(gh, "w", "wins")
            gaa, gsv = pick_col(gh, "gaa", "gaavg", "goalsagainstaverage"), pick_col(gh, "sv%", "svpct", "savepct", "savepercentage", "svp")
            gl = []
            for r in grows:
                if alnum(cell(r, gt)) != key:
                    continue
                gp = whole(cell(r, gg)) or 0
                if gp:
                    gl.append((tidy_name(cell(r, gn)), whole(cell(r, gw)) or 0, gp,
                               [gp, whole(cell(r, gw)) or 0, "" if num(cell(r, gaa)) is None else "%.2f" % num(cell(r, gaa)), save_pct(cell(r, gsv))]))
            gl.sort(key=lambda x: (-x[1], -x[2], x[0]))
            if gl[:GOALIES_SHOWN]:
                groups.append({"title": "Goalies", "cols": ["GP", "W", "GAA", "SV%"], "key": 1,
                               "rows": [{"name": n, "vals": v} for n, _, _, v in gl[:GOALIES_SHOWN]]})
        if not groups:
            missing.append(club)
            continue
        out.append({"team": "junior", "club": club, "league": PJHL_LEAGUE, "link": PJHL_LINK, "note": PJHL_NOTE,
                    "updated": now.isoformat(), "groups": groups})
    if not out:
        raise RuntimeError(f"none of the four PJHL clubs matched the TEAM column; teams in the file include {teams_seen[:12]}")
    if missing:
        print(f"::warning::PJHL export has no rows for: {', '.join(missing)}; teams in the file include {teams_seen[:12]}")
    return out

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
    jobs = [([(e[0], e[1])], (lambda e=e: scrape_club(e, now))) for e in TEAMS]
    jobs.append(([("lancers", "Windsor Lancers")], lambda: scrape_lancers_football(now)))
    jobs.append(([("junior", c) for c in PJHL_CLUBS], lambda: scrape_pjhl(now)))
    for keys, run in jobs:
        label = keys[0][1] if len(keys) == 1 else "PJHL clubs"
        try:
            got = run()
            teams.extend(got if isinstance(got, list) else [got])
            print(f"  {label}: ok")
        except FileNotFoundError as ex:
            print(f"  {label}: skipped - {ex}")      # not an error: it just hasn't been set up yet
            for k in keys:
                if previous.get(k):
                    teams.append(previous[k])
        except Exception as ex:
            failed.append(label)
            print(f"::warning::Stats for {label} failed: {ex}")
            for k in keys:                           # keep the last good numbers rather than dropping the club
                if previous.get(k):
                    teams.append(previous[k])
    # "Updated" should mean "the numbers last changed", so keep the old stamp when a club's numbers are the same
    for i, t in enumerate(teams):
        old = previous.get((t["team"], t["club"]))
        if old and without_times([old]) == without_times([t]):
            teams[i] = dict(t, updated=old["updated"])
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
