// "Electrification Mix — Recent" stacked bar chart: BEV/PHEV/HEV as a % (or, in "# of Units" mode,
// the raw count) of each period's total registrations. Petrol/Diesel are also available but start
// hidden (dimmed in the legend) -- click either chip (or "# of Units"/"%" mode toggle) to reveal
// them stacked on top. Periods are the last 5 full annual years (fewer if a country's history is
// shorter), then the current year's YTD bar, then each real month of the current year so far (just
// the YTD bar, on its own, if no monthly breakdown exists for that country). Shared by country.html
// (always, for the URL country),
// individual-country.html (only while a country is focused), and powertrain-mix-by-country.html
// (only while a country is focused).
// Requires COUNTRY_YEARLY, optionally COUNTRY_MONTHLY, FUEL_COLORS, FUEL_LABELS, and d3 already
// loaded, plus a card in the host page shaped like:
//   <div class="card chart-card" id="elec-bars-card">
//     <h2 id="elec-bars-title"></h2>
//     <p class="note" id="elec-bars-note"></p>
//     <div class="chart-legend" id="elec-bars-legend"></div>
//     <svg class="chart" id="elec-bars-svg" viewBox="0 0 900 320" preserveAspectRatio="none"></svg>
//     <div class="tooltip" id="elec-bars-tooltip"></div>
//   </div>
// The %/# of Units mode toggle is injected into the DOM on first render (wrapping the existing
// h2 in a .chart-header-row) -- no host-page markup change needed.

const ELEC_BARS_KEYS = ['bev', 'phev', 'hev']; // shown by default
const ELEC_BARS_EXTRA_KEYS = ['petrol', 'diesel']; // start hidden/dimmed in the legend -- click to reveal
const ELEC_BARS_ALL_KEYS = [...ELEC_BARS_KEYS, ...ELEC_BARS_EXTRA_KEYS];
const ELEC_BARS_MONTH_ABBR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const ELEC_BARS_NOTE = "Battery Electric, Plug-in Hybrid, and Hybrid as a share of each period's total registrations -- not stacked to 100% (Others isn't shown). Petrol and Diesel start dimmed in the legend; click either one (or a bar segment) to add it to the stack. The last 5 full years (fewer if history is shorter), then the current year's YTD total, then each month of the current year so far (just the YTD bar if no monthly breakdown exists). Click a legend swatch or any segment to toggle that powertrain on/off.";
// how many full annual years (immediately preceding the current one) to show, history permitting
const ELEC_BARS_YEAR_COUNT = 5;
// width ratios, relative to a single narrow bar (width 1) -- years widest, the current year's
// YTD bar in between, individual months narrowest
const ELEC_BARS_YEAR_WIDTH_RATIO = 2.2;
const ELEC_BARS_YTD_WIDTH_RATIO = 1.6;
const ELEC_BARS_MONTH_WIDTH_RATIO = 0.7;
// Y axis is fixed 0-100% in "%" mode (not auto-scaled to the country's own data) so charts are
// comparable across countries and never jump around when switching focus -- 100% comfortably
// covers the highest real value seen in this dataset (Norway, ~99.2% in March 2026).
const ELEC_BARS_Y_MAX = 100;

// module-level state -- only one instance of this chart is ever shown per page at a time
// (country.html has exactly one; the other two pages show/hide their single instance based on
// focus). Scoped to this chart only, independent of any page-wide fuel filter used elsewhere.
let elecBarsCountry = null;
let elecBarsHidden = new Set(ELEC_BARS_EXTRA_KEYS); // keys currently excluded from the stack
let elecBarsMode = 'pct'; // 'pct' | 'raw'

