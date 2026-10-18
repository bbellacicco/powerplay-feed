/* Powerplay Windsor: share buttons and "follow us" links, used by home.html, sports.html and network.html.
   PPShare.button({ title, url, text })  -> a small "Share" button; tapping it opens a menu right under it:
                                             Facebook · X · Text message · Email · Copy link (or the phone's own share sheet)
   PPShare.follow()                      -> a row of follow links: YouTube (subscribe) · Instagram · Facebook · X
   PPShare.link(tab)                     -> the public address of a hub section: pro -> the Pro Hub (/local-sports),
                                            anything else -> the Local Hub (/scores-standings?tab=...) */
(function () {
  var SITE = 'https://www.powerplaywindsor.com/';
  var SOCIAL = [
    ['YouTube', 'https://www.youtube.com/@PowerplayWindsor?sub_confirmation=1', 'Subscribe', '#ff3d3d',
      'M23 7.2a3 3 0 0 0-2.1-2.1C19 4.6 12 4.6 12 4.6s-7 0-8.9.5A3 3 0 0 0 1 7.2 31 31 0 0 0 .6 12a31 31 0 0 0 .4 4.8 3 3 0 0 0 2.1 2.1c1.9.5 8.9.5 8.9.5s7 0 8.9-.5a3 3 0 0 0 2.1-2.1 31 31 0 0 0 .4-4.8 31 31 0 0 0-.4-4.8zM9.7 15.1V8.9l5.8 3.1-5.8 3.1z'],
    ['Instagram', 'https://www.instagram.com/powerplaysportswindsor/', 'Follow', '#e1306c',
      'M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm0 8.2a3.2 3.2 0 1 1 0-6.4 3.2 3.2 0 0 1 0 6.4zM17.3 5.5a1.2 1.2 0 1 0 0 2.4 1.2 1.2 0 0 0 0-2.4zM12 2.2c2.7 0 3 0 4 .1 2.7.1 4 1.4 4.1 4.1.1 1 .1 1.3.1 4s0 3-.1 4c-.1 2.7-1.4 4-4.1 4.1-1 .1-1.3.1-4 .1s-3 0-4-.1c-2.7-.1-4-1.4-4.1-4.1-.1-1-.1-1.3-.1-4s0-3 .1-4C4 3.7 5.3 2.4 8 2.3c1-.1 1.3-.1 4-.1z'],
    ['Facebook', 'https://www.facebook.com/powerplaysportsvideo', 'Follow', '#3b82f6',
      'M14 8.5V6.6c0-.9.6-1.1 1-1.1h2.5V1.7L14 1.7c-3.8 0-4.6 2.8-4.6 4.6v2.2H7v3.9h2.4V22.3H14V12.4h3.1l.4-3.9H14z'],
    ['X', 'https://x.com/ppsportsvideo', 'Follow', '#e7e9ea',
      'M17.8 2.5h3.3l-7.2 8.2 8.5 11.2h-6.6l-5.2-6.8-6 6.8H1.3l7.7-8.8L.9 2.5h6.8l4.7 6.2 5.4-6.2zm-1.2 17.4h1.8L6.6 4.4H4.6l12 15.5z']
  ];
  var ICON_SHARE = 'M18 16a3 3 0 0 0-2.4 1.2L8.9 13.7a3 3 0 0 0 0-1.4l6.7-3.5A3 3 0 1 0 15 7l-6.7 3.5a3 3 0 1 0 0 3l6.7 3.5A3 3 0 1 0 18 16z';

  var css = document.createElement('style');
  css.textContent =
    '.pps-btn{display:inline-flex;align-items:center;gap:6px;border:1px solid rgba(255,255,255,.22);background:rgba(255,255,255,.06);color:#f2f5fb;' +
    'border-radius:999px;padding:5px 11px 5px 9px;font:700 12px/1 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;cursor:pointer;white-space:nowrap}' +
    '.pps-btn:hover{border-color:#e8b021;color:#e8b021}.pps-btn svg{width:13px;height:13px;fill:currentColor}' +
    '.pps-menu{position:absolute;z-index:50;min-width:210px;background:#10244a;border:1px solid #1e3a6e;border-radius:10px;box-shadow:0 14px 36px rgba(0,0,0,.5);padding:6px;' +
    'font:600 14px/1.2 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}' +
    '.pps-menu a,.pps-menu button{display:flex;align-items:center;gap:10px;width:100%;padding:10px 12px;border:0;border-radius:7px;background:none;color:#f2f5fb;' +
    'text-decoration:none;font:inherit;cursor:pointer;text-align:left}.pps-menu a:hover,.pps-menu button:hover{background:#1a3566}' +
    '.pps-menu .t{color:#9fb0cf;font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;padding:6px 12px 4px}' +
    '.pps-menu .ok{color:#3ccf7a}' +
    '.pps-follow{display:flex;flex-wrap:wrap;align-items:center;gap:8px}' +
    '.pps-follow .lbl{color:#9fb0cf;font:700 12px system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;margin-right:2px}' +
    '.pps-follow a{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:6px 12px 6px 9px;text-decoration:none;color:#f2f5fb;' +
    'background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.14);font:700 12px/1 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}' +
    '.pps-follow a:hover{border-color:var(--c)}.pps-follow a svg{width:14px;height:14px;fill:var(--c)}' +
    '.pps-follow a.yt{background:#ff3d3d;border-color:#ff3d3d}.pps-follow a.yt svg{fill:#fff}';
  document.head.appendChild(css);

  function svg(d) { return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + d + '"/></svg>'; }
  var open = null;
  function close() { if (open) { open.remove(); open = null; } }
  document.addEventListener('click', function (e) { if (open && !open.contains(e.target) && !e.target.closest('.pps-btn')) close(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });

  function copy(text) {
    var ta = document.createElement('textarea'); ta.value = text; ta.setAttribute('readonly', '');
    ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0'; document.body.appendChild(ta); ta.select();
    var ok = false; try { ok = document.execCommand('copy'); } catch (e) {}
    ta.remove();
    if (!ok && navigator.clipboard) { navigator.clipboard.writeText(text).catch(function () {}); ok = true; }
    return ok;
  }

  function menu(btn, o) {
    close();
    var url = o.url, text = o.text || o.title, m = document.createElement('div'); m.className = 'pps-menu';
    var e = encodeURIComponent, items = [
      ['Facebook', 'https://www.facebook.com/sharer/sharer.php?u=' + e(url)],
      ['X', 'https://x.com/intent/post?text=' + e(text) + '&url=' + e(url)],
      ['Text message', 'sms:?&body=' + e(text + ' ' + url)],
      ['Email', 'mailto:?subject=' + e(o.title) + '&body=' + e(text + '\n\n' + url)]
    ];
    m.innerHTML = '<div class="t">Share ' + o.title.replace(/</g, '&lt;') + '</div>';
    items.forEach(function (it) {
      var a = document.createElement('a'); a.href = it[1]; a.textContent = it[0];
      a.target = /^(sms|mailto):/.test(it[1]) ? '_top' : '_blank'; a.rel = 'noopener';
      a.onclick = function () { setTimeout(close, 50); };
      m.appendChild(a);
    });
    var c = document.createElement('button'); c.type = 'button'; c.textContent = 'Copy link';
    c.onclick = function () { if (copy(url)) { c.textContent = 'Link copied ✓'; c.className = 'ok'; setTimeout(close, 1200); } else { prompt('Copy this link:', url); } };
    m.appendChild(c);
    document.body.appendChild(m);
    var r = btn.getBoundingClientRect(), left = r.right + window.scrollX - m.offsetWidth;
    m.style.left = Math.max(8, Math.min(left, document.documentElement.clientWidth - m.offsetWidth - 8)) + 'px';
    m.style.top = (r.bottom + window.scrollY + 6) + 'px';
    open = m;
  }

  window.PPShare = {
    link: function (tab) {
      if (tab === 'pro') return SITE + 'local-sports?tab=scores';
      if (/^pro-/.test(tab)) return SITE + 'local-sports?tab=' + tab.slice(4);
      var map = { local: 'scores' }; tab = map[tab] || tab || 'scores';
      return SITE + 'scores-standings?tab=' + tab;
    },
    button: function (o) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'pps-btn';
      b.setAttribute('aria-label', 'Share ' + o.title);
      b.innerHTML = svg(ICON_SHARE) + '<span>Share</span>';
      b.onclick = function (ev) {
        ev.stopPropagation();
        var data = typeof o === 'function' ? o() : o;
        // the phone's own share sheet when the page is allowed to use it; otherwise our menu
        if (navigator.share && /iPhone|iPad|Android/i.test(navigator.userAgent)) {
          navigator.share({ title: data.title, text: data.text || data.title, url: data.url }).catch(function (err) {
            if (!err || err.name !== 'AbortError') menu(b, data);
          });
        } else menu(b, data);
      };
      return b;
    },
    follow: function (label) {
      var d = document.createElement('div'); d.className = 'pps-follow';
      if (label !== false) { var l = document.createElement('span'); l.className = 'lbl'; l.textContent = label || 'Follow Powerplay'; d.appendChild(l); }
      SOCIAL.forEach(function (s) {
        var a = document.createElement('a'); a.href = s[1]; a.target = '_blank'; a.rel = 'noopener';
        a.style.setProperty('--c', s[3]); if (s[0] === 'YouTube') a.className = 'yt';
        a.innerHTML = svg(s[4]) + '<span>' + (s[0] === 'YouTube' ? 'Subscribe on YouTube' : s[0]) + '</span>';
        a.setAttribute('aria-label', s[2] + ' on ' + s[0]);
        d.appendChild(a);
      });
      return d;
    }
  };
})();
