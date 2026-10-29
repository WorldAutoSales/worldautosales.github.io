/* Mix by Country -- filter layout experiments.
   The filter groups (Period, Market Rank, Powertrain, Car class, Continent, Country) and their handlers are untouched; this only decides WHERE they live:
     classic     the two side panels, as before
     collapse    the side panels with collapsible groups (each shows a one-line summary) and retractable side rails
     bar         a sticky top bar of filter chips; a chip opens its group in a popover; both side panels are gone
     drawer      a "Filters" button opens a slide-in panel; the active filters are shown as removable tags; both side panels are gone
   The choice and the collapsed states are remembered in localStorage. Loaded after the page's own script (it reads its filter state). */
(function(){
  'use strict';
  if(typeof selectedMonths === 'undefined' || typeof recompute !== 'function') return;

  const store = {
    get(k, d){ try{ const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); }catch(e){ return d; } },
    set(k, v){ try{ localStorage.setItem(k, JSON.stringify(v)); }catch(e){} }
  };
  const MODES = [['classic', 'Classic'], ['collapse', 'Collapsible'], ['bar', 'Top bar'], ['drawer', 'Drawer']];
  const wrap = document.querySelector('.content-with-filters');
  const left = wrap.querySelector('.filters-panel-left');
  const right = [...wrap.children].find(el => el.classList.contains('filters-panel') && el !== left);
  const page = wrap.querySelector('.page');
  const header = page.querySelector('.page-header');
  const actions = right.querySelector('.filter-actions');
  const groupOf = id => document.getElementById(id).closest('.filter-group');

  // one-line summary of a multi-select: "All", the few that are on, "All but X", or "n of N"
  const FUEL_SHORT = { bev:'BEV', phev:'PHEV', hev:'HEV', petrol:'Petrol', diesel:'Diesel', others:'Others' };
  function listSum(keys, sel, label){
    const on = keys.filter(k => sel.has(k)), off = keys.filter(k => !sel.has(k));
    if(!off.length) return 'All';
    if(!on.length) return 'None';
    if(on.length <= 3) return on.map(label).join(', ');
    return off.length <= 2 ? 'All but ' + off.map(label).join(', ') : `${on.length} of ${keys.length}`;
  }
  const GROUPS = [
    { key:'period', title:'Period', side:'left', el: groupOf('filter-months'),
      sum: () => { const k = [...selectedMonths][0]; return MONTHLY_DATA[k] ? MONTHLY_DATA[k].label : k; },
      active: () => [...selectedMonths][0] !== DEFAULT_MONTH, reset: () => { const r = document.querySelector(`#filter-months input[data-month="${DEFAULT_MONTH}"]`); if(r){ r.checked = true; r.dispatchEvent(new Event('change', { bubbles:true })); } } },
    { key:'rank', title:'Market rank', side:'left', el: groupOf('filter-rank-tiers'),
      sum: () => { const s = listSum(RANK_TIER_KEYS, selectedRankTiers, k => RANK_TIER_LABELS[k]); return s === 'All' ? 'All tiers' : s; },
      active: () => selectedRankTiers.size !== RANK_TIER_KEYS.length },
    { key:'fuels', title:'Powertrain', side:'left', el: groupOf('filter-fuels'),
      sum: () => listSum(FUEL_KEYS, selectedFuels, k => FUEL_SHORT[k] || FUEL_LABELS[k]),
      active: () => selectedFuels.size !== FUEL_KEYS.length },
    { key:'classes', title:'Car class', side:'left', el: groupOf('filter-classes'),
      sum: () => !classFilterActive() ? 'All' : `${selectedClasses.size} of ${CLASS_KEYS.length}`,
      active: () => classFilterActive() },
    { key:'continents', title:'Continent', side:'right', el: groupOf('filter-continents'),
      sum: () => listSum(ALL_CONTINENTS, selectedContinents, contShort),
      active: () => selectedContinents.size !== ALL_CONTINENTS.length },
    { key:'countries', title:'Country', side:'right', wide:true, el: groupOf('filter-countries-group'),
      sum: () => selectedCountries.size === FILTER_COUNTRIES.length ? `All ${FILTER_COUNTRIES.length}` : selectedCountries.size === 1 ? [...selectedCountries][0] : `${selectedCountries.size} of ${FILTER_COUNTRIES.length}`,
      active: () => selectedCountries.size !== FILTER_COUNTRIES.length }
  ];
  const panelsOf = side => GROUPS.filter(g => g.side === side);
  let collapsed = store.get('mixFilterCollapsed', { rank:true, classes:true, continents:true, countries:true });
  let railsClosed = store.get('mixFilterRails', { left:false, right:false });
  let mode = store.get('mixFilterLayout', 'collapse');
  if(!MODES.some(m => m[0] === mode)) mode = 'collapse';
  let bar = null, drawer = null, backdrop = null, openPop = null;

  // ---------- group headers: a chevron to collapse + a one-line summary ----------
  GROUPS.forEach(g => {
    const label = g.el.querySelector('.filter-label');
    const tog = label.querySelector('.filter-toggle');
    let titleEl = tog;
    if(!titleEl){
      const tn = [...label.childNodes].find(n => n.nodeType === 3 && n.textContent.trim());
      titleEl = document.createElement('span'); titleEl.className = 'fl-title'; titleEl.textContent = tn.textContent.trim(); tn.remove();
    }
    const lft = document.createElement('div'); lft.className = 'fl-left';
    const chev = document.createElement('button'); chev.type = 'button'; chev.className = 'fl-chev'; chev.textContent = '▾'; chev.setAttribute('aria-label', 'Collapse or expand ' + g.title);
    const sum = document.createElement('span'); sum.className = 'fl-sum';
    lft.append(chev, titleEl, sum); label.prepend(lft);
    g.sumEl = sum;
    lft.addEventListener('click', e => { if(e.target.closest('.filter-toggle')) return; toggleGroup(g); });
  });
  function toggleGroup(g){
    const on = !g.el.classList.contains('fl-collapsed');
    g.el.classList.toggle('fl-collapsed', on);
    collapsed[g.key] = on; store.set('mixFilterCollapsed', collapsed);
  }
  function applyCollapsed(useSaved){
    GROUPS.forEach(g => g.el.classList.toggle('fl-collapsed', useSaved && !!collapsed[g.key]));
  }

  // ---------- retractable side rails ----------
  [['left', left], ['right', right]].forEach(([side, panel]) => {
    const head = document.createElement('div'); head.className = 'fl-panel-head';
    head.innerHTML = '<button type="button" class="fl-panel-toggle" title="Hide or show these filters"><span class="fl-pt-ico">⇤</span><span class="fl-pt-txt">Filters</span><span class="fl-badge"></span></button>';
    panel.prepend(head);
    head.firstChild.addEventListener('click', () => { railsClosed[side] = !railsClosed[side]; store.set('mixFilterRails', railsClosed); applyRails(); });
    panel._head = head;
  });
  function applyRails(){
    [['left', left], ['right', right]].forEach(([side, panel]) => {
      const closed = mode === 'collapse' && railsClosed[side];
      panel.classList.toggle('fl-panel-collapsed', closed);
      panel._head.querySelector('.fl-pt-ico').textContent = closed ? (side === 'left' ? '⇥' : '⇤') : (side === 'left' ? '⇤' : '⇥');
    });
  }

  // ---------- summaries, chips, badges ----------
  function refresh(){
    let total = 0;
    GROUPS.forEach(g => {
      const on = g.active(); if(on) total++;
      g.sumEl.textContent = g.sum(); g.sumEl.classList.toggle('is-active', on);
      if(g.chipEl){ g.chipEl.querySelector('.fl-chip-v').textContent = g.sum(); g.chipEl.classList.toggle('is-active', on); }
    });
    ['left', 'right'].forEach(side => { const n = panelsOf(side).filter(g => g.active()).length; const b = (side === 'left' ? left : right)._head.querySelector('.fl-badge'); b.textContent = n || ''; b.dataset.n = n; });
    const ob = document.querySelector('.fl-open .fl-badge'); if(ob){ ob.textContent = total || ''; ob.dataset.n = total; }
    const act = document.querySelector('.fl-active'); if(act) renderTags(act);
  }
  function renderTags(box){
    box.innerHTML = '';
    GROUPS.forEach(g => {
      const on = g.active();
      if(!on && g.key !== 'period') return;
      const tag = document.createElement('span'); tag.className = 'fl-tag' + (on ? '' : ' plain');
      tag.innerHTML = `<small>${g.title}</small>${g.sum().replace(/</g, '&lt;')}`;
      if(on){
        const x = document.createElement('button'); x.type = 'button'; x.title = 'Reset ' + g.title; x.textContent = '✕';
        x.addEventListener('click', () => resetGroup(g)); tag.append(x);
      }
      box.append(tag);
    });
  }
  function resetGroup(g){
    if(g.reset){ g.reset(); return; }
    const btn = g.el.querySelector('.filter-bulk-btn[data-action="check"]');
    if(btn) btn.click();
  }

  // ---------- layouts ----------
  function teardown(){
    closePop();
    panelsOf('left').forEach(g => left.append(g.el));
    panelsOf('right').forEach(g => right.append(g.el)); right.append(actions);
    GROUPS.forEach(g => { g.chipEl = null; });
    [bar, drawer, backdrop].forEach(el => el && el.remove()); bar = drawer = backdrop = null;
  }
  function buildBar(){
    bar = document.createElement('div'); bar.className = 'fl-bar';
    const chips = document.createElement('div'); chips.className = 'fl-chips';
    GROUPS.forEach((g, i) => {
      const w = document.createElement('div'); w.className = 'fl-chipwrap' + (g.wide ? ' fl-pop-wide' : '') + (i >= GROUPS.length - 2 ? ' fl-pop-right' : '');
      const b = document.createElement('button'); b.type = 'button'; b.className = 'fl-chip'; b.setAttribute('aria-expanded', 'false');
      b.innerHTML = `<span class="fl-chip-k">${g.title}</span><span class="fl-chip-v"></span><span class="fl-caret">▾</span>`;
      const pop = document.createElement('div'); pop.className = 'fl-pop'; pop.hidden = true; pop.append(g.el);
      w.append(b, pop); chips.append(w); g.chipEl = b;
      b.addEventListener('click', e => { e.stopPropagation(); togglePop(w); });
    });
    const act = document.createElement('div'); act.className = 'fl-bar-actions'; act.append(actions);
    bar.append(chips, act); page.prepend(bar);
  }
  function togglePop(w){
    const isOpen = openPop === w; closePop();
    if(isOpen) return;
    w.querySelector('.fl-pop').hidden = false; w.querySelector('.fl-chip').setAttribute('aria-expanded', 'true'); openPop = w;
  }
  function closePop(){
    if(!openPop) return;
    openPop.querySelector('.fl-pop').hidden = true; openPop.querySelector('.fl-chip').setAttribute('aria-expanded', 'false'); openPop = null;
  }
  document.addEventListener('click', e => { if(openPop && !e.target.closest('.fl-chipwrap')) closePop(); });
  document.addEventListener('keydown', e => { if(e.key === 'Escape'){ closePop(); setDrawer(false); } });

  function buildDrawer(){
    bar = document.createElement('div'); bar.className = 'fl-bar';
    const open = document.createElement('button'); open.type = 'button'; open.className = 'fl-open';
    open.innerHTML = '☰ Filters <span class="fl-badge"></span>'; open.addEventListener('click', () => setDrawer(true));
    const act = document.createElement('div'); act.className = 'fl-active';
    bar.append(open, act); page.prepend(bar);
    backdrop = document.createElement('div'); backdrop.className = 'fl-backdrop'; backdrop.addEventListener('click', () => setDrawer(false));
    drawer = document.createElement('aside'); drawer.className = 'fl-drawer'; drawer.setAttribute('aria-label', 'Filters');
    const dh = document.createElement('div'); dh.className = 'fl-drawer-head'; dh.innerHTML = '<span>Filters</span><button type="button" aria-label="Close filters">✕</button>';
    dh.querySelector('button').addEventListener('click', () => setDrawer(false));
    const body = document.createElement('div'); body.className = 'fl-drawer-body';
    GROUPS.forEach(g => body.append(g.el)); body.append(actions);
    drawer.append(dh, body); document.body.append(backdrop, drawer);
  }
  function setDrawer(on){ if(drawer){ drawer.classList.toggle('open', on); backdrop.classList.toggle('open', on); } }

  function applyMode(m){
    mode = m; store.set('mixFilterLayout', m);
    teardown();
    document.body.dataset.flMode = m;
    applyCollapsed(m === 'collapse' || m === 'drawer');
    if(m === 'bar') buildBar();
    if(m === 'drawer') buildDrawer();
    applyRails();
    document.querySelectorAll('.fl-switch button').forEach(b => b.classList.toggle('active', b.dataset.mode === m));
    refresh();
    window.dispatchEvent(new Event('resize'));        // charts that size themselves to their card re-measure
  }

  // ---------- switcher ----------
  const sw = document.createElement('div'); sw.className = 'fl-switch'; sw.setAttribute('role', 'group'); sw.setAttribute('aria-label', 'Filter layout');
  sw.innerHTML = '<span>Filters</span>' + MODES.map(([k, l]) => `<button type="button" data-mode="${k}">${l}</button>`).join('');
  sw.addEventListener('click', e => { const b = e.target.closest('button[data-mode]'); if(b && b.dataset.mode !== mode) applyMode(b.dataset.mode); });
  header.prepend(sw);

  // the page's own recompute() keeps the summaries and tags in step with every filter change
  window.refreshFilterLayout = refresh;
  applyMode(mode);
})();