function buildElectrificationBarsSeries(country){
  const yearly = (typeof COUNTRY_YEARLY !== 'undefined' && COUNTRY_YEARLY[country]) || [];
  const annualPeriods = yearly
    .filter(r => r.period_type === 'ANNUAL')
    .sort((a, b) => a.year - b.year)
    .slice(-ELEC_BARS_YEAR_COUNT)
    .map(r => ({ label: String(r.year), bev: r.bev, phev: r.phev, hev: r.hev, petrol: r.petrol, diesel: r.diesel, total: r.total, isPartial: false, isYear: true }));

  const ytdRow = yearly.find(r => r.period_type === 'YTD');
  const ytdPeriod = ytdRow
    ? { label: `${ytdRow.year} YTD`, bev: ytdRow.bev, phev: ytdRow.phev, hev: ytdRow.hev, petrol: ytdRow.petrol, diesel: ytdRow.diesel, total: ytdRow.total, isPartial: true, isYear: false, isYTD: true }
    : null;

  let monthPeriods = [];
  if(ytdRow && typeof COUNTRY_MONTHLY !== 'undefined' && COUNTRY_MONTHLY[country]){
    const yr = String(ytdRow.year);
    monthPeriods = COUNTRY_MONTHLY[country]
      .filter(r => r.ym.startsWith(yr))
      .sort((a, b) => a.ym.localeCompare(b.ym))
      .map(r => {
        const mm = parseInt(r.ym.slice(5, 7), 10);
        return { label: `${ELEC_BARS_MONTH_ABBR[mm - 1]} '${yr.slice(2)}`, bev: r.bev, phev: r.phev, hev: r.hev, petrol: r.petrol, diesel: r.diesel, total: r.total, isPartial: false, isYear: false };
      });
  }

  // countries with no monthly breakdown fall back to the YTD bar alone as their only
  // representation of the current year; otherwise the YTD bar leads the monthly bars
  if(monthPeriods.length === 0) return ytdPeriod ? [...annualPeriods, ytdPeriod] : annualPeriods;
  return ytdPeriod ? [...annualPeriods, ytdPeriod, ...monthPeriods] : [...annualPeriods, ...monthPeriods];
}

// variable-width x positions: year bars wider than month/YTD bars, scaled to fill innerW
function elecBarsLayout(periods, innerW){
  const gapFrac = 0.4; // gap between bars, as a fraction of one narrow (month) bar's width
  const slots = periods.map(d => d.isYear ? ELEC_BARS_YEAR_WIDTH_RATIO : d.isYTD ? ELEC_BARS_YTD_WIDTH_RATIO : ELEC_BARS_MONTH_WIDTH_RATIO);
  const totalSlots = slots.reduce((a, b) => a + b, 0) + gapFrac * Math.max(0, periods.length - 1);
  const unit = innerW / totalSlots;
  let cursor = 0;
  return periods.map((d, i) => {
    const w = slots[i] * unit;
    const x0 = cursor;
    cursor += w + gapFrac * unit;
    return { ...d, x0, w };
  });
}

function toggleElecBarsKey(key){
  if(elecBarsHidden.has(key)) elecBarsHidden.delete(key); else elecBarsHidden.add(key);
  if(elecBarsCountry) renderElectrificationBarsChart(elecBarsCountry);
}

// injected once, lazily, on first render -- wraps the existing h2 in a .chart-header-row and adds
// a %/# of Units toggle next to it, matching the "Electrified Share by Country" section's pattern.
function ensureElecBarsModeToggle(){
  if(document.getElementById('elec-bars-mode-toggle')) return;
  const titleEl = document.getElementById('elec-bars-title');
  if(!titleEl) return;
  const headerRow = document.createElement('div');
  headerRow.className = 'chart-header-row';
  titleEl.parentNode.insertBefore(headerRow, titleEl);
  headerRow.appendChild(titleEl);
  const toggle = document.createElement('div');
  toggle.id = 'elec-bars-mode-toggle';
  toggle.className = 'chart-mode-toggle lg';
  toggle.setAttribute('role', 'group');
  toggle.setAttribute('aria-label', 'Bar display mode');
  toggle.innerHTML = `
    <button type="button" class="mode-btn active" data-elec-bars-mode="pct" title="Show each period's mix as a % of its own total registrations.">%</button>
    <button type="button" class="mode-btn" data-elec-bars-mode="raw" title="Show actual unit counts."># of Units</button>
  `;
  headerRow.appendChild(toggle);
  toggle.addEventListener('click', e => {
    const btn = e.target.closest('[data-elec-bars-mode]');
    if(!btn || btn.dataset.elecBarsMode === elecBarsMode) return;
    elecBarsMode = btn.dataset.elecBarsMode;
    toggle.querySelectorAll('[data-elec-bars-mode]').forEach(b => b.classList.toggle('active', b === btn));
    if(elecBarsCountry) renderElectrificationBarsChart(elecBarsCountry);
  });
}

