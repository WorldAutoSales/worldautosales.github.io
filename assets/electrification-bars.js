// "Electrification Mix — Recent" stacked bar chart: BEV/PHEV/HEV as a % of each period's total
// registrations (not stacked to 100% -- Petrol/Diesel/Others are intentionally left out). Periods
// are the last 3 full annual years, then either each real month of the current year so far, or a
// single YTD bar if no monthly breakdown exists for that country. Shared by country.html (always,
// for the URL country) and powertrain-mix-by-country.html (only while a country is focused).
// Requires COUNTRY_YEARLY, optionally COUNTRY_MONTHLY, FUEL_COLORS, FUEL_LABELS, and d3 already
// loaded, plus a card in the host page shaped like:
//   <div class="card chart-card" id="elec-bars-card">
//     <h2 id="elec-bars-title"></h2>
//     <p class="note" id="elec-bars-note"></p>
//     <div class="chart-legend" id="elec-bars-legend"></div>
//     <svg class="chart" id="elec-bars-svg" viewBox="0 0 900 320" preserveAspectRatio="none"></svg>
//     <div class="tooltip" id="elec-bars-tooltip"></div>
//   </div>

const ELEC_BARS_KEYS = ['bev', 'phev', 'hev'];
const ELEC_BARS_MONTH_ABBR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const ELEC_BARS_NOTE = "Battery Electric, Plug-in Hybrid, and Hybrid as a % of each period's total registrations -- not stacked to 100% (Petrol/Diesel/Others aren't shown). The last 3 full years, then each month of the current year so far, or year-to-date if no monthly breakdown exists. Click a legend swatch or any segment to isolate that powertrain; click again to bring the others back.";
// years are drawn this many times wider than a single month/YTD bar
const ELEC_BARS_YEAR_WIDTH_RATIO = 2.2;
// Y axis is fixed 0-100% (not auto-scaled to the country's own data) so charts are comparable
// across countries and never jump around when switching focus -- 100% comfortably covers the
// highest real value seen in this dataset (Norway, ~99.2% in March 2026).
const ELEC_BARS_Y_MAX = 100;

// isolate-on-click state -- module-level since only one instance of this chart is ever shown per
// page at a time (country.html has exactly one; powertrain-mix-by-country.html shows/hides its
// single instance based on focus). Scoped to this chart only, independent of the page-wide
// selectedFuels filter that powertrain-mix-by-country.html's other charts use, since this chart's
// bars aren't 100%-stacked and isolating shouldn't rescale them.
let elecBarsCountry = null;
let elecBarsIsolated = null;

function buildElectrificationBarsSeries(country){
  const yearly = (typeof COUNTRY_YEARLY !== 'undefined' && COUNTRY_YEARLY[country]) || [];
  const annualPeriods = yearly
    .filter(r => r.period_type === 'ANNUAL')
    .sort((a, b) => a.year - b.year)
    .slice(-3)
    .map(r => ({ label: String(r.year), bev: r.bev, phev: r.phev, hev: r.hev, total: r.total, isPartial: false, isYear: true }));

  const ytdRow = yearly.find(r => r.period_type === 'YTD');
  let currentPeriods = [];
  if(ytdRow && typeof COUNTRY_MONTHLY !== 'undefined' && COUNTRY_MONTHLY[country]){
    const yr = String(ytdRow.year);
    currentPeriods = COUNTRY_MONTHLY[country]
      .filter(r => r.ym.startsWith(yr))
      .sort((a, b) => a.ym.localeCompare(b.ym))
      .map(r => {
        const mm = parseInt(r.ym.slice(5, 7), 10);
        return { label: `${ELEC_BARS_MONTH_ABBR[mm - 1]} '${yr.slice(2)}`, bev: r.bev, phev: r.phev, hev: r.hev, total: r.total, isPartial: false, isYear: false };
      });
  }
  if(currentPeriods.length === 0 && ytdRow){
    currentPeriods = [{ label: `${ytdRow.year} YTD`, bev: ytdRow.bev, phev: ytdRow.phev, hev: ytdRow.hev, total: ytdRow.total, isPartial: true, isYear: false }];
  }
  return [...annualPeriods, ...currentPeriods];
}

