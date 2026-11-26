/* Powerplay Windsor "local guide" panel: the things you can only get here, in one glance.
   Today's local games, the latest local finals and the Community Calendar, with how fresh the data is.
   Used by home.html (under the top story) and discover.html (the strip under every blog post).
   { mode: 'pro' }: the Pro Sports Guide on the Pro Hub (every pro game today with the scores, and the next three days).
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
  var TIPS = 'powerplaysportsvideo@gmail.com';   // where fans send events and story ideas
  var SPONSOR = { name: 'St. Clair College Alumni', logo: 'https://bbellacicco.github.io/powerplay-feed/logos/st-clair-alumni.png' };   // "Presented by" in the guide's header

  var CSS = '' +
    '.ppg{position:relative;border:1px solid #1e3a6e;border-radius:12px;overflow:hidden;background:radial-gradient(120% 160% at 0% 0%,rgba(232,176,33,.13),transparent 55%),linear-gradient(180deg,#10244a,#0b1a33);color:#f2f5fb;font:14px/1.35 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}' +
    '.ppg::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:#e8b021}' +
    '.ppg *{box-sizing:border-box}.ppg a{color:inherit;text-decoration:none}' +
    '.ppg .pg-gh{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:14px 16px 10px 20px}' +
    '.ppg .pg-gk{font-size:11px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:#e8b021}' +
    '.ppg .pg-gt{margin:3px 0 0;font-size:22px;font-weight:900;line-height:1.1;letter-spacing:-.01em}' +
    '.ppg .pg-gs{color:#9fb0cf;font-size:13px;margin-top:3px}' +
    '.ppg .pg-gr{display:flex;flex-direction:column;align-items:flex-end;gap:7px}' +
    '.ppg .pg-by{display:flex;align-items:center;gap:7px;font-size:11px;color:#9fb0cf;letter-spacing:.04em;text-transform:uppercase;font-weight:700}' +
    '.ppg .pg-by b{color:#f2f5fb;text-transform:none;letter-spacing:0;font-size:12.5px}' +
    '.ppg .pg-spchip{display:inline-flex;align-items:center;background:#fff;border-radius:4px;padding:3px 7px;height:30px}.ppg .pg-spchip img{height:24px;width:auto;max-width:90px;object-fit:contain;display:block}' +
    '.ppg .pg-krow{display:flex;align-items:center;justify-content:space-between;gap:8px}.ppg .pg-fresh.pg-fm{display:none}' +
    '@media (max-width:820px){.ppg .pg-gh{flex-direction:column;align-items:stretch;gap:9px}.ppg .pg-gs{display:none}.ppg .pg-gk{font-size:10px}' + '.ppg .pg-gr{flex-direction:row;align-items:center;justify-content:space-between;width:100%;gap:8px;padding-top:9px;border-top:1px solid rgba(255,255,255,.08)}' + '.ppg .pg-by{gap:6px;font-size:9.5px;min-width:0}.ppg .pg-by b{font-size:11.5px;white-space:normal;line-height:1.15;min-width:0}.ppg .pg-spchip{height:24px;padding:2px 5px}.ppg .pg-spchip img{height:20px}' + '.ppg .pg-fresh{font-size:10.5px;padding:3px 8px;gap:5px;flex:none}.ppg .pg-fresh i{width:7px;height:7px}.ppg .pg-fresh.pg-fd{display:none}.ppg .pg-fresh.pg-fm{display:inline-flex}.ppg .pg-gr{justify-content:flex-start}.ppg .pg-by span{white-space:nowrap}.ppg .pg-by b{overflow:visible}}' +
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
    '.ppg .pg-sb{display:flex;flex-direction:column;gap:1px}.ppg .pg-sl{display:flex;align-items:baseline;gap:8px;font-size:13px;font-weight:600;color:#cfd8ea}.ppg .pg-sl .pg-sn{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ppg .pg-sl .pg-sc{flex:none;min-width:22px;text-align:right;font-size:14px}.ppg .pg-sl.pg-win{color:#fff;font-weight:800}.ppg .pg-sb + .pg-b{margin-top:2px}' +
    '.ppg .pg-sc{color:#fff;font-weight:900;font-variant-numeric:tabular-nums}@keyframes pgpulse{50%{opacity:.25}}' +
    '.ppg .pg-li .pg-a{font-weight:700;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.ppg .pg-li .pg-b{color:#9fb0cf;font-size:11.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.ppg .pg-dt{flex:none;width:40px;text-align:center;background:#fff;color:#0b1a33;border-radius:5px;padding:3px 0 4px;line-height:1}' +
    '.ppg .pg-dt small{display:block;font-size:9px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#a5161f}' +
    '.ppg .pg-cal .pg-a{white-space:normal;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;line-height:1.25}.ppg .pg-cal .pg-li{align-items:flex-start}' +
    '.ppg .pg-dt b{display:block;font-size:16px;font-weight:800;margin-top:1px}' +
    '.ppg .pg-li.pg-game .pg-dt{box-shadow:inset 0 -3px 0 var(--c)}' +
    '.ppg .pg-none{color:#9fb0cf;font-size:13px;padding:6px 0}' +
    '.ppg a.pg-link{border-radius:6px;transition:background .15s}.ppg a.pg-link:hover{background:rgba(255,255,255,.05)}.ppg a.pg-link:hover .pg-a,.ppg a.pg-link:hover .pg-sn{text-decoration:underline}' +
    '.ppg button.pg-chip{border:1px solid transparent;color:inherit;font-family:inherit;cursor:pointer}.ppg button.pg-chip:hover{border-color:var(--c)}' +
    '.ppg button.pg-chip.pg-on{background:#fff;color:#0b1a33;border-color:#fff}' +
    '.ppg .pg-scroll{max-height:330px;overflow-y:auto;scrollbar-width:thin;padding-right:4px}.ppg .pg-sub.pg-subtop{margin-top:0;padding-top:0;border-top:0;color:#e8b021}' +
    '.ppg .pg-sub{margin:8px 0 2px;padding-top:7px;border-top:1px solid rgba(255,255,255,.12);font-size:10.5px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:#9fb0cf}' +
    '.ppg .pg-go{margin-top:auto;padding-top:9px;font-size:12.5px;font-weight:800;color:#e8b021}' +
    '.ppg .pg-go:hover{text-decoration:underline}' +
    '.ppg .pg-col:hover{border-color:rgba(232,176,33,.45)}' +
    '@media (max-width:820px){.ppg .pg-cols{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;padding-right:14px;scrollbar-width:none}.ppg .pg-cols::-webkit-scrollbar{display:none}.ppg .pg-col{flex:0 0 84%;scroll-snap-align:start}.ppg .pg-gt{font-size:19px}.ppg .pg-gh{padding:12px 14px 8px 18px}}' +
    '@media (max-width:480px){.ppg .pg-gh{padding:10px 12px 8px 14px;gap:7px}.ppg .pg-gk{font-size:9.5px;letter-spacing:.08em}.ppg .pg-gt{font-size:17px}' + '.ppg .pg-gr{padding-top:7px}.ppg .pg-by{gap:5px;font-size:8.5px;letter-spacing:.03em;flex-wrap:nowrap}.ppg .pg-by b{font-size:11px;white-space:normal;line-height:1.15}.ppg .pg-spchip{height:22px;padding:1px 4px}.ppg .pg-spchip img{height:19px}' + '.ppg .pg-cols{gap:8px;padding:0 12px 12px 14px}.ppg .pg-col{flex-basis:88%;padding:10px 10px 8px}.ppg .pg-ch b{font-size:10.5px;letter-spacing:.05em;white-space:nowrap}.ppg .pg-ch span{font-size:11px}' + '.ppg .pg-big{font-size:24px;margin-bottom:6px}.ppg .pg-big small{font-size:12.5px}.ppg .pg-chip{font-size:10.5px;padding:2px 6px}' + '.ppg .pg-li{gap:7px;padding:5px 0}.ppg .pg-li .pg-tm{width:54px;font-size:11px}.ppg .pg-li .pg-a{font-size:12.5px;white-space:normal;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;line-height:1.2}.ppg .pg-li .pg-b{font-size:10.5px}' + '.ppg .pg-li.pg-scored{flex-wrap:wrap;row-gap:2px}.ppg .pg-li.pg-scored .pg-tm{width:100%}.ppg .pg-sl .pg-sn{white-space:normal;line-height:1.2}' +  '.ppg .pg-sl{font-size:12.5px}.ppg .pg-sl .pg-sc{font-size:13px}.ppg .pg-dt{width:36px}.ppg .pg-go{font-size:12px}}' +
    '.ppg .pg-tip{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:4px 8px;margin:0 14px 12px 18px;padding:9px 12px;border-radius:8px;background:rgba(232,176,33,.1);border:1px dashed rgba(232,176,33,.45);font-size:13px;color:#dbe3f2;text-align:center}' +
    '.ppg .pg-tip b{color:#e8b021;font-weight:800}.ppg .pg-tip .pg-tipm,.ppg .pg-tip .pg-tipa{display:none}.ppg .pg-tipa{flex-basis:100%;font-size:11.5px;color:#9fb0cf}.ppg .pg-tip:hover{background:rgba(232,176,33,.18)}' +
    '@media (max-width:480px){.ppg .pg-tip{margin:0 12px 10px 14px;font-size:12px;padding:8px 10px}.ppg .pg-tip .pg-tipd{display:none}.ppg .pg-tip .pg-tipm{display:inline}.ppg .pg-tip .pg-tipa{display:block}}' +
    '.ppg.compact .pg-gt{font-size:18px}.ppg.compact .pg-big{font-size:24px}' +
    /* the Pro Hub line: two scores for our pro teams and a link to the Pro Hub */
    '.ppg .pg-pro{display:flex;align-items:center;gap:10px 14px;margin:0 14px 12px 18px;padding:10px 12px;border-radius:10px;background:rgba(8,20,40,.55);border:1px solid rgba(255,255,255,.08);flex-wrap:wrap}' +
    '.ppg a.pg-pg:hover{background:rgba(255,255,255,.12)}.ppg .pg-prog:hover{text-decoration:underline}' +
    '.ppg .pg-prol{display:flex;flex-direction:column;flex:none}.ppg .pg-prol b{font-size:12px;font-weight:800;letter-spacing:.1em;text-transform:uppercase}.ppg .pg-prol span{color:#9fb0cf;font-size:11px}' +
    '.ppg .pg-pros{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;flex:1;min-width:0}' +
    '.ppg .pg-pros .pg-pg{flex-direction:column;justify-content:center;gap:3px;text-align:center}.ppg .pg-pros .pg-pg em{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}' +
    '.ppg .pg-pg{display:flex;align-items:center;flex-wrap:wrap;gap:8px;max-width:100%;background:rgba(255,255,255,.06);border-radius:6px;padding:6px 10px;font-size:13px;font-weight:700;min-width:0;white-space:nowrap}' +
    '.ppg .pg-pg em{font-style:normal;font-size:10.5px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#9fb0cf}.ppg .pg-pg em.pg-live{color:#ff4d4d}' +
    '.ppg .pg-pg .pg-sc{color:#fff}.ppg .pg-pg .pg-lo{color:#9fb0cf;font-weight:600}' +
    '.ppg{-webkit-text-size-adjust:100%;text-size-adjust:100%}' +
    '.ppg .pg-row{display:inline-flex;align-items:center;gap:8px;white-space:nowrap;flex:none}' +
    '.ppg .pg-tm2{display:inline-flex;align-items:center;gap:6px}.ppg .pg-tm2 img{width:24px;height:24px;object-fit:contain;display:block}' +
    '.ppg .pg-tm2.pg-lo img{opacity:.55}.ppg .pg-tm2.pg-lo .pg-sc{color:#9fb0cf}.ppg .pg-at{color:#9fb0cf;font-weight:600}.ppg .pg-ab{font-size:12px;letter-spacing:.04em}' +
    '.ppg .pg-prog{flex:none;font-size:12.5px;font-weight:800;color:#e8b021;white-space:nowrap}' +
    '@media (max-width:640px){.ppg .pg-pro{margin:0 12px 10px 14px;padding:9px 10px;gap:8px}.ppg .pg-prol{flex-direction:row;align-items:baseline;gap:8px;width:100%;justify-content:space-between}' +
    '.ppg .pg-pros{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));width:100%;gap:8px}' + '.ppg .pg-pros .pg-pg{min-width:0;justify-content:center;gap:4px 6px;padding:6px 6px;font-size:12.5px}' + '.ppg .pg-pros .pg-pg em{width:100%;text-align:center;font-size:9.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' + '.ppg .pg-tm2{gap:3px}.ppg .pg-tm2 img{width:18px;height:18px}.ppg .pg-prog{width:100%;text-align:center}' + '.ppg .pg-row{flex-wrap:nowrap;gap:4px;font-size:12px;letter-spacing:-.01em}.ppg .pg-row .pg-at{font-size:10.5px}.ppg .pg-pros .pg-pg{padding:6px 3px;overflow:hidden}.ppg .pg-ab{font-size:10.5px}.ppg .pg-big3 .pg-at{display:none}.ppg .pg-big3 .pg-row{gap:5px}}';
  var PRO_HUB = 'https://www.powerplaywindsor.com/local-sports';
  var PRO_LG = { nfl: 'football/nfl', nhl: 'hockey/nhl', nba: 'basketball/nba', mlb: 'baseball/mlb' };
  var PRO_OURS = { nhl: ['DET', 'TOR', 'MTL'], nba: ['DET', 'TOR'], nfl: ['DET', 'BUF'], mlb: ['DET', 'TOR'], ncaaf: ['MICH', 'MSU'], ncaam: ['MICH', 'MSU'] };

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

  var PICK = null, redraw = null;   // the team picked in Today's games, and a way to redraw the guide
  var TEAMNAME = { spitfires: 'Spitfires', lancers: 'Lancers', saints: 'Saints', junior: 'Junior hockey', highschool: 'High school' };
  var box_live = false, pro_live = false;   // any game live right now (refresh every minute instead of every five)
  // our pro teams (ESPN, live): two games for the Pro Hub line. A live game first, then today's finals,
  // then yesterday's, otherwise the next games coming up.
  function proGames() {
    var now = new Date(), days = [-1, 0, 1].map(function (n) { return dayKey(new Date(now.getTime() + n * 864e5)); });
    var jobs = [];
    Object.keys(PRO_LG).forEach(function (lg) {
      days.forEach(function (k, n) {
        jobs.push(fetch('https://site.api.espn.com/apis/site/v2/sports/' + PRO_LG[lg] + '/scoreboard?dates=' + k.replace(/-/g, ''))
          .then(function (r) { return r.ok ? r.json() : { events: [] }; }).catch(function () { return { events: [] }; })
          .then(function (j) {
            return (j.events || []).map(function (e) {
              var c = e.competitions[0], st = e.status.type;
              var side = function (h) { var x = c.competitors.filter(function (t) { return t.homeAway === h; })[0];
                return { abbr: x.team.abbreviation, name: x.team.shortDisplayName || x.team.name, logo: x.team.logo || '', score: x.score, win: x.winner }; };
              var ls = e.links || [], by = function (r) { var x = ls.filter(function (l) { return (l.rel || []).indexOf(r) >= 0; })[0]; return x && x.href; };
              var link = st.state === 'post' ? (by('recap') || by('boxscore') || by('summary')) : (by('summary') || by('preview'));
              return { lg: lg, start: e.date, state: st.state, detail: st.shortDetail || '', away: side('away'), home: side('home'), day: n - 1, off: /POSTPONED|CANCELED/.test(st.name), link: link || '' };
            }).filter(function (g) { return !g.off && (PRO_OURS[lg].indexOf(g.home.abbr) >= 0 || PRO_OURS[lg].indexOf(g.away.abbr) >= 0); });
          }));
      });
    });
    return Promise.all(jobs).then(function (r) {
      var all = [].concat.apply([], r), seen = {};
      all = all.filter(function (g) { var k = g.lg + g.start + g.home.abbr; if (seen[k]) return false; seen[k] = 1; return true; });
      var newest = function (a, b) { return b.start.localeCompare(a.start); };
      var live = all.filter(function (g) { return g.state === 'in'; });
      var fin0 = all.filter(function (g) { return g.state === 'post' && g.day === 0; }).sort(newest);
      var fin1 = all.filter(function (g) { return g.state === 'post' && g.day === -1; }).sort(newest);
      var next = all.filter(function (g) { return g.state === 'pre' && new Date(g.start) > now; }).sort(function (a, b) { return a.start.localeCompare(b.start); });
      return live.concat(fin0, fin1, next).slice(0, 4);
    }).catch(function () { return []; });
  }
  function load() {
    return Promise.all([getJSON('local-games.json'), getJSON('saints.json'), getJSON('highschool.json'), getJSON('calendar.json'), Promise.resolve([])]).then(function (r) {
      var lg = r[0] || {}, sc = r[1], hs = r[2], cal = r[3];
      var all = (lg.games || []).slice();
      if (sc && sc.games) all = all.filter(function (g) { return !(g.team === 'saints' && g.sport !== 'Football'); })
        .concat(sc.games.filter(function (g) { return g.sport !== 'Football'; }));
      if (hs && hs.games) all = all.filter(function (g) { return g.team !== 'highschool'; }).concat(hs.games);
      var seen = {};
      all = all.filter(function (g) { var k = g.id || (g.team + g.start + g.opponent); if (seen[k]) return false; seen[k] = 1; return true; });
      var upd = [lg.updated, sc && sc.updated, hs && hs.updated, cal && cal.updated].filter(Boolean).map(function (u) { return new Date(u).getTime(); });
      pro_live = (r[4] || []).some(function (g) { return g.state === 'in'; });
      return { games: all, events: (cal && cal.events) || [], updated: upd.length ? Math.max.apply(null, upd) : 0, pro: r[4] || [] };
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

  // two lines, scoreboard style: each team with its score at the right edge, so the score never gets cut off on a phone
  function scoreBox(rows) {   // rows: [[name, score, winner?], [name, score, winner?]]
    var b = el('div', 'pg-sb');
    rows.forEach(function (r) {
      var line = el('div', 'pg-sl' + (r[2] ? ' pg-win' : ''));
      line.appendChild(el('span', 'pg-sn', r[0])); line.appendChild(el('b', 'pg-sc', String(r[1] == null ? 0 : r[1])));
      b.appendChild(line);
    });
    return b;
  }

  // every game in the guide is a link: the game centre / box score / recap when the league has one,
  // otherwise the Local Hub (scores for live and final games, Coming Up for the rest)
  function gameRow(g, target) {
    var L = g.links || {}, live = g.status === 'live', fin = g.status === 'final';
    var u = live ? (L.gamecentre || L.boxscore || L.powerplay) : fin ? (L.powerplay || L.recap || L.boxscore || L.gamecentre) : (L.gamecentre || L.powerplay);
    var a = el('a', 'pg-li pg-link');
    if (u) { a.href = u; if (u.indexOf('powerplaywindsor.com') >= 0) a.target = target; else { a.target = '_blank'; a.rel = 'noopener'; } }
    else { a.href = live || fin ? hubLink('scores') : hubLink('upcoming') + '&day=' + dayKey(new Date(g.start)); a.target = target; }
    return a;
  }

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
    if (PICK && !count[PICK]) PICK = null;
    // tap a team to list all of its games today (tap it again for everything)
    var chips = el('div', 'pg-chips');
    Object.keys(count).sort(function (a, b) { return RANK[a] - RANK[b]; }).forEach(function (t) {
      var c = el('button', 'pg-chip' + (PICK === t ? ' pg-on' : '')); c.type = 'button';
      c.setAttribute('aria-pressed', String(PICK === t));
      c.style.setProperty('--c', COLOR[t] || '#e8b021'); c.appendChild(el('i'));
      c.appendChild(document.createTextNode(TEAMNAME[t] + ' ' + count[t]));
      c.onclick = function (e) { e.preventDefault(); e.stopPropagation(); PICK = PICK === t ? null : t; if (redraw) redraw(); };
      chips.appendChild(c);
    });
    col.appendChild(chips);
    var now = Date.now();
    var stale = function (g) { return g.status === 'live' && now - new Date(g.start).getTime() > 4 * 3600e3; };   // data behind: don't show it as live
    var isLive = function (g) { return g.status === 'live' && !stale(g); };
    var scored = function (g) { return g.our_score != null && g.opp_score != null; };
    var n = compact ? 3 : 5;
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
    if (PICK) {     // one team picked: every one of its games today, live first, then by start time
      pick = mine.filter(function (g) { return g.team === PICK && g.status !== 'cancelled'; })
        .sort(function (a, b) { return (isLive(a) ? 0 : 1) - (isLive(b) ? 0 : 1) || (a.time_tbd ? 1 : 0) - (b.time_tbd ? 1 : 0) || (a.start < b.start ? -1 : 1); });
    }
    // room left (a quiet day): the next day's games fill the column, under their own label
    var nextDay = '', extra = [];
    if (!compact && !PICK && pick.length < n) {
      nextDay = future.map(function (g) { return dayKey(new Date(g.start)); }).filter(function (k) { return k > day; }).sort()[0] || '';
      if (nextDay) extra = future.filter(function (g) { return dayKey(new Date(g.start)) === nextDay && g.status !== 'cancelled'; })
        .sort(function (a, b) { return (RANK[a.team] - RANK[b.team]) || (a.start < b.start ? -1 : 1); }).slice(0, n - pick.length)
        .sort(function (a, b) { return (a.time_tbd ? 1 : 0) - (b.time_tbd ? 1 : 0) || (a.start < b.start ? -1 : 1); });
    }
    var list = el('div', PICK ? 'pg-scroll' : null);
    if (PICK) list.appendChild(el('div', 'pg-sub pg-subtop', TEAMNAME[PICK] + ' \u00b7 ' + pick.length + (pick.length === 1 ? ' game' : ' games') + ' \u00b7 tap again for all'));
    pick.concat(extra.length ? ['divider'] : [], extra).forEach(function (g) {
      if (g === 'divider') {
        list.appendChild(el('div', 'pg-sub', (nextDay === dayKey(new Date(Date.now() + 864e5)) && day === today ? 'Tomorrow' : wd(nextDay)) + ' \u00b7 ' + wd(nextDay).slice(0, 3) + '., ' + cpDate(nextDay)));
        return;
      }
      var s = sides(g), li = gameRow(g, target); li.style.setProperty('--c', COLOR[g.team] || '#e8b021');
      var lv = isLive(g), fin = g.status === 'final';
      var started = !g.time_tbd && g.status === 'upcoming' && new Date(g.start).getTime() < now && now - new Date(g.start).getTime() < 3 * 3600e3;
      var tm = el('div', 'pg-tm' + (lv ? ' pg-live' : fin ? ' pg-fin' : ''),
        lv ? 'LIVE' : fin ? 'Final' : g.status === 'postponed' ? 'PPD' : started ? 'Now' : g.time_tbd ? 'TBA' : cpTime(new Date(g.start)));
      li.appendChild(tm);
      var tx = el('div', 'pg-tx'), a = el('div', 'pg-a');
      if ((lv || fin) && (scored(g) || lv)) {     // away over home, scores lined up on the right
        li.classList.add('pg-scored');
        a = scoreBox([[s[0], s[2], fin && +s[2] > +s[3]], [s[1], s[3], fin && +s[3] > +s[2]]]);
      } else a.textContent = s[0] + (g.home_away === 'N' && !(g.home && g.away) ? ' vs. ' : ' at ') + s[1];
      tx.appendChild(a);
      tx.appendChild(el('div', 'pg-b', label(g) + (lv && (g.detail || g.note) ? ' · ' + (g.detail || g.note) : ''))); li.appendChild(tx); list.appendChild(li);
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
    var n = compact ? 4 : 6, show = ours.slice(0, Math.max(n - Math.min(2, hsg.length), 0));
    show = show.concat(hsg.slice(0, n - show.length));
    colHead(col, 'Latest scores', fin.length ? fin.length + ' finals' : '');
    if (!show.length) col.appendChild(el('div', 'pg-none', 'No local finals in the last two days.'));
    show.forEach(function (g) {
      var s = sides(g), li = gameRow(g, target); li.style.setProperty('--c', COLOR[g.team] || '#e8b021'); li.appendChild(el('i'));
      var w = +s[2] >= +s[3] ? [s[0], s[2], s[1], s[3]] : [s[1], s[3], s[0], s[2]];
      var tx = el('div', 'pg-tx'); tx.appendChild(scoreBox([[w[0], w[1], +w[1] !== +w[3]], [w[2], w[3], false]]));   // winner on top
      var k = dayKey(new Date(g.start));
      tx.appendChild(el('div', 'pg-b', label(g) + ' · ' + (k === dayKey(new Date()) ? 'Today' : k === dayKey(new Date(Date.now() - 864e5)) ? 'Yesterday' : wd(k))));
      li.appendChild(tx); col.appendChild(li);
    });
    goLink(col, 'All local scores', hubLink('scores'), target);
    return col;
  }

  // 3. Community Calendar: what's on in the community, from your event posts
  // when there aren't enough Community Calendar posts, upcoming home games fill the rest:
  // Spitfires, Lancers and Saints first, then the Flyers, Vipers and the local PJHL clubs (next 7 days)
  var CAL_CLUBS = /^(leamington flyers|lasalle vipers|lakeshore canadiens|essex 73'?s|wheatley sharks|amherstburg admirals)$/i;
  function calTier(g) { return g.team === 'spitfires' ? 0 : g.team === 'lancers' ? 1 : g.team === 'saints' ? 2 : g.team === 'junior' && CAL_CLUBS.test(g.club || '') ? 3 : g.team === 'junior' ? 4 : 9; }
  function gameEvents(games, n, skipDay) {
    if (n <= 0) return [];
    var now = Date.now(), week = now + 14 * 864e5;   // the next two weeks
    var pool = games.filter(function (g) {
      var t = new Date(g.start).getTime();
      return g.home_away === 'H' && calTier(g) < 9 && g.status !== 'final' && g.status !== 'cancelled' && g.status !== 'postponed' && t > now && t < week;
    });
    var later = pool.filter(function (g) { return dayKey(new Date(g.start)) !== skipDay; });
    if (later.length) pool = later;                       // Today's games are already listed beside it
    pool.sort(function (a, b) { return calTier(a) - calTier(b) || (a.start < b.start ? -1 : 1); });
    return pool.slice(0, n).map(function (g) {
      var who = g.team === 'spitfires' ? 'Spitfires' : g.team === 'lancers' ? 'Lancers ' + String(g.sport || '').toLowerCase()
        : g.team === 'saints' ? 'Saints ' + String(g.sport || '').toLowerCase() : (g.club || '');
      return { game: true, team: g.team, date: dayKey(new Date(g.start)), start: g.start, headline: who + ' vs. ' + g.opponent,
        when: g.time_tbd ? 'Time TBA' : cpTime(new Date(g.start)), where: g.location || '',
        url: hubLink('upcoming') + '&day=' + dayKey(new Date(g.start)) };
    });
  }

  // an event post is "over" once its day has passed, or on the day itself once its time has passed:
  // "7:10 p.m." -> gone 3 hours after the start; "1 to 4 p.m." -> gone an hour after it ends; no time -> end of the day
  function evOver(e, today) {
    var last = e.end || e.date;
    if (last < today) return true;
    if (last > today) return false;
    var re = /(\d{1,2})(?::(\d\d))?\s*([ap])\.?\s*m\b\.?/gi, m, t = null, n = 0;
    var txt = String(e.when || '');
    var range = /\d\s*(?:-|–|to)\s*\d{1,2}(?::\d\d)?\s*[ap]\.?\s*m/i.test(txt);
    while ((m = re.exec(txt))) { var h = (+m[1] % 12) + (m[3].toLowerCase() === 'p' ? 12 : 0); t = h * 60 + (+(m[2] || 0)); n++; }
    if (t === null) return false;
    var nowP = {}; new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Toronto', hour: 'numeric', minute: '2-digit', hourCycle: 'h23' })
      .formatToParts(new Date()).forEach(function (x) { nowP[x.type] = x.value; });
    var nowMin = (+nowP.hour) * 60 + (+nowP.minute);
    return nowMin > t + (range || n > 1 ? 60 : 180);
  }

  function calCol(d, target, compact) {
    var col = el('div', 'pg-col pg-cal'), today = dayKey(new Date());
    var max = compact ? 3 : 6;
    var evs = d.events.filter(function (e) { return !evOver(e, today); }).slice(0, max);
    evs = evs.concat(gameEvents(d.games, max - evs.length, today))
      .sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : (a.game ? 1 : 0) - (b.game ? 1 : 0) || ((a.start || '') < (b.start || '') ? -1 : 1); });
    colHead(col, 'Coming Up', evs.length ? 'Events & games' : '');
    if (!evs.length) col.appendChild(el('div', 'pg-none', 'New community events are posted here as they are announced.'));
    evs.forEach(function (e) {
      var a = el('a', 'pg-li' + (e.game ? ' pg-game' : '')); a.href = e.url; a.target = target;
      if (e.game) a.style.setProperty('--c', COLOR[e.team] || '#e8b021');
      var dt = el('div', 'pg-dt'), nd = noon(e.date);
      dt.appendChild(el('small', null, e.date === today ? 'Today' : MON[nd.getMonth()].replace('.', '').slice(0, 4)));
      dt.appendChild(el('b', null, String(nd.getDate()))); a.appendChild(dt);
      var tx = el('div', 'pg-tx'); tx.appendChild(el('div', 'pg-a', e.headline));
      tx.appendChild(el('div', 'pg-b', [e.when, e.where].filter(Boolean).join(' · '))); a.appendChild(tx);
      col.appendChild(a);
    });
    goLink(col, 'See everything coming up', hubLink('upcoming'), target);
    return col;
  }

  function proLine(list, target) {
    var a = el('div', 'pg-pro');
    var l = el('a', 'pg-prol'); l.href = PRO_HUB; l.target = target; l.appendChild(el('b', null, 'National Hub')); l.appendChild(el('span', null, 'Presented by Scarehouse Windsor')); a.appendChild(l);
    var gs = el('div', 'pg-pros');
    if (!list.length) { var nn = el('span', 'pg-pg', 'Wings, Leafs, Habs, Lions, Bills, Pistons, Raptors, Tigers and Jays'); nn.style.gridColumn = '1 / -1'; nn.style.whiteSpace = 'normal'; nn.style.textAlign = 'center'; gs.appendChild(nn); }
    list.forEach(function (g) {
      var c = el('a', 'pg-pg'), st;          // tap a score: the game on ESPN (gamecast, recap or preview)
      if (g.link) { c.href = g.link; c.target = '_blank'; c.rel = 'noopener'; } else { c.href = PRO_HUB; c.target = target; }
      if (g.state === 'in') st = el('em', 'pg-live', 'Live \u00b7 ' + g.detail);
      else if (g.state === 'post') st = el('em', null, g.day === -1 ? 'Final \u00b7 ' + wd(dayKey(new Date(g.start))).slice(0, 3) + '.' : 'Final');
      else { var k = dayKey(new Date(g.start)), today = dayKey(new Date()); st = el('em', null, (k === today ? 'Today' : wd(k).slice(0, 3) + '.') + ' \u00b7 ' + cpTime(new Date(g.start))); }
      c.appendChild(st);
      // each team: its logo (the abbreviation if the logo won't load) and its score, side by side
      var rowEl = el('span', 'pg-row'); c.appendChild(rowEl);
      [g.away, g.home].forEach(function (t, i) {
        if (i) rowEl.appendChild(el('span', 'pg-at', '@'));
        var sp = el('span', 'pg-tm2' + (g.state === 'post' && !t.win ? ' pg-lo' : ''));
        sp.title = t.name;
        if (t.logo) {
          var im = new Image(); im.alt = t.name; im.src = t.logo; im.referrerPolicy = 'no-referrer';
          im.onerror = function () { im.replaceWith(el('b', 'pg-ab', t.abbr)); };
          sp.appendChild(im);
        } else sp.appendChild(el('b', 'pg-ab', t.abbr));
        if (g.state !== 'pre') sp.appendChild(el('span', 'pg-sc', String(t.score)));
        rowEl.appendChild(sp);
      });
      if (g.state !== 'pre' && (String(g.away.score).length > 2 || String(g.home.score).length > 2)) c.classList.add('pg-big3');
      gs.appendChild(c);
    });
    a.appendChild(gs);
    // never cut a score off: shrink a row that's still too wide for its box (three-digit basketball scores on phones)
    function fit() {
      Array.prototype.forEach.call(gs.querySelectorAll('.pg-row'), function (r) {
        r.style.transform = ''; r.style.alignSelf = ''; r.style.transformOrigin = '';
        var room = r.parentNode.clientWidth - 6, w = r.scrollWidth;
        if (room > 0 && w > room) {
          var k = Math.max(0.6, room / w);
          r.style.alignSelf = 'flex-start'; r.style.transformOrigin = 'left center';
          var off = r.getBoundingClientRect().left - r.parentNode.getBoundingClientRect().left - r.parentNode.clientLeft;
          r.style.transform = 'translateX(' + ((r.parentNode.clientWidth - w * k) / 2 - off).toFixed(1) + 'px) scale(' + k.toFixed(3) + ')';
        }
      });
    }
    var fitT = function () { requestAnimationFrame(fit); };
    setTimeout(fitT, 0); setTimeout(fitT, 400); setTimeout(fitT, 1500);
    window.addEventListener('resize', fitT);
    gs.addEventListener('load', fitT, true);
    var go = el('a', 'pg-prog', 'Every pro score \u203a'); go.href = PRO_HUB; go.target = target; a.appendChild(go);
    return a;
  }


  // ================= the Pro Sports Guide (the Pro Hub's Scores tab): render(box, { mode: 'pro' }) =================
  // the same look as the local guide, for every pro game: today's games and scores together (live first, then
  // tonight's games, today's finals and last night's scores), and the next three days. Our teams' games come first
  // in each group. Tap a league to see just its games, then pick a team from the drop-down.
  // NHL, NFL, NBA and MLB live from ESPN's scoreboards; the CFL and PWHL from data/local-games.json.
  // U.S. college: the Big Ten's games (ESPN group 5 = Big Ten football, 7 = Big Ten men's basketball), Michigan and Michigan State marked as ours
  var PRO_PATH = { nhl: 'hockey/nhl', nfl: 'football/nfl', nba: 'basketball/nba', mlb: 'baseball/mlb', ncaaf: 'football/college-football', ncaam: 'basketball/mens-college-basketball' };
  var PRO_GROUP = { ncaaf: 5, ncaam: 7 };
  var PRO_NAME = { nhl: 'NHL', nfl: 'NFL', nba: 'NBA', mlb: 'MLB', cfl: 'CFL', pwhl: 'PWHL', ncaaf: 'NCAA FB', ncaam: 'NCAA BB' };
  var PRO_COLOR = { nhl: '#94a3b8', nfl: '#1d4ed8', nba: '#ea580c', mlb: '#0891b2', cfl: '#dc2626', pwhl: '#7c3aed', ncaaf: '#a3e635', ncaam: '#2dd4bf' };
  var PRO_RANK = { nhl: 0, nfl: 1, nba: 2, mlb: 3, cfl: 4, pwhl: 5, ncaaf: 6, ncaam: 7 };
  var PRO_LOCAL = { cfl: /argonauts|tiger-cats/i, pwhl: /sceptres/i };
  var PPICK = { lg: '', team: '', more1: false, more2: false };
  var proNews = [], proVids = [], TICK_LG = '', tickScroll = 0, vidOpen = null;   // the National Hub's top: news, the scores bar's league and where it was scrolled   // the league and team picked, and "show all"
  function proHubLink(tab) { return PRO_HUB + '?tab=' + tab; }
  function nick(n) { n = String(n || ''); var w = n.split(' '), two = w.length > 2 && /^(red|maple|blue|golden|white|trail|black|tiger)$/i.test(w[w.length - 2]); return w.slice(two ? -2 : -1).join(' ') || n; }
  function espnGame(lg, e) {
    var c = e.competitions && e.competitions[0]; if (!c) return null;
    var st = (c.status && c.status.type) || (e.status && e.status.type) || {};
    if (/POSTPONED|CANCELED|CANCELLED/.test(st.name || '')) return null;
    var side = function (h) { var x = c.competitors.filter(function (t) { return t.homeAway === h; })[0]; if (!x) return null;
      var sc = x.score == null ? null : typeof x.score === 'object' ? x.score.displayValue : x.score;
      return { abbr: x.team.abbreviation, name: x.team.shortDisplayName || x.team.name || x.team.displayName, full: x.team.displayName || '', score: sc, win: !!x.winner, logo: x.team.logo || '' }; };
    var away = side('away'), home = side('home'); if (!away || !home) return null;
    var ls = e.links || [], by = function (r) { var x = ls.filter(function (l) { return (l.rel || []).indexOf(r) >= 0; })[0]; return x && x.href; };
    return { lg: lg, start: e.date, state: st.state, detail: st.shortDetail || '', away: away, home: home, tbd: e.timeValid === false,
             ours: PRO_OURS[lg].indexOf(away.abbr) >= 0 || PRO_OURS[lg].indexOf(home.abbr) >= 0,
             venue: c.venue && c.venue.fullName || '', link: by('summary') || by('boxscore') || by('recap') || '' };
  }
  function proLoad() {
    var jobs = [], now = new Date();
    var days = [-1, 0, 1, 2, 3].map(function (n) { return dayKey(new Date(now.getTime() + n * 864e5)); });
    Object.keys(PRO_PATH).forEach(function (lg) {
      days.forEach(function (k) {
        jobs.push(fetch('https://site.api.espn.com/apis/site/v2/sports/' + PRO_PATH[lg] + '/scoreboard?dates=' + k.replace(/-/g, '') + (lg === 'nba' || lg === 'nhl' ? '&limit=100' : '') + (PRO_GROUP[lg] ? '&groups=' + PRO_GROUP[lg] + '&limit=200' : ''))
          .then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; })
          .then(function (j) { return (j.events || []).map(function (e) { return espnGame(lg, e); }).filter(Boolean); }));
      });
    });
    jobs.push(getJSON('network.json').then(function (j) { proVids = (j && j.pro) || []; return []; }));
    jobs.push(getJSON('local-games.json').then(function (j) {
      proNews = ((j && j.pro_news) || []).concat((j && j.more_news) || []);
      return ((j && j.pro_games) || []).concat((j && j.pro_ahead) || []).map(function (g) {
        var lg = g.league || g.team; if (!PRO_LOCAL[lg] || g.status === 'postponed' || g.status === 'cancelled') return null;
        var fin = g.status === 'final';
        return { lg: lg, start: g.start, state: fin ? 'post' : g.status === 'live' ? 'in' : 'pre', detail: g.note || '', tbd: g.time_tbd,
                 ours: PRO_LOCAL[lg].test((g.home || '') + ' ' + (g.away || '')),
                 away: { abbr: g.away_abbr, name: nick(g.away), full: g.away, score: g.our_score, win: fin && g.our_score > g.opp_score },
                 home: { abbr: g.home_abbr, name: nick(g.home), full: g.home, score: g.opp_score, win: fin && g.opp_score > g.our_score },
                 venue: g.location || '', link: g.link || (g.links && g.links.gamecentre) || '' };
      }).filter(Boolean);
    }));
    return Promise.all(jobs).then(function (r) {
      var by = {};
      [].concat.apply([], r).forEach(function (g) { var k = g.lg + dayKey(new Date(g.start)) + g.home.abbr + g.away.abbr; by[k] = g; });
      var all = Object.keys(by).map(function (k) { return by[k]; }).filter(function (g) { var k = dayKey(new Date(g.start)); return k >= days[0] && k <= days[4]; })
        .sort(function (a, b) { return a.start < b.start ? -1 : 1; });
      pro_live = all.some(function (g) { return g.state === 'in'; });
      return { pro: all, updated: Date.now() };
    });
  }
  // the league and team the fan picked
  function proShown(d) {
    return d.pro.filter(function (g) { return (!PPICK.lg || g.lg === PPICK.lg) && (!PPICK.team || g.home.abbr === PPICK.team || g.away.abbr === PPICK.team); });
  }
  function proRow(g, target) {
    var a = el('a', 'pg-li pg-link' + (g.ours ? ' pg-ours' : '')); a.href = g.link || proHubLink(g.lg); a.target = g.link ? '_blank' : target; if (g.link) a.rel = 'noopener';
    a.style.setProperty('--c', PRO_COLOR[g.lg]); return a;
  }
  function proGameLine(g, target, showDay) {
    var li = proRow(g, target), lv = g.state === 'in', fin = g.state === 'post';
    li.appendChild(el('div', 'pg-tm' + (lv ? ' pg-live' : fin ? ' pg-fin' : ''), lv ? 'LIVE' : fin ? 'Final' : g.tbd ? 'TBA' : cpTime(new Date(g.start))));
    var tx = el('div', 'pg-tx');
    if ((lv || fin) && g.away.score != null && g.home.score != null) { li.classList.add('pg-scored'); tx.appendChild(scoreBox([[g.away.name, g.away.score, fin && g.away.win], [g.home.name, g.home.score, fin && g.home.win]])); }
    else tx.appendChild(el('div', 'pg-a', g.away.name + ' at ' + g.home.name));
    var bits = [PRO_NAME[g.lg]];
    if (lv && g.detail) bits.push(g.detail); else if (fin && /OT|SO|\//.test(g.detail)) bits.push(g.detail.replace(/^Final\/?/, ''));
    if (showDay) bits.push(showDay);
    tx.appendChild(el('div', 'pg-b', bits.join(' · '))); li.appendChild(tx);
    return li;
  }
  var proOrder = function (a, b) { return (b.ours ? 1 : 0) - (a.ours ? 1 : 0) || (a.start < b.start ? -1 : 1) || PRO_RANK[a.lg] - PRO_RANK[b.lg]; };
  function moreBtn(list, n, key, label) {
    var b = el('button', 'pg-more', label); b.type = 'button';
    b.onclick = function (e) { e.preventDefault(); e.stopPropagation(); PPICK[key] = true; if (redraw) redraw(); };
    list.appendChild(b);
  }
  // league chips (all of today's games) and, once a league is picked, a drop-down of its teams
  var proTeams = {};
  function proPicker(d, col) {
    var today = dayKey(new Date()), count = {};
    d.pro.forEach(function (g) { var k = dayKey(new Date(g.start)); if (k === today || (g.state === 'in')) count[g.lg] = (count[g.lg] || 0) + 1; });
    var chips = el('div', 'pg-chips');
    var all = el('button', 'pg-chip' + (!PPICK.lg ? ' pg-on' : ''), 'All'); all.type = 'button'; all.style.setProperty('--c', '#e8b021');
    all.onclick = function (e) { e.preventDefault(); e.stopPropagation(); PPICK = { lg: '', team: '' }; if (redraw) redraw(); }; chips.appendChild(all);
    ['nhl', 'nfl', 'nba', 'mlb', 'cfl', 'pwhl', 'ncaaf', 'ncaam'].forEach(function (lg) {
      var on = d.pro.some(function (g) { return g.lg === lg; }); if (!on) return;
      var c = el('button', 'pg-chip' + (PPICK.lg === lg ? ' pg-on' : '')); c.type = 'button'; c.style.setProperty('--c', PRO_COLOR[lg]); c.appendChild(el('i'));
      c.appendChild(document.createTextNode(PRO_NAME[lg] + (count[lg] ? ' ' + count[lg] : '')));
      c.onclick = function (e) { e.preventDefault(); e.stopPropagation(); PPICK = { lg: PPICK.lg === lg ? '' : lg, team: '' }; if (redraw) redraw(); };
      chips.appendChild(c);
    });
    col.appendChild(chips);
    if (!PPICK.lg) return;
    var lg = PPICK.lg, sel = el('select', 'pg-sel'); sel.setAttribute('aria-label', 'Pick a ' + PRO_NAME[lg] + ' team');
    sel.appendChild(new Option('All ' + PRO_NAME[lg] + ' teams', ''));
    var fill = function (list) { list.forEach(function (t) { sel.appendChild(new Option(t.name, t.abbr)); }); sel.value = PPICK.team; };
    if (proTeams[lg]) fill(proTeams[lg]);
    else {
      var seen = {}, list = [];
      d.pro.forEach(function (g) { if (g.lg !== lg) return; [g.away, g.home].forEach(function (t) { if (t.abbr && !seen[t.abbr]) { seen[t.abbr] = 1; list.push({ abbr: t.abbr, name: t.full || t.name }); } }); });
      var done = function (l) { proTeams[lg] = l.sort(function (a, b) { return a.name.localeCompare(b.name); }); fill(proTeams[lg]); };
      if (PRO_PATH[lg]) fetch('https://site.api.espn.com/apis/v2/sports/' + PRO_PATH[lg] + '/standings?level=3').then(function (r) { return r.json(); }).then(function (j) {
          (function walk(n) { if (!n) return; ((n.standings && n.standings.entries) || []).forEach(function (e) { if (!seen[e.team.abbreviation]) { seen[e.team.abbreviation] = 1; list.push({ abbr: e.team.abbreviation, name: e.team.displayName }); } }); (n.children || []).forEach(walk); })(j);
          done(list); }).catch(function () { done(list); });
      else done(list);
    }
    sel.onclick = function (e) { e.stopPropagation(); };
    sel.onchange = function () { PPICK.team = sel.value; PPICK.more1 = PPICK.more2 = false; if (redraw) redraw(); };
    var row = el('div', 'pg-selrow'); row.appendChild(sel);
    var go = el('a', 'pg-tlink', PPICK.team ? 'Team page ›' : PRO_NAME[lg] + ' page ›'); go.href = proHubLink(lg) + (PPICK.team ? '&team=' + PPICK.team.toLowerCase() : ''); go.target = '_top'; row.appendChild(go);
    col.appendChild(row);
  }
  // 1. today's games and scores, together
  function proTodayCol(d, target) {
    var col = el('div', 'pg-col pg-wide'), today = dayKey(new Date()), yest = dayKey(new Date(Date.now() - 864e5));
    var g = proShown(d);
    var live = g.filter(function (x) { return x.state === 'in'; }).sort(proOrder);
    var tonight = g.filter(function (x) { return x.state === 'pre' && dayKey(new Date(x.start)) === today; }).sort(proOrder);
    var finToday = g.filter(function (x) { return x.state === 'post' && dayKey(new Date(x.start)) === today; }).sort(proOrder);
    var finYest = g.filter(function (x) { return x.state === 'post' && dayKey(new Date(x.start)) === yest; }).sort(proOrder);
    var n = live.length + tonight.length + finToday.length;
    colHead(col, "Today's games & scores", wd(today).slice(0, 3) + '., ' + cpDate(today));
    var big = el('div', 'pg-big', String(n)); big.appendChild(el('small', null, (n === 1 ? 'game today' : 'games today') + (PPICK.team ? '' : PPICK.lg ? ' in the ' + PRO_NAME[PPICK.lg] : ''))); col.appendChild(big);
    proPicker(d, col);
    var list = el('div'), rows = [];
    live.concat(tonight, finToday).forEach(function (x) { rows.push(x); });
    if (finYest.length) { rows.push('Last night'); finYest.forEach(function (x) { rows.push(x); }); }
    var cap = PPICK.more1 || PPICK.team ? rows.length : 10, shown = 0;
    if (!rows.length) list.appendChild(el('div', 'pg-none', PPICK.team ? 'No game today or last night.' : 'No games today.'));
    rows.forEach(function (x) {
      if (shown >= cap) return;
      if (typeof x === 'string') { list.appendChild(el('div', 'pg-sub', x + ' · ' + wd(yest).slice(0, 3) + '., ' + cpDate(yest))); return; }
      list.appendChild(proGameLine(x, target)); shown++;
    });
    var total = rows.filter(function (x) { return typeof x !== 'string'; }).length;
    if (shown < total) moreBtn(list, total, 'more1', 'Show all ' + total + ' games and scores');
    col.appendChild(list);
    return col;
  }
  // 2. the next three days
  function proComingCol(d, target) {
    var col = el('div', 'pg-col'), today = dayKey(new Date());
    var next = proShown(d).filter(function (g) { return g.state === 'pre' && dayKey(new Date(g.start)) > today; });
    colHead(col, 'Coming Up', 'Next three days');
    if (!next.length) col.appendChild(el('div', 'pg-none', PPICK.team ? 'No games in the next three days.' : 'No games in the next three days.'));
    var byDay = {}; next.forEach(function (g) { var k = dayKey(new Date(g.start)); (byDay[k] = byDay[k] || []).push(g); });
    var cap = PPICK.more2 || PPICK.team ? 999 : 10, shown = 0, total = next.length;
    Object.keys(byDay).sort().forEach(function (k) {
      if (shown >= cap) return;
      col.appendChild(el('div', 'pg-sub', (k === dayKey(new Date(Date.now() + 864e5)) ? 'Tomorrow' : wd(k)) + ' · ' + wd(k).slice(0, 3) + '., ' + cpDate(k)));
      byDay[k].sort(proOrder).forEach(function (g) { if (shown >= cap) return; col.appendChild(proGameLine(g, target)); shown++; });
    });
    if (shown < total) moreBtn(col, total, 'more2', 'Show all ' + total + ' games');
    return col;
  }
  var PRO_CSS = '.ppg .pg-cols.pg-two{grid-template-columns:1.25fr 1fr}' +
    '.ppg .pg-li.pg-ours{box-shadow:inset 3px 0 0 #e8b021;padding-left:8px}' +
    '.ppg .pg-more{display:block;width:100%;margin-top:8px;font:inherit;font-size:12.5px;font-weight:800;color:#e8b021;background:rgba(232,176,33,.08);border:1px solid rgba(232,176,33,.35);border-radius:6px;padding:7px;cursor:pointer}' +
    '.ppg .pg-selrow{display:flex;align-items:center;gap:10px;margin:0 0 8px}.ppg .pg-sel{flex:1;min-width:0;font:inherit;font-size:14px;font-weight:700;color:#f2f5fb;background:#132b57;border:1px solid rgba(232,176,33,.6);border-radius:6px;padding:6px 8px}' +
    '.ppg .pg-tlink{flex:none;font-size:12.5px;font-weight:800;color:#e8b021;white-space:nowrap}' +
    '.ppg .pg-chips .pg-chip.pg-on{background:#fff;color:#0b1a33;border-color:#fff}';


  // ---------- National Hub top, like theScore / TSN: a bar of score cards, then the big story and the headlines ----------
  function tkDay(g) {
    var k = dayKey(new Date(g.start)), t = dayKey(new Date());
    return k === t ? 'Today' : k === dayKey(new Date(Date.now() - 864e5)) ? 'Yest.' : k === dayKey(new Date(Date.now() + 864e5)) ? 'Tmrw' : cpDate(k);
  }
  function tkTeam(t, g, showScore, lose) {
    var r = el('div', 'pt-r' + (lose ? ' pt-lose' : ''));
    if (t.logo) { var im = new Image(); im.src = t.logo; im.alt = ''; im.loading = 'lazy'; im.className = 'pt-lg'; im.onerror = function () { im.replaceWith(el('span', 'pt-dot')); }; r.appendChild(im); }
    else { var d = el('span', 'pt-dot'); d.style.background = PRO_COLOR[g.lg]; r.appendChild(d); }
    r.appendChild(el('b', 'pt-ab', t.abbr || nick(t.full || t.name).slice(0, 3).toUpperCase()));
    if (showScore) r.appendChild(el('span', 'pt-sc', t.score == null ? '' : String(t.score)));
    return r;
  }
  function tkCard(g, target) {
    var lv = g.state === 'in', fin = g.state === 'post', sc = (lv || fin) && g.away.score != null && g.home.score != null;
    var a = el('a', 'pt-card' + (lv ? ' pt-livec' : '') + (g.ours ? ' pt-ours' : ''));
    a.href = g.link || proHubLink(g.lg); a.target = g.link ? '_blank' : target; if (g.link) a.rel = 'noopener';
    var rows = el('div', 'pt-rows');
    rows.appendChild(tkTeam(g.away, g, sc, fin && !g.away.win && g.home.win));
    rows.appendChild(tkTeam(g.home, g, sc, fin && !g.home.win && g.away.win));
    a.appendChild(rows);
    var st = el('div', 'pt-st');
    if (lv) { st.appendChild(el('span', 'pt-lv', 'LIVE')); st.appendChild(el('span', 'pt-s2', (g.detail || '').replace(/ - /, ' '))); }
    else if (fin) { st.appendChild(el('span', 'pt-s1', /OT|SO/.test(g.detail) ? g.detail.replace(/^Final\/?/, 'F/') : 'Final')); st.appendChild(el('span', 'pt-s2', tkDay(g))); }
    else { st.appendChild(el('span', 'pt-s1', g.tbd ? 'TBA' : cpTime(new Date(g.start)).replace(' a.m.', ' AM').replace(' p.m.', ' PM'))); st.appendChild(el('span', 'pt-s2', tkDay(g))); }
    st.appendChild(el('span', 'pt-lgn', PRO_NAME[g.lg]));
    a.appendChild(st);
    return a;
  }
  function proTicker(d, target) {
    var wrap = el('div', 'pt-wrap');
    var today = dayKey(new Date()), yest = dayKey(new Date(Date.now() - 864e5));
    var have = {}; d.pro.forEach(function (g) { have[g.lg] = 1; });
    var chips = el('div', 'pt-chips');
    [''].concat(Object.keys(PRO_RANK).filter(function (lg) { return have[lg]; })).forEach(function (lg) {
      var c = el('button', 'pt-chip' + (TICK_LG === lg ? ' pt-on' : ''), lg ? PRO_NAME[lg] : 'All'); c.type = 'button';
      if (lg) c.style.setProperty('--c', PRO_COLOR[lg]);
      c.onclick = function (e) { e.preventDefault(); TICK_LG = lg; tickScroll = 0; if (redraw) redraw(); };
      chips.appendChild(c);
    });
    wrap.appendChild(chips);
    var list = d.pro.filter(function (g) { return !TICK_LG || g.lg === TICK_LG; });
    var k = function (g) { return dayKey(new Date(g.start)); };
    var live = list.filter(function (g) { return g.state === 'in'; });
    var upToday = list.filter(function (g) { return g.state === 'pre' && k(g) === today; });
    var fins = list.filter(function (g) { return g.state === 'post' && (k(g) === today || k(g) === yest); }).sort(function (a, b) { return a.start < b.start ? 1 : -1; });
    var later = list.filter(function (g) { return g.state === 'pre' && k(g) > today; });
    var byOurs = function (a, b) { return (b.ours ? 1 : 0) - (a.ours ? 1 : 0); };
    var cards = live.sort(byOurs).concat(upToday, fins, later).slice(0, 60);
    var row = el('div', 'pt-row'), track = el('div', 'pt-track');
    if (!cards.length) track.appendChild(el('div', 'pt-none', 'No games on the schedule right now.'));
    cards.forEach(function (g) { track.appendChild(tkCard(g, target)); });
    var prev = el('button', 'pt-arr pt-prev', '‹'), next = el('button', 'pt-arr pt-next', '›');
    prev.type = next.type = 'button'; prev.setAttribute('aria-label', 'Earlier games'); next.setAttribute('aria-label', 'More games');
    prev.onclick = function () { track.scrollBy({ left: -track.clientWidth * 0.85, behavior: 'smooth' }); };
    next.onclick = function () { track.scrollBy({ left: track.clientWidth * 0.85, behavior: 'smooth' }); };
    track.addEventListener('scroll', function () { tickScroll = track.scrollLeft; });
    row.appendChild(prev); row.appendChild(track); row.appendChild(next);
    wrap.appendChild(row);
    setTimeout(function () { track.scrollLeft = tickScroll; }, 0);
    return wrap;
  }
  function newsAgo(p) {
    var m = Math.round((Date.now() - new Date(p).getTime()) / 60000);
    if (isNaN(m)) return '';
    if (m < 60) return Math.max(1, m) + ' min ago';
    var h = Math.round(m / 60); if (h < 24) return h + (h === 1 ? ' hour ago' : ' hours ago');
    var dd = Math.round(h / 24); return dd + (dd === 1 ? ' day ago' : ' days ago');
  }
  function proTop() {
    var seen = {}, items = proNews.filter(function (x) { if (!x || !x.headline || !x.url || seen[x.url] || !PRO_NAME[x.league]) return false; /* the hub's leagues only */ seen[x.url] = 1; return true; })
      .sort(function (a, b) { return a.published < b.published ? 1 : -1; });
    if (!items.length) return null;
    var lead = items.filter(function (x) { return x.image; })[0] || items[0];
    var rest = items.filter(function (x) { return x !== lead; }).slice(0, 6);
    var box = el('div', 'pt-top');
    var a = el('a', 'pt-lead'); a.href = lead.url; a.target = '_blank'; a.rel = 'noopener';
    if (lead.image) { var im = new Image(); im.src = lead.image; im.alt = ''; im.referrerPolicy = 'no-referrer'; im.onerror = function () { im.remove(); }; a.appendChild(im); }
    var cap = el('div', 'pt-cap');
    if (lead.league && PRO_NAME[lead.league]) { var t = el('span', 'pt-tag', PRO_NAME[lead.league]); t.style.setProperty('--c', PRO_COLOR[lead.league]); cap.appendChild(t); }
    cap.appendChild(el('div', 'pt-hl', lead.headline));
    cap.appendChild(el('div', 'pt-meta', [newsAgo(lead.published), lead.source].filter(Boolean).join(' · ')));
    a.appendChild(cap); box.appendChild(a);
    var side = el('div', 'pt-heads'); side.appendChild(el('div', 'pt-hh', 'Headlines'));
    var ul = el('ul');
    rest.forEach(function (x) {
      var li = el('li'), l = el('a'); l.href = x.url; l.target = '_blank'; l.rel = 'noopener';
      l.appendChild(el('span', 'pt-ht', x.headline));
      l.appendChild(el('span', 'pt-hm', [PRO_NAME[x.league] || '', newsAgo(x.published)].filter(Boolean).join(' · ')));
      li.appendChild(l); ul.appendChild(li);
    });
    side.appendChild(ul); box.appendChild(side);
    return box;
  }

  PRO_CSS += '.pt-wrap{margin:0 0 14px}' +
    '.pt-chips{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 8px}' +
    '.pt-chip{font:inherit;font-size:11.5px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#cfd8ea;background:#13264d;border:1px solid rgba(255,255,255,.14);border-radius:999px;padding:5px 11px;cursor:pointer;box-shadow:inset 0 -2px 0 var(--c,transparent)}' +
    '.pt-chip.pt-on{background:#fff;color:#0b1a33;border-color:#fff}' +
    '.pt-row{display:flex;align-items:stretch;gap:6px}' +
    '.pt-track{flex:1;min-width:0;display:flex;gap:8px;overflow-x:auto;scroll-snap-type:x proximity;scrollbar-width:none;padding:1px}' +
    '.pt-track::-webkit-scrollbar{display:none}' +
    '.pt-arr{flex:none;width:34px;font:700 22px/1 system-ui,sans-serif;color:#fff;background:#13264d;border:1px solid rgba(255,255,255,.16);border-radius:6px;cursor:pointer}' +
    '.pt-arr:hover{background:#1c3a72}' +
    '.pt-card{flex:none;scroll-snap-align:start;display:flex;gap:10px;align-items:center;justify-content:space-between;min-width:172px;padding:9px 12px;background:#0f2148;border:1px solid rgba(255,255,255,.1);border-radius:6px;color:#f2f5fb;text-decoration:none}' +
    '.pt-card:hover{border-color:rgba(255,255,255,.35);background:#14295a}' +
    '.pt-card.pt-ours{box-shadow:inset 0 3px 0 #e8b021}' +
    '.pt-card.pt-livec{border-color:rgba(239,68,68,.6)}' +
    '.pt-rows{display:grid;gap:5px;min-width:0}' +
    '.pt-r{display:grid;grid-template-columns:22px 40px 26px;align-items:center;gap:6px;font-size:14.5px}' +
    '.pt-r.pt-lose{color:#8fa1c4}' +
    '.pt-lg{width:22px;height:22px;object-fit:contain}' +
    '.pt-dot{display:block;width:12px;height:12px;border-radius:50%;margin:0 5px;background:#64748b}' +
    '.pt-ab{font-weight:800;letter-spacing:.02em}' +
    '.pt-sc{font-weight:800;text-align:right;font-variant-numeric:tabular-nums}' +
    '.pt-st{display:grid;justify-items:end;gap:3px;font-size:12px;color:#9fb0cf;white-space:nowrap}' +
    '.pt-s1{color:#f2f5fb;font-weight:700}' +
    '.pt-lv{background:#ef4444;color:#fff;font-weight:900;font-size:10px;letter-spacing:.08em;border-radius:3px;padding:2px 5px}' +
    '.pt-lgn{font-size:10px;font-weight:800;letter-spacing:.08em;color:#6f82a8}' +
    '.pt-none{color:#9fb0cf;padding:14px 4px}' +
    '.pt-top{display:grid;grid-template-columns:minmax(0,1.75fr) minmax(0,1fr);gap:14px;margin:0 0 16px}' +
    '.pt-lead{position:relative;display:block;aspect-ratio:16/10;border-radius:8px;overflow:hidden;background:#13264d;color:#fff;text-decoration:none;border:1px solid rgba(255,255,255,.1)}' +
    '.pt-lead img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transition:transform .3s}' +
    '.pt-lead:hover img{transform:scale(1.03)}' +
    '.pt-cap{position:absolute;left:0;right:0;bottom:0;padding:60px 20px 18px;background:linear-gradient(to top,rgba(5,12,28,.96),rgba(5,12,28,.7) 55%,transparent)}' +
    '.pt-tag{display:inline-block;font-size:11px;font-weight:900;letter-spacing:.1em;background:var(--c,#e8b021);color:#fff;border-radius:3px;padding:3px 7px;margin-bottom:8px}' +
    '.pt-hl{font-size:26px;font-weight:800;line-height:1.18;letter-spacing:-.01em}' +
    '.pt-meta{margin-top:6px;font-size:12.5px;color:#b8c4dc}' +
    '.pt-heads{background:#0f2148;border:1px solid rgba(255,255,255,.1);border-radius:8px;overflow:hidden}' +
    '.pt-hh{font-size:15px;font-weight:900;letter-spacing:.12em;text-transform:uppercase;color:#cfd8ea;padding:14px 16px;background:#13295a;border-bottom:1px solid rgba(255,255,255,.08)}' +
    '.pt-heads ul{list-style:none;margin:0;padding:6px 16px 10px}' +
    '.pt-heads li{border-top:1px solid rgba(255,255,255,.07)}.pt-heads li:first-child{border-top:0}' +
    '.pt-heads li a{display:block;padding:10px 0 10px 14px;position:relative;color:#f2f5fb;text-decoration:none}' +
    '.pt-heads li a:before{content:"";position:absolute;left:0;top:17px;width:6px;height:6px;border-radius:50%;background:#3b82f6}' +
    '.pt-heads li a:hover .pt-ht{color:#e8b021}' +
    '.pt-ht{display:block;font-size:14px;font-weight:600;line-height:1.35}' +
    '.pt-hm{display:block;font-size:11.5px;color:#8fa1c4;margin-top:3px}' +
    '.pt-sec .pt-arr{align-self:center;height:64px}' +
    '.pt-sec{margin:0 0 18px}.pt-sh{font-size:15px;font-weight:900;letter-spacing:.12em;text-transform:uppercase;color:#cfd8ea;margin:0 0 9px}' +
    '.pt-sc2{flex:none;scroll-snap-align:start;width:250px;display:block;text-align:left;font:inherit;color:#f2f5fb;text-decoration:none;background:#0f2148;border:1px solid rgba(255,255,255,.1);border-radius:8px;overflow:hidden;cursor:pointer;padding:0 0 10px}' +
    '.pt-sc2:hover{border-color:rgba(255,255,255,.35)}.pt-sc2:hover .pt-ct{color:#e8b021}' +
    '.pt-pic{position:relative;aspect-ratio:16/9;background:#13264d;overflow:hidden}.pt-pic img{width:100%;height:100%;object-fit:cover;display:block}' +
    '.pt-pic .pt-tag{position:absolute;left:8px;top:8px;margin:0;font-size:10px;padding:2px 6px}' +
    '.pt-play{position:absolute;left:50%;top:50%;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;background:rgba(0,0,0,.6);border:2px solid #fff}' +
    '.pt-play:after{content:"";position:absolute;left:17px;top:12px;border-style:solid;border-width:9px 0 9px 15px;border-color:transparent transparent transparent #fff}' +
    '.pt-ct{padding:9px 11px 0;font-size:14px;font-weight:700;line-height:1.3;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}' +
    '.pt-cm{padding:5px 11px 0;font-size:11.5px;color:#8fa1c4}' +
    '.pt-player{margin:0 0 12px;background:#000;border-radius:8px;overflow:hidden;border:1px solid rgba(255,255,255,.14)}.pt-player[hidden]{display:none}' +
    '.pt-pfr{position:relative;aspect-ratio:16/9;max-height:70vh;margin:0 auto}.pt-pfr iframe{position:absolute;inset:0;width:100%;height:100%;border:0}' +
    '.pt-pcap{display:flex;align-items:center;gap:12px;justify-content:space-between;padding:10px 12px;background:#0f2148;font-size:14px}' +
    '.pt-px{flex:none;font:inherit;font-size:12.5px;font-weight:800;color:#fff;background:transparent;border:1px solid rgba(255,255,255,.4);border-radius:999px;padding:6px 12px;cursor:pointer}' +
    '@media (max-width:760px){.pt-sc2{width:220px}.pt-top{grid-template-columns:minmax(0,1fr)}.pt-hl{font-size:20px}.pt-cap{padding:50px 14px 14px}.pt-arr{display:none}.pt-card{min-width:156px;padding:8px 10px}.pt-r{font-size:14px;grid-template-columns:20px 38px 24px}.pt-lg{width:20px;height:20px}}';

  // a sideways strip with arrows (computers) or a swipe (phones)
  function ptStrip(title, cards) {
    var sec = el('div', 'pt-sec'); sec.appendChild(el('div', 'pt-sh', title));
    var row = el('div', 'pt-row'), track = el('div', 'pt-track pt-strack');
    cards.forEach(function (c) { track.appendChild(c); });
    var prev = el('button', 'pt-arr pt-prev', '‹'), next = el('button', 'pt-arr pt-next', '›'); prev.type = next.type = 'button';
    prev.onclick = function () { track.scrollBy({ left: -track.clientWidth * 0.85, behavior: 'smooth' }); };
    next.onclick = function () { track.scrollBy({ left: track.clientWidth * 0.85, behavior: 'smooth' }); };
    row.appendChild(prev); row.appendChild(track); row.appendChild(next); sec.appendChild(row);
    return sec;
  }
  function ptPic(src) {
    var pic = el('div', 'pt-pic');
    if (src) { var im = new Image(); im.src = src; im.alt = ''; im.loading = 'lazy'; im.referrerPolicy = 'no-referrer'; im.onerror = function () { im.remove(); }; pic.appendChild(im); }
    return pic;
  }
  // Top stories: the stories with pictures after the big one and the headlines
  function proStoryStrip() {
    var seen = {}, items = proNews.filter(function (x) { if (!x || !x.headline || !x.url || !x.image || seen[x.url] || !PRO_NAME[x.league]) return false; seen[x.url] = 1; return true; })
      .sort(function (a, b) { return a.published < b.published ? 1 : -1; });
    var used = {}; [].forEach.call(document.querySelectorAll('.pt-top a'), function (a) { used[a.href] = 1; });
    items = items.filter(function (x) { return !used[x.url]; }).slice(0, 16);
    if (!items.length) return null;
    return ptStrip('Top stories', items.map(function (x) {
      var a = el('a', 'pt-sc2'); a.href = x.url; a.target = '_blank'; a.rel = 'noopener';
      var pic = ptPic(x.image); var t = el('span', 'pt-tag', PRO_NAME[x.league]); t.style.setProperty('--c', PRO_COLOR[x.league]); pic.appendChild(t); a.appendChild(pic);
      a.appendChild(el('div', 'pt-ct', x.headline));
      a.appendChild(el('div', 'pt-cm', [x.source, newsAgo(x.published)].filter(Boolean).join(' · ')));
      return a;
    }));
  }
  // Videos: the newest from the leagues, teams and networks; they play right here, above the strip
  function proVideoStrip() {
    var vids = proVids.filter(function (v) { return v && v.u && /[?&]v=([\w-]{11})/.test(v.u); }).slice(0, 20);
    if (!vids.length) return null;
    var player = el('div', 'pt-player'); player.hidden = true;
    function play(v) {
      var id = v.u.match(/[?&]v=([\w-]{11})/)[1]; vidOpen = v;
      player.innerHTML = '';
      var fr = el('div', 'pt-pfr'), f = document.createElement('iframe');
      f.src = 'https://www.youtube-nocookie.com/embed/' + id + '?autoplay=1&rel=0'; f.allow = 'autoplay; fullscreen; picture-in-picture; encrypted-media'; f.allowFullscreen = true; f.title = v.t;
      fr.appendChild(f); player.appendChild(fr);
      var cap = el('div', 'pt-pcap'); cap.appendChild(el('b', null, v.t));
      var x = el('button', 'pt-px', '✕ Close'); x.type = 'button'; x.onclick = function () { vidOpen = null; player.innerHTML = ''; player.hidden = true; };
      cap.appendChild(x); player.appendChild(cap);
      player.hidden = false;
      try { player.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); } catch (e) {}
    }
    var sec = ptStrip('Videos', vids.map(function (v) {
      var b = el('button', 'pt-sc2 pt-vc'); b.type = 'button';
      var pic = ptPic(v.i); pic.appendChild(el('span', 'pt-play')); b.appendChild(pic);
      b.appendChild(el('div', 'pt-ct', v.t));
      b.appendChild(el('div', 'pt-cm', [v.ch, newsAgo(v.p)].filter(Boolean).join(' · ')));
      b.onclick = function () { play(v); };
      return b;
    }));
    sec.insertBefore(player, sec.children[1]);
    if (vidOpen) setTimeout(function () { play(vidOpen); }, 0);
    return sec;
  }
  function draw(box, d, o) {
    if (o.mode === 'pro' && vidOpen && box.querySelector('.pt-player iframe')) return;   // a video is playing: the refresh waits
    box.innerHTML = '';
    if (o.mode === 'pro') {
      box.appendChild(proTicker(d, o.target)); var tp = proTop(); if (tp) box.appendChild(tp);
      var ss = proStoryStrip(); if (ss) box.appendChild(ss);
      var vs = proVideoStrip(); if (vs) box.appendChild(vs);
    }
    var g = el('div', 'ppg' + (o.compact ? ' compact' : ''));
    var h = el('div', 'pg-gh'), l = el('div');
    var krow = el('div', 'pg-krow'); krow.appendChild(el('div', 'pg-gk', o.kicker || 'Your local sports guide')); l.appendChild(krow);
    l.appendChild(el('div', 'pg-gt', o.title || 'Windsor-Essex sports, all in one place'));
    l.appendChild(el('div', 'pg-gs', o.sub || 'Every local game, score and community event, checked around the clock.'));
    h.appendChild(l);
    var rt = el('div', 'pg-gr');
    var sp = o.sponsor === false ? null : (o.sponsor || SPONSOR);
    if (sp) {    // "Presented by" the guide's sponsor
      var by = el('div', 'pg-by'); by.appendChild(el('span', null, 'Presented by'));
      var chip = el('span', 'pg-spchip'), im = new Image(); im.src = sp.logo; im.alt = sp.name; im.onerror = function () { chip.remove(); };
      chip.appendChild(im); by.appendChild(chip); by.appendChild(el('b', null, sp.name));
      rt.appendChild(by);
    }
    var f = ago(d.updated);
    if (f) {   // computers: under the sponsor; phones: beside "Your local sports guide" (short: "6 min ago")
      var fr = el('span', 'pg-fresh pg-fd'); fr.appendChild(el('i')); fr.appendChild(document.createTextNode(f)); rt.appendChild(fr);
      var fm = el('span', 'pg-fresh pg-fm'); fm.appendChild(el('i')); fm.appendChild(document.createTextNode(f.replace(/^Updated /, ''))); krow.appendChild(fm);
    }
    h.appendChild(rt);
    g.appendChild(h);
    var cols = el('div', 'pg-cols');
    if (o.mode === 'pro') {
      cols.classList.add('pg-two');
      cols.appendChild(proTodayCol(d, o.target));
      cols.appendChild(proComingCol(d, o.target));
    } else {
      cols.appendChild(gamesCol(d, o.target, o.compact));
      cols.appendChild(finalsCol(d, o.target, o.compact));
      cols.appendChild(calCol(d, o.target, o.compact));
    }
    g.appendChild(cols);
    // our pro teams appear only in the Pro Sports Guide (the Pro Hub), so the local guide has no Pro Hub line
    if (o.pro === true && o.mode !== 'pro') g.appendChild(proLine(d.pro || [], o.target));
    // one line under the guide: fans send their events and story ideas
    if (o.tips !== false) {
      var tip = el('a', 'pg-tip'); tip.href = 'mailto:' + TIPS + '?subject=' + encodeURIComponent('Event / story idea for Powerplay Windsor');
      tip.target = '_blank'; tip.rel = 'noopener';   // _top is blocked for email links inside the Wix box
      tip.appendChild(el('span', 'pg-tipq', 'Got an event or story idea?'));
      tip.appendChild(el('b', 'pg-tipd', 'Email ' + TIPS + ' \u203a'));
      tip.appendChild(el('b', 'pg-tipm', 'Email us \u203a'));     // phones: short, with the address on its own line
      tip.appendChild(el('span', 'pg-tipa', TIPS));
      g.appendChild(tip);
    }
    box.appendChild(g);
  }

  function render(box, opts) {
    if (!box) return;
    var o = opts || {}; o.target = o.target || '_top';
    if (!document.getElementById('ppg-css')) { var s = document.createElement('style'); s.id = 'ppg-css'; s.textContent = CSS + PRO_CSS; document.head.appendChild(s); }
    var last = null;
    function go() { (o.mode === 'pro' ? proLoad() : load()).then(function (d) { last = d; redraw = function () { draw(box, d, o); if (o.onDraw) o.onDraw(); }; redraw(); }); }
    var lastRun = 0;
    function tick() { if (Date.now() - lastRun >= (box_live || pro_live ? 60000 : 5 * 60000)) { lastRun = Date.now(); go(); } }
    tick();
    setInterval(tick, 15000);
    setInterval(function () { if (last) { [].forEach.call(box.querySelectorAll('.pg-fresh'), function (fr) { var t = ago(last.updated); fr.lastChild.textContent = fr.classList.contains('pg-fm') ? t.replace(/^Updated /, '') : t; }); } }, 60000);
  }

  window.PPGuide = { render: render };
})();
