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
const ELEC_BARS_NOTE = "Battery Electric, Plug-in Hybrid, and Hybrid as a % of each period's total registrations -- not stacked to 100% (Petrol/Diesel/Others aren't shown). The last 3 full years, then each month of the current year so far, or year-to-date if no monthly breakdown exists.";

function buildElectrificationBarsSeries(country){
  const yearly = (typeof COUNTRY_YEARLY !== 'undefined' && COUNTRY_YEARLY[country]) || [];
  const annualPeriods = yearly
    .filter(r => r.period_type === 'ANNUAL')
    .sort((a, b) => a.year - b.year)
    .slice(-3)
    .map(r => ({ label: String(r.year), bev: r.bev, phev: r.phev, hev: r.hev, total: r.total, isPartial: false }));

  const ytdRow = yearly.find(r => r.period_type === 'YTD');
  let currentPeriods = [];
  if(ytdRow && typeof COUNTRY_MONTHLY !== 'undefined' && COUNTRY_MONTHLY[country]){
    const yr = String(ytdRow.year);
    currentPeriods = COUNTRY_MONTHLY[country]
      .filter(r => r.ym.startsWith(yr))
      .sort((a, b) => a.ym.localeCompare(b.ym))
      .map(r => {
        const mm = parseInt(r.ym.slice(5, 7), 10);
        return { label: `${ELEC_BARS_MONTH_ABBR[mm - 1]} '${yr.slice(2)}`, bev: r.bev, phev: r.phev, hev: r.hev, total: r.total, isPartial: false };
      });
  }
  if(currentPeriods.length === 0 && ytdRow){
    currentPeriods = [{ label: `${ytdRow.year} YTD`, bev: ytdRow.bev, phev: ytdRow.phev, hev: ytdRow.hev, total: ytdRow.total, isPartial: true }];
  }
  return [...annualPeriods, ...currentPeriods];
}

function renderElectrificationBarsChart(country){
  const card = document.getElementById('elec-bars-card');
  if(!card) return;
  const series = buildElectrificationBarsSeries(country).filter(d => d.total);
  if(series.length === 0){ card.classList.add('hidden'); return; }
  card.classList.remove('hidden');

  const pctSeries = series.map(d => {
    const pct = { label: d.label, total: d.total, isPartial: d.isPartial };
    ELEC_BARS_KEYS.forEach(k => { pct[k] = (d[k] || 0) / d.total * 100; });
    return pct;
  });

  document.getElementById('elec-bars-title').textContent = `Electrification Mix — ${country}`;
  document.getElementById('elec-bars-note').textContent = ELEC_BARS_NOTE +
    (country === 'Canada' ? ' Statistics Canada reports quarterly, not monthly -- each "month" bar here is really its whole quarter, labeled at the quarter\'s first month.' : '');
  document.getElementById('elec-bars-legend').innerHTML = ELEC_BARS_KEYS.map(k => `
    <div class="legend-chip"><span class="swatch" style="background:${FUEL_COLORS[k]}"></span>${FUEL_LABELS[k]}</div>
  `).join('');

  const svgEl = document.getElementById('elec-bars-svg');
  const svg = d3.select(svgEl);
  const tooltip = document.getElementById('elec-bars-tooltip');
  const wrap = svgEl.closest('.chart-card');
  svg.selectAll('*').remove();

  const W = 900, H = 320, M = { top: 16, right: 16, bottom: pctSeries.length > 6 ? 56 : 34, left: 38 };
  const innerW = W - M.left - M.right;
  const innerH = H - M.top - M.bottom;

  const xScale = d3.scaleBand().domain(pctSeries.map(d => d.label)).range([0, innerW]).padding(0.3);
  const yMax = Math.max(10, d3.max(pctSeries, d => ELEC_BARS_KEYS.reduce((s, k) => s + d[k], 0)) * 1.15);
  const yScale = d3.scaleLinear().domain([0, yMax]).range([innerH, 0]);

  const g = svg.append('g').attr('transform', `translate(${M.left},${M.top})`);

  const xAxis = g.append('g')
    .attr('class', 'bubble-axis')
    .attr('transform', `translate(0,${innerH})`)
    .call(d3.axisBottom(xScale));
  if(pctSeries.length > 6){
    xAxis.selectAll('text')
      .attr('transform', 'rotate(-40)')
      .style('text-anchor', 'end');
  }

  g.append('g')
    .attr('class', 'bubble-axis')
    .call(d3.axisLeft(yScale).ticks(5).tickFormat(d => d + '%'));

  const stacked = d3.stack().keys(ELEC_BARS_KEYS)(pctSeries);

  stacked.forEach(layer => {
    g.selectAll(`.elec-bar-${layer.key}`)
      .data(layer)
      .join('rect')
      .attr('class', `elec-bar-${layer.key}`)
      .attr('x', d => xScale(d.data.label))
      .attr('width', xScale.bandwidth())
      .attr('y', d => yScale(d[1]))
      .attr('height', d => Math.max(0, yScale(d[0]) - yScale(d[1])))
      .attr('fill', FUEL_COLORS[layer.key])
      .attr('opacity', d => d.data.isPartial ? 0.75 : 1)
      .on('pointermove', (e, d) => {
        const rect = wrap.getBoundingClientRect();
        tooltip.style.left = (e.clientX - rect.left) + 'px';
        tooltip.style.top = (e.clientY - rect.top - 10) + 'px';
        tooltip.style.opacity = 1;
        tooltip.innerHTML = `<strong>${d.data.label}${d.data.isPartial ? ' (YTD)' : ''}</strong><br>` +
          ELEC_BARS_KEYS.map(k => `${FUEL_LABELS[k]}: <strong>${d.data[k].toFixed(1)}%</strong>`).join('<br>') +
          `<br>Total: ${d.data.total.toLocaleString('en-US')}`;
      })
      .on('pointerleave', () => { tooltip.style.opacity = 0; });
  });
}