// variable-width x positions: year bars wider than month/YTD bars, scaled to fill innerW
function elecBarsLayout(periods, innerW){
  const gapFrac = 0.4; // gap between bars, as a fraction of one narrow (month) bar's width
  const slots = periods.map(d => d.isYear ? ELEC_BARS_YEAR_WIDTH_RATIO : 1);
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

function toggleElecBarsIsolation(key){
  elecBarsIsolated = elecBarsIsolated === key ? null : key;
  if(elecBarsCountry) renderElectrificationBarsChart(elecBarsCountry);
}

function renderElectrificationBarsChart(country){
  const card = document.getElementById('elec-bars-card');
  if(!card) return;
  elecBarsCountry = country;
  const series = buildElectrificationBarsSeries(country).filter(d => d.total);
  if(series.length === 0){ card.classList.add('hidden'); return; }
  card.classList.remove('hidden');

  const pctSeries = series.map(d => {
    const pct = { label: d.label, total: d.total, isPartial: d.isPartial, isYear: d.isYear };
    ELEC_BARS_KEYS.forEach(k => { pct[k] = (d[k] || 0) / d.total * 100; });
    return pct;
  });

  document.getElementById('elec-bars-title').textContent = `Electrification Mix — ${country}`;
  document.getElementById('elec-bars-note').textContent = ELEC_BARS_NOTE +
    (country === 'Canada' ? ' Statistics Canada reports quarterly, not monthly -- each "month" bar here is really its whole quarter, labeled at the quarter\'s first month.' : '');
  document.getElementById('elec-bars-legend').innerHTML = ELEC_BARS_KEYS.map(k => `
    <div class="legend-chip${elecBarsIsolated && elecBarsIsolated !== k ? ' dimmed' : ''}" data-fuel="${k}" style="cursor:pointer"><span class="swatch" style="background:${FUEL_COLORS[k]}"></span>${FUEL_LABELS[k]}</div>
  `).join('');
  const legendEl = document.getElementById('elec-bars-legend');
  legendEl.onclick = e => {
    const chip = e.target.closest('.legend-chip');
    if(chip) toggleElecBarsIsolation(chip.dataset.fuel);
  };

  const svgEl = document.getElementById('elec-bars-svg');
  const svg = d3.select(svgEl);
  const tooltip = document.getElementById('elec-bars-tooltip');
  const wrap = svgEl.closest('.chart-card');
  svg.selectAll('*').remove();

  const W = 900, H = 320, M = { top: 16, right: 16, bottom: pctSeries.length > 6 ? 56 : 34, left: 38 };
  const innerW = W - M.left - M.right;
  const innerH = H - M.top - M.bottom;

  const laidOut = elecBarsLayout(pctSeries, innerW);
  const yScale = d3.scaleLinear().domain([0, ELEC_BARS_Y_MAX]).range([innerH, 0]);

  const g = svg.append('g').attr('transform', `translate(${M.left},${M.top})`);

  // y axis
  g.append('g')
    .attr('class', 'bubble-axis')
    .call(d3.axisLeft(yScale).tickValues([0, 20, 40, 60, 80, 100]).tickFormat(d => d + '%'));

  // x axis -- drawn manually since bar widths vary (years wider than months), which
  // d3.scaleBand can't express. Ticks still use the .tick/.domain classes so they pick up
  // the same styling as every d3-generated axis elsewhere on the site (see styles.css).
  const xAxisG = g.append('g').attr('class', 'bubble-axis').attr('transform', `translate(0,${innerH})`);
  xAxisG.append('line').attr('class', 'domain').attr('x1', 0).attr('x2', innerW).attr('y1', 0).attr('y2', 0);
  const rotateLabels = pctSeries.length > 6;
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

  // stacked bars, drawn fuel-by-fuel (bottom to top: BEV, PHEV, HEV)
  let baseline = laidOut.map(() => 0);
  ELEC_BARS_KEYS.forEach(key => {
    if(elecBarsIsolated && elecBarsIsolated !== key) return; // isolated to a different fuel: this one stays hidden
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
      .on('click', () => toggleElecBarsIsolation(key))
      .on('pointermove', (e, d) => {
        const rect = wrap.getBoundingClientRect();
        tooltip.style.left = (e.clientX - rect.left) + 'px';
        tooltip.style.top = (e.clientY - rect.top - 10) + 'px';
        tooltip.style.opacity = 1;
        tooltip.innerHTML = `<strong>${d.label}${d.isPartial ? ' (YTD)' : ''}</strong><br>` +
          ELEC_BARS_KEYS.map(k => `${FUEL_LABELS[k]}: <strong>${d[k].toFixed(1)}%</strong>`).join('<br>') +
          `<br>Total: ${d.total.toLocaleString('en-US')}`;
      })
      .on('pointerleave', () => { tooltip.style.opacity = 0; });
    laidOut.forEach((d, i) => { baseline[i] += d[key]; });
  });
}
