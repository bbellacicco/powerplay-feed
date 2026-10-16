/* Powerplay Windsor: left / right arrows on every sideways strip, for computers with a mouse.
   (Phones and tablets swipe, so they don't get arrows.) An arrow hides when there's nothing more that way. */
(function () {
  if (!window.matchMedia || !matchMedia('(hover: hover) and (pointer: fine)').matches) return;
  var SEL = '.sstrip, .strip, .grid, .row, .scroller';
  var css = document.createElement('style');
  css.textContent =
    '.ppa-wrap{position:relative}' +
    '.ppa{position:absolute;z-index:6;top:50%;width:40px;height:40px;margin-top:-26px;border-radius:50%;border:1px solid rgba(255,255,255,.35);' +
    'background:rgba(11,26,51,.88);color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;' +
    'box-shadow:0 6px 18px rgba(0,0,0,.45);transition:opacity .2s,background .2s}' +
    '.ppa:hover{background:#e8b021;color:#0b1a33;border-color:#e8b021}' +
    '.ppa svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}' +
    '.ppa.l{left:6px}.ppa.r{right:6px}.ppa.off{opacity:0;pointer-events:none}' +
    '.rarrow{display:none!important}';
  document.head.appendChild(css);

  function arrow(dir) {
    var b = document.createElement('button'); b.type = 'button'; b.className = 'ppa ' + dir;
    b.setAttribute('aria-label', dir === 'l' ? 'Scroll left' : 'Scroll right');
    b.innerHTML = '<svg viewBox="0 0 24 24"><path d="' + (dir === 'l' ? 'M15 5l-7 7 7 7' : 'M9 5l7 7-7 7') + '"/></svg>';
    return b;
  }
  function setup(el) {
    if (el.__ppa) return;
    var ov = getComputedStyle(el).overflowX;
    if (ov !== 'auto' && ov !== 'scroll') return;
    el.__ppa = true;
    var wrap = el.parentNode;
    if (!wrap.classList.contains('ppa-wrap') && !wrap.classList.contains('rowwrap')) {
      wrap = document.createElement('div'); wrap.className = 'ppa-wrap';
      el.parentNode.insertBefore(wrap, el); wrap.appendChild(el);
    } else wrap.classList.add('ppa-wrap');
    var l = arrow('l'), r = arrow('r');
    wrap.appendChild(l); wrap.appendChild(r);
    function update() {
      var max = el.scrollWidth - el.clientWidth;
      l.classList.toggle('off', el.scrollLeft <= 4);
      r.classList.toggle('off', max <= 4 || el.scrollLeft >= max - 4);
      // keep the arrows centred on the strip itself, not on any caption under it
      var top = el.offsetTop + Math.min(el.clientHeight, 260) / 2;
      l.style.top = r.style.top = top + 'px';
    }
    l.onclick = function () { el.scrollBy({ left: -el.clientWidth * 0.8, behavior: 'smooth' }); };
    r.onclick = function () { el.scrollBy({ left: el.clientWidth * 0.8, behavior: 'smooth' }); };
    el.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    if (window.ResizeObserver) new ResizeObserver(update).observe(el);
    el.__ppaUpdate = update;
    update();
  }
  var tmr;
  function scan() {
    clearTimeout(tmr);
    tmr = setTimeout(function () {
      [].forEach.call(document.querySelectorAll(SEL), function (el) { setup(el); if (el.__ppaUpdate) el.__ppaUpdate(); });
    }, 150);
  }
  function start() {
    scan();
    new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