function renderElectrificationBarsChart(country){
  const card = document.getElementById('elec-bars-card');
  if(!card) return;
  elecBarsCountry = country;
  const series = buildElectrificationBarsSeries(country).filter(d => d.total);
  if(series.length === 0){ card.classList.add('hidden'); return; }
  card.classList.remove('hidden');
  ensureElecBarsModeToggle();

  const visibleKeys = ELEC_BARS_ALL_KEYS.filter(k => !elecBarsHidden.has(k));

  // one row per period, carrying both the raw units (under _raw) and whichever unit the current
  // mode displays (% of total, or the raw count itself) under each fuel key directly
  const displaySeries = series.map(d => {
    const row = { label: d.label, total: d.total, isPartial: d.isPartial, isYear: d.isYear, _raw: d };
    ELEC_BARS_ALL_KEYS.forEach(k => {
      const raw = d[k] || 0;
      row[k] = elecBarsMode === 'raw' ? raw : (d.total ? raw / d.total * 100 : 0);
    });
    return row;
  });

  document.getElementById('elec-bars-title').textContent = `Electrification Mix — ${country}`;
  document.getElementById('elec-bars-note').textContent = ELEC_BARS_NOTE +
    (country === 'Canada' ? ' Statistics Canada reports quarterly, not monthly -- each "month" bar here is really its whole quarter, labeled at the quarter\'s first month.' : '');
  document.getElementById('elec-bars-legend').innerHTML = ELEC_BARS_ALL_KEYS.map(k => `
    <div class="legend-chip${elecBarsHidden.has(k) ? ' dimmed' : ''}" data-fuel="${k}" style="cursor:pointer"><span class="swatch" style="background:${FUEL_COLORS[k]}"></span>${FUEL_LABELS[k]}</div>
  `).join('');
  const legendEl = document.getElementById('elec-bars-legend');
  legendEl.onclick = e => {
    const chip = e.target.closest('.legend-chip');
    if(chip) toggleElecBarsKey(chip.dataset.fuel);
  };

  const svgEl = document.getElementById('elec-bars-svg');
  const svg = d3.select(svgEl);
  const tooltip = document.getElementById('elec-bars-tooltip');
  const wrap = svgEl.closest('.chart-card');
  svg.selectAll('*').remove();

  const W = 900, H = 320, M = { top: 16, right: 16, bottom: displaySeries.length > 6 ? 56 : 34, left: elecBarsMode === 'raw' ? 50 : 38 };
  const innerW = W - M.left - M.right;
  const innerH = H - M.top - M.bottom;

  const laidOut = elecBarsLayout(displaySeries, innerW);
  const yMax = elecBarsMode === 'raw'
    ? Math.max(1, ...displaySeries.map(d => visibleKeys.reduce((s, k) => s + d[k], 0)))
    : ELEC_BARS_Y_MAX;
  const yScale = d3.scaleLinear().domain([0, yMax]).range([innerH, 0]);
  if(elecBarsMode === 'raw') yScale.nice();

  const g = svg.append('g').attr('transform', `translate(${M.left},${M.top})`);

  // y axis
  const yAxis = elecBarsMode === 'raw'
    ? d3.axisLeft(yScale).ticks(5).tickFormat(d3.format('~s'))
    : d3.axisLeft(yScale).tickValues([0, 20, 40, 60, 80, 100]).tickFormat(d => d + '%');
  g.append('g').attr('class', 'bubble-axis').call(yAxis);

  // x axis -- drawn manually since bar widths vary (years wider than months), which
  // d3.scaleBand can't express. Ticks still use the .tick/.domain classes so they pick up
  // the same styling as every d3-generated axis elsewhere on the site (see styles.css).
  const xAxisG = g.append('g').attr('class', 'bubble-axis').attr('transform', `translate(0,${innerH})`);
  xAxisG.append('line').attr('class', 'domain').attr('x1', 0).attr('x2', innerW).attr('y1', 0).attr('y2', 0);
  const rotateLabels = displaySeries.length > 6;
  laidOut.forEach(d => {
    const cx = d.x0 + d.w / 2;
    const tick = xAxisG.append('g').attr('class', 'tick').attr('transform', `translate(${cx},0)`);
    tick.append('line').attr('x1', 0).attr('x2', 0).attr('y1', 0).attr('y2', 6);
    const label = tick.append('text').attr('x', 0).attr('y', rotateLabels ? 10 : 20).text(d.label);
    if(rotateLabels){
      label.attr('transform', 'rotate(-40)').style('text-anchor', 'end');
    } else {
      label.style('text-anchor', 'middle');
    }
  });

  // stacked bars, drawn fuel-by-fuel in the site-wide canonical order (bev, phev, hev, petrol,
  // diesel) -- hidden keys (petrol/diesel, by default) are simply skipped, not drawn at height 0,
  // so revealing one adds it on top of whatever's already shown rather than leaving a gap.
  let baseline = laidOut.map(() => 0);
  visibleKeys.forEach(key => {
    g.selectAll(`.elec-bar-${key}`)
      .data(laidOut)
      .join('rect')
      .attr('class', `elec-bar-${key}`)
      .attr('x', d => d.x0)
      .attr('width', d => d.w)
      .attr('y', (d, i) => yScale(baseline[i] + d[key]))
      .attr('height', (d, i) => Math.max(0, yScale(baseline[i]) - yScale(baseline[i] + d[key])))
      .attr('fill', FUEL_COLORS[key])
      .attr('opacity', d => d.isPartial ? 0.75 : 1)
      .style('cursor', 'pointer')
      .on('click', () => toggleElecBarsKey(key))
      .on('pointermove', (e, d) => {
        const rect = wrap.getBoundingClientRect();
        tooltip.style.left = (e.clientX - rect.left) + 'px';
        tooltip.style.top = (e.clientY - rect.top - 10) + 'px';
        tooltip.style.opacity = 1;
        tooltip.innerHTML = `<strong>${d.label}${d.isPartial ? ' (YTD)' : ''}</strong><br>` +
          visibleKeys.map(k => `${FUEL_LABELS[k]}: <strong>${d._raw[k].toLocaleString('en-US')}</strong> (${(d._raw.total ? d._raw[k] / d._raw.total * 100 : 0).toFixed(1)}%)`).join('<br>') +
          `<br>Total: ${d.total.toLocaleString('en-US')}`;
      })
      .on('pointerleave', () => { tooltip.style.opacity = 0; });
    laidOut.forEach((d, i) => { baseline[i] += d[key]; });
  });

  // BEV label above each bar -- always the full BEV value (in whichever unit the current mode
  // uses), positioned above the top of the visible stack, only when BEV itself is shown
  if(visibleKeys.includes('bev')){
    g.selectAll('.elec-bar-bev-label')
      .data(laidOut)
      .join('text')
      .attr('class', 'elec-bar-bev-label')
      .attr('x', d => d.x0 + d.w / 2)
      .attr('y', d => yScale(visibleKeys.reduce((s, k) => s + d[k], 0)) - 6)
      .attr('text-anchor', 'middle')
      .style('font-size', '10.5px')
      .style('font-weight', '700')
      .style('font-variant-numeric', 'tabular-nums')
      .style('fill', 'var(--text)')
      .style('pointer-events', 'none')
      .text(d => elecBarsMode === 'raw' ? d.bev.toLocaleString('en-US') : d.bev.toFixed(1) + '%');
  }
}
