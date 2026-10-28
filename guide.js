/* Powerplay Windsor "local guide" panel: the things you can only get here, in one glance.
   Today's local games, the latest local finals and the Community Calendar, with how fresh the data is.
   Used by home.html (under the top story) and discover.html (the strip under every blog post).
     <script src="guide.js"></script>
     PPGuide.render(document.getElementById('guide'), { compact: false, target: '_top' });
   Data: local-games.json, saints.json, highschool.json, calendar.json (refreshes every 5 minutes). */
(function () {
  var DATA = 'https://bbellacicco.github.io/powerplay-feed/data/';
  var HUB = 'https://www.powerplaywindsor.com/scores-standings';
  var TZ = 'America/Toronto';
  var MON = ['Jan.', 'Feb.', 'March', 'April', 'May', 'June', 'July', 'Aug.', 'Sept.', 'Oct.', 'Nov.', 'Dec.'];
  var DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  var COLOR = { spitfires: '#d4202c', lancers: '#0f6bd6', saints: '#1f9d55', junior: '#0ea5a4', highschool: '#8b5cf6' };
  var RANK = { spitfires: 0, lancers: 1, saints: 2, junior: 3, highschool: 4 };
  var US = { spitfires: 'Spitfires', lancers: 'Lancers', saints: 'Saints' };

  var CSS = '' +
    '.ppg{position:relative;border:1px solid #1e3a6e;border-radius:12px;overflow:hidden;background:radial-gradient(120% 160% at 0% 0%,rgba(232,176,33,.13),transparent 55%),linear-gradient(180deg,#10244a,#0b1a33);color:#f2f5fb;font:14px/1.35 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}' +
    '.ppg::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:#e8b021}' +
    '.ppg *{box-sizing:border-box}.ppg a{color:inherit;text-decoration:none}' +
    '.ppg .pg-gh{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:14px 16px 10px 20px}' +
    '.ppg .pg-gk{font-size:11px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:#e8b021}' +
    '.ppg .pg-gt{margin:3px 0 0;font-size:22px;font-weight:900;line-height:1.1;letter-spacing:-.01em}' +
    '.ppg .pg-gs{color:#9fb0cf;font-size:13px;margin-top:3px}' +
    '.ppg .pg-fresh{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:700;color:#cfe0ff;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:999px;padding:5px 11px;white-space:nowrap}' +
    '.ppg .pg-fresh i{width:8px;height:8px;border-radius:50%;background:#2ecc71;box-shadow:0 0 0 3px rgba(46,204,113,.25)}' +
    '.ppg .pg-cols{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px;padding:0 14px 14px 18px}' +
    '.ppg .pg-col{display:flex;flex-direction:column;background:rgba(8,20,40,.55);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:12px 12px 10px;min-width:0}' +
    '.ppg .pg-ch{display:flex;align-items:baseline;justify-content:space-between;gap:8px;margin-bottom:8px}' +
    '.ppg .pg-ch b{font-size:12px;font-weight:800;letter-spacing:.1em;text-transform:uppercase}' +
    '.ppg .pg-ch span{color:#9fb0cf;font-size:12px;white-space:nowrap}' +
    '.ppg .pg-big{font-size:30px;font-weight:900;line-height:1;margin:0 0 8px}.ppg .pg-big small{font-size:14px;font-weight:700;color:#9fb0cf;margin-left:6px}' +
    '.ppg .pg-chips{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:8px}' +
    '.ppg .pg-chip{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:700;background:rgba(255,255,255,.07);border-radius:4px;padding:3px 7px}' +
    '.ppg .pg-chip i,.ppg .pg-li i{flex:none;width:8px;height:8px;border-radius:2px;background:var(--c)}' +
    '.ppg .pg-li{display:flex;align-items:center;gap:8px;padding:6px 0;border-top:1px solid rgba(255,255,255,.07);min-width:0}' +
    '.ppg .pg-li:first-child{border-top:0}' +
    '.ppg .pg-li .pg-tm{flex:none;width:58px;font-weight:800;font-size:12.5px;color:#e8b021;white-space:nowrap}' +
    '.ppg .pg-li .pg-tx{min-width:0;flex:1}' +
    '.ppg .pg-li .pg-tm.pg-live{color:#ff4d4d}.ppg .pg-li .pg-tm.pg-live::before{content:"";display:inline-block;width:7px;height:7px;border-radius:50%;background:#ff4d4d;margin-right:5px;vertical-align:1px;animation:pgpulse 1.2s infinite}.ppg .pg-li .pg-tm.pg-fin{color:#9fb0cf}' +
    '.ppg .pg-sc{color:#fff;font-weight:900;font-variant-numeric:tabular-nums}@keyframes pgpulse{50%{opacity:.25}}' +
    '.ppg .pg-li .pg-a{font-weight:700;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.ppg .pg-li .pg-b{color:#9fb0cf;font-size:11.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.ppg .pg-dt{flex:none;width:40px;text-align:center;background:#fff;color:#0b1a33;border-radius:5px;padding:3px 0 4px;line-height:1}' +
    '.ppg .pg-dt small{display:block;font-size:9px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#a5161f}' +
    '.ppg .pg-cal .pg-a{white-space:normal;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;line-height:1.25}.ppg .pg-cal .pg-li{align-items:flex-start}' +
    '.ppg .pg-dt b{display:block;font-size:16px;font-weight:800;margin-top:1px}' +
    '.ppg .pg-none{color:#9fb0cf;font-size:13px;padding:6px 0}' +
    '.ppg .pg-go{margin-top:auto;padding-top:9px;font-size:12.5px;font-weight:800;color:#e8b021}' +
    '.ppg .pg-go:hover{text-decoration:underline}' +
    '.ppg .pg-col:hover{border-color:rgba(232,176,33,.45)}' +
    '@media (max-width:820px){.ppg .pg-cols{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;padding-right:14px;scrollbar-width:none}.ppg .pg-cols::-webkit-scrollbar{display:none}.ppg .pg-col{flex:0 0 84%;scroll-snap-align:start}.ppg .pg-gt{font-size:19px}.ppg .pg-gh{padding:12px 14px 8px 18px}}' +
    '.ppg.compact .pg-gt{font-size:18px}.ppg.compact .pg-big{font-size:24px}';

  function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }
  function getJSON(n) { return fetch(DATA + n + '?t=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }); }
  function parts(d) { var p = {}; new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: '2-digit', hourCycle: 'h23' }).formatToParts(d).forEach(function (x) { p[x.type] = x.value; }); return p; }
  function dayKey(d) { var p = parts(d); return p.year + '-' + ('0' + p.month).slice(-2) + '-' + ('0' + p.day).slice(-2); }
  function noon(k) { return new Date(k + 'T12:00:00'); }
  function cpDate(k) { var d = noon(k); return MON[d.getMonth()] + ' ' + d.getDate(); }
  function wd(k) { return DAYS[noon(k).getDay()]; }
  function cpTime(d) { var p = parts(d), h = +p.hour; return (h % 12 || 12) + (p.minute === '00' ? '' : ':' + p.minute) + (h < 12 ? ' a.m.' : ' p.m.'); }
  function hubLink(tab) { return HUB + '?tab=' + tab; }

  function shortSport(s) {
    return String(s || '').replace(/^Senior /, 'Sr. ').replace(/^Junior /, 'Jr. ').replace(/ Boys /, ' boys ').replace(/ Girls /, ' girls ')
      .replace(/ (Basketball|Volleyball|Football|Soccer|Hockey|Rugby|Baseball|Softball)$/, function (m) { return m.toLowerCase(); });
  }
  function label(g) {   // who the game belongs to, for the small grey line
    if (g.team === 'highschool') return 'High school · ' + shortSport(g.sport);
    if (g.team === 'junior') return (g.club || 'Junior hockey') + (g.sport ? ' · ' + g.sport.replace(/\s*\(.*\)/, '') : '');
    if (g.team === 'spitfires') return 'Spitfires · OHL';
    return (US[g.team] || g.club || '') + (g.sport ? ' · ' + g.sport.toLowerCase() : '');
  }
  function sides(g) {   // [away, home, away score, home score]
    var us = g.club || US[g.team] || '';
    if (g.home && g.away) return [g.away, g.home, g.our_score, g.opp_score];
    if (g.home_away === 'H') return [g.opponent, us, g.opp_score, g.our_score];
    return [us, g.opponent, g.our_score, g.opp_score];
  }

  var box_live = false;   // any game live right now (refresh every minute instead of every five)
  function load() {
    return Promise.all([getJSON('local-games.json'), getJSON('saints.json'), getJSON('highschool.json'), getJSON('calendar.json')]).then(function (r) {
      var lg = r[0] || {}, sc = r[1], hs = r[2], cal = r[3];
      var all = (lg.games || []).slice();
      if (sc && sc.games) all = all.filter(function (g) { return !(g.team === 'saints' && g.sport !== 'Football'); })
        .concat(sc.games.filter(function (g) { return g.sport !== 'Football'; }));
      if (hs && hs.games) all = all.filter(function (g) { return g.team !== 'highschool'; }).concat(hs.games);
      var seen = {};
      all = all.filter(function (g) { var k = g.id || (g.team + g.start + g.opponent); if (seen[k]) return false; seen[k] = 1; return true; });
      var upd = [lg.updated, sc && sc.updated, hs && hs.updated, cal && cal.updated].filter(Boolean).map(function (u) { return new Date(u).getTime(); });
      return { games: all, events: (cal && cal.events) || [], updated: upd.length ? Math.max.apply(null, upd) : 0 };
    });
  }

  function ago(t) {
    if (!t) return '';
    var m = Math.round((Date.now() - t) / 60000);
    if (m < 1) return 'Updated just now';
    if (m < 60) return 'Updated ' + m + ' min ago';
    var h = Math.round(m / 60);
    return h < 24 ? 'Updated ' + h + (h === 1 ? ' hour ago' : ' hours ago') : '';
  }

  function colHead(col, title, side) {
    var h = el('div', 'pg-ch'); h.appendChild(el('b', null, title)); if (side) h.appendChild(el('span', null, side)); col.appendChild(h);
  }
  function goLink(col, text, href, target) { var a = el('a', 'pg-go', text + ' ›'); a.href = href; a.target = target; col.appendChild(a); }

  // 1. today's games (or the next day that has some)
  function gamesCol(d, target, compact) {
    box_live = false;
    var col = el('div', 'pg-col'), today = dayKey(new Date());
    var future = d.games.filter(function (g) { return dayKey(new Date(g.start)) >= today; });
    var day = future.some(function (g) { return dayKey(new Date(g.start)) === today; }) ? today
      : future.map(function (g) { return dayKey(new Date(g.start)); }).sort()[0];
    var mine = day ? future.filter(function (g) { return dayKey(new Date(g.start)) === day; }) : [];
    var title = day === today ? 'Today' : day === dayKey(new Date(Date.now() + 864e5)) ? 'Tomorrow' : day ? wd(day) : 'Coming up';
    colHead(col, title + "'s games", day ? wd(day).slice(0, 3) + '., ' + cpDate(day) : '');
    if (!mine.length) { col.appendChild(el('div', 'pg-none', 'No local games on the schedule yet.')); goLink(col, 'See the schedule', hubLink('upcoming'), target); return col; }
    var big = el('div', 'pg-big', String(mine.length)); big.appendChild(el('small', null, mine.length === 1 ? 'local game' : 'local games')); col.appendChild(big);
    var count = {}; mine.forEach(function (g) { count[g.team] = (count[g.team] || 0) + 1; });
    var chips = el('div', 'pg-chips');
    Object.keys(count).sort(function (a, b) { return RANK[a] - RANK[b]; }).forEach(function (t) {
      var c = el('span', 'pg-chip'); c.style.setProperty('--c', COLOR[t] || '#e8b021'); c.appendChild(el('i'));
      c.appendChild(document.createTextNode(({ spitfires: 'Spitfires', lancers: 'Lancers', saints: 'Saints', junior: 'Junior hockey', highschool: 'High school' })[t] + ' ' + count[t]));
      chips.appendChild(c);
    });
    col.appendChild(chips);
    var now = Date.now();
    var stale = function (g) { return g.status === 'live' && now - new Date(g.start).getTime() > 4 * 3600e3; };   // data behind: don't show it as live
    var isLive = function (g) { return g.status === 'live' && !stale(g); };
    var scored = function (g) { return g.our_score != null && g.opp_score != null; };
    var n = compact ? 3 : 4;
    // live games first (with the score), then the next games, then today's finals if there's room
    var live = mine.filter(isLive).sort(function (a, b) { return RANK[a.team] - RANK[b.team]; });
    var next = mine.filter(function (g) { return !isLive(g) && g.status !== 'final' && g.status !== 'cancelled'; })
      .sort(function (a, b) { return (RANK[a.team] - RANK[b.team]) || (a.time_tbd ? 1 : 0) - (b.time_tbd ? 1 : 0) || (a.start < b.start ? -1 : 1); })
      .slice(0, Math.max(n - live.length, 0))
      .sort(function (a, b) { return (a.time_tbd ? 1 : 0) - (b.time_tbd ? 1 : 0) || (a.start < b.start ? -1 : 1); });
    var done = mine.filter(function (g) { return g.status === 'final' && scored(g); })
      .sort(function (a, b) { return RANK[a.team] - RANK[b.team]; });
    var pick = live.concat(next);
    pick = pick.concat(done.slice(0, Math.max(n - pick.length, 0)));
    var list = el('div');
    pick.forEach(function (g) {
      var s = sides(g), li = el('div', 'pg-li'); li.style.setProperty('--c', COLOR[g.team] || '#e8b021');
      var lv = isLive(g), fin = g.status === 'final';
      var started = !g.time_tbd && g.status === 'upcoming' && new Date(g.start).getTime() < now && now - new Date(g.start).getTime() < 3 * 3600e3;
      var tm = el('div', 'pg-tm' + (lv ? ' pg-live' : fin ? ' pg-fin' : ''),
        lv ? 'LIVE' : fin ? 'Final' : g.status === 'postponed' ? 'PPD' : started ? 'Now' : g.time_tbd ? 'TBA' : cpTime(new Date(g.start)));
      li.appendChild(tm);
      var tx = el('div', 'pg-tx'), a = el('div', 'pg-a');
      if ((lv || fin) && (scored(g) || lv)) {     // "Saginaw Spirit 2 at Spitfires 3", scores in bold
        a.appendChild(document.createTextNode(s[0] + ' ')); a.appendChild(el('b', 'pg-sc', String(s[2] == null ? 0 : s[2])));
        a.appendChild(document.createTextNode(' at ' + s[1] + ' ')); a.appendChild(el('b', 'pg-sc', String(s[3] == null ? 0 : s[3])));
      } else a.textContent = s[0] + (g.home_away === 'N' && !(g.home && g.away) ? ' vs. ' : ' at ') + s[1];
      tx.appendChild(a);
      tx.appendChild(el('div', 'pg-b', label(g) + (lv && g.detail ? ' · ' + g.detail : ''))); li.appendChild(tx); list.appendChild(li);
    });
    box_live = live.length > 0;
    col.appendChild(list);
    var rest = mine.length - pick.length;
    goLink(col, rest > 0 ? 'See all ' + mine.length + ' games' : 'See the full schedule', hubLink('upcoming') + (day !== today ? '&day=' + day : ''), target);
    return col;
  }

  // 2. the latest local finals (last two days), our teams first
  function finalsCol(d, target, compact) {
    var col = el('div', 'pg-col');
    var since = Date.now() - 2.5 * 864e5;
    var fin = d.games.filter(function (g) { return g.status === 'final' && g.our_score != null && g.opp_score != null && new Date(g.start).getTime() > since; });
    fin.sort(function (a, b) { return b.start < a.start ? -1 : b.start > a.start ? 1 : RANK[a.team] - RANK[b.team]; });
    var ours = fin.filter(function (g) { return g.team !== 'highschool'; }), hsg = fin.filter(function (g) { return g.team === 'highschool'; });
    var n = compact ? 4 : 5, show = ours.slice(0, Math.max(n - Math.min(2, hsg.length), 0));
    show = show.concat(hsg.slice(0, n - show.length));
    colHead(col, 'Latest scores', fin.length ? fin.length + ' finals' : '');
    if (!show.length) col.appendChild(el('div', 'pg-none', 'No local finals in the last two days.'));
    show.forEach(function (g) {
      var s = sides(g), li = el('div', 'pg-li'); li.style.setProperty('--c', COLOR[g.team] || '#e8b021'); li.appendChild(el('i'));
      var w = +s[2] >= +s[3] ? [s[0], s[2], s[1], s[3]] : [s[1], s[3], s[0], s[2]];
      var tx = el('div', 'pg-tx'); tx.appendChild(el('div', 'pg-a', w[0] + ' ' + w[1] + ', ' + w[2] + ' ' + w[3]));
      var k = dayKey(new Date(g.start));
      tx.appendChild(el('div', 'pg-b', label(g) + ' · ' + (k === dayKey(new Date()) ? 'Today' : k === dayKey(new Date(Date.now() - 864e5)) ? 'Yesterday' : wd(k))));
      li.appendChild(tx); col.appendChild(li);
    });
    goLink(col, 'All local scores', hubLink('scores'), target);
    return col;
  }

  // 3. Community Calendar: what's on in the community, from your event posts
  function calCol(d, target, compact) {
    var col = el('div', 'pg-col pg-cal'), today = dayKey(new Date());
    var evs = d.events.filter(function (e) { return (e.end || e.date) >= today; }).slice(0, compact ? 3 : 4);
    colHead(col, 'Community Calendar', evs.length ? 'Coming up' : '');
    if (!evs.length) col.appendChild(el('div', 'pg-none', 'New community events are posted here as they are announced.'));
    evs.forEach(function (e) {
      var a = el('a', 'pg-li'); a.href = e.url; a.target = target;
      var dt = el('div', 'pg-dt'), nd = noon(e.date);
      dt.appendChild(el('small', null, e.date === today ? 'Today' : MON[nd.getMonth()].replace('.', '').slice(0, 4)));
      dt.appendChild(el('b', null, String(nd.getDate()))); a.appendChild(dt);
      var tx = el('div', 'pg-tx'); tx.appendChild(el('div', 'pg-a', e.headline));
      tx.appendChild(el('div', 'pg-b', [e.when, e.where].filter(Boolean).join(' · '))); a.appendChild(tx);
      col.appendChild(a);
    });
    goLink(col, 'See the calendar', hubLink('upcoming'), target);
    return col;
  }

  function draw(box, d, o) {
    box.innerHTML = '';
    var g = el('div', 'ppg' + (o.compact ? ' compact' : ''));
    var h = el('div', 'pg-gh'), l = el('div');
    l.appendChild(el('div', 'pg-gk', o.kicker || 'Your local sports guide'));
    l.appendChild(el('div', 'pg-gt', o.title || 'Windsor-Essex sports, all in one place'));
    l.appendChild(el('div', 'pg-gs', o.sub || 'Every local game, score and community event, checked around the clock.'));
    h.appendChild(l);
    var f = ago(d.updated);
    if (f) { var fr = el('span', 'pg-fresh'); fr.appendChild(el('i')); fr.appendChild(document.createTextNode(f)); h.appendChild(fr); }
    g.appendChild(h);
    var cols = el('div', 'pg-cols');
    cols.appendChild(gamesCol(d, o.target, o.compact));
    cols.appendChild(finalsCol(d, o.target, o.compact));
    cols.appendChild(calCol(d, o.target, o.compact));
    g.appendChild(cols);
    box.appendChild(g);
  }

  function render(box, opts) {
    if (!box) return;
    var o = opts || {}; o.target = o.target || '_top';
    if (!document.getElementById('ppg-css')) { var s = document.createElement('style'); s.id = 'ppg-css'; s.textContent = CSS; document.head.appendChild(s); }
    var last = null;
    function go() { load().then(function (d) { last = d; draw(box, d, o); if (o.onDraw) o.onDraw(); }); }
    var lastRun = 0;
    function tick() { if (Date.now() - lastRun >= (box_live ? 60000 : 5 * 60000)) { lastRun = Date.now(); go(); } }
    tick();
    setInterval(tick, 15000);
    setInterval(function () { if (last) { var fr = box.querySelector('.pg-fresh'); if (fr) fr.lastChild.textContent = ago(last.updated); } }, 60000);
  }

  window.PPGuide = { render: render };
})();
