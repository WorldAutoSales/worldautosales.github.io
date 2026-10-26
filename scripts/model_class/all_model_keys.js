// node all_model_keys.js <repo root> <out.json>: [[modelKey, brand, most common model spelling, units]] for every model of the model tables
const fs = require('fs'), vm = require('vm'), path = require('path');
const root = process.argv[2], outFile = process.argv[3];
const html = fs.readFileSync(path.join(root, 'manufacturers.html'), 'utf8');
const BRAND_ALIASES = eval('(' + html.match(/const BRAND_ALIASES = (\{[^\n]*\});/)[1] + ')');
const ctx = {}; vm.createContext(ctx);
for (const f of ['manufacturer-model-monthly-data', 'manufacturer-model-yearly-data'])
  vm.runInContext(fs.readFileSync(path.join(root, 'assets', f + '.js'), 'utf8').replace(/^const /, 'var '), ctx);
const CATCH = /^\((other|unclassified)|^other\/discontinued|^(other|unknown)\b/i;
const alnum = x => String(x).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '');
const base = m => String(m).replace(/\s+(BEV|PHEV|HEV|ICE)$/i, '');
function key(brand, model){ const b = BRAND_ALIASES[brand] || brand, bk = alnum(b); let m = alnum(base(model)); if(m.startsWith(bk) && m.length > bk.length) m = m.slice(bk.length); return bk + '|' + m; }
const agg = new Map();
for (const src of [ctx.MANUFACTURER_MODEL_MONTHLY, ctx.MANUFACTURER_MODEL_YEARLY]) for (const rows of Object.values(src)) for (const r of rows) {
  if (CATCH.test(r.model)) continue;
  const k = key(r.brand, r.model); let a = agg.get(k);
  if (!a) { a = { k, b: BRAND_ALIASES[r.brand] || r.brand, names: new Map(), v: 0 }; agg.set(k, a); }
  a.v += r.total || 0; const d = base(r.model).trim(); a.names.set(d, (a.names.get(d) || 0) + 1);
}
const out = [...agg.values()].map(a => { let best = null, bn = -1; a.names.forEach((n, d) => { if (n > bn) { best = d; bn = n; } }); return [a.k, a.b, best, a.v]; }).sort((x, y) => y[3] - x[3]);
fs.writeFileSync(outFile, JSON.stringify(out));
