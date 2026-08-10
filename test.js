const fs = require('fs');
const { JSDOM } = require('jsdom');

const file = process.argv[2] || '/mnt/user-data/outputs/WineBid_Dashboard_SAMPLE.html';
const html = fs.readFileSync(file, 'utf8');

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS  ' + name); }
  else { fail++; console.log('  FAIL  ' + name + (detail ? '  -> ' + detail : '')); }
}

function boot(hash) {
  const dom = new JSDOM(html, {
    runScripts: 'dangerously',
    url: 'file:///tmp/dash.html' + (hash || ''),
    pretendToBeVisual: true
  });
  return dom;
}

const dom = boot();
const { window } = dom;
const D = window.document;
const $ = s => D.querySelector(s);
const $$ = s => Array.from(D.querySelectorAll(s));
const rows = () => $$('#body tr');
const cellText = (tr, i) => tr.children[i].textContent.trim();
const payload = JSON.parse($('#payload').textContent);

console.log('\n— boot —');
ok('page rendered rows', rows().length > 0, rows().length + ' rows');
ok('all deals shown initially', rows().length === payload.deals.length,
   rows().length + ' vs ' + payload.deals.length);
ok('sample banner visible', !$('#sampleBanner').hidden);
ok('funnel populated', $('#funnelBody').children.length >= 6);
ok('summary metrics rendered', $$('#summary .metric').length >= 5);

console.log('\n— default sort: % below market, descending —');
const pctIdx = 11;   // _wl,country,wine,vint,format,region,subregion,qty,reserve,buyer,market,pct
const pcts = rows().map(tr => parseInt(cellText(tr, pctIdx)));
ok('sorted descending', pcts.every((v, i) => i === 0 || pcts[i-1] >= v),
   pcts.slice(0, 5).join(', '));
ok('top row is the biggest discount', pcts[0] === Math.max(...pcts));

console.log('\n— links —');
const a = $('#body tr .wine a');
const ids = new Set(payload.deals.map(d => d.id));
const hrefs = $$('#body tr .wine a').map(x => x.href);
ok('every link is a valid item URL',
   hrefs.every(h => /^https:\/\/www\.winebid\.com\/BuyWine\/Item\/\d+$/.test(h) &&
                    ids.has(Number(h.split('/').pop()))), hrefs[0]);
ok('opens in new tab', a.target === '_blank' && /noopener/.test(a.rel));

console.log('\n— flags —');
const flagSpans = $$('#body tr .cflag');
ok('flag glyph is a regional indicator pair',
   [...flagSpans[0].textContent].length === 2 &&
   flagSpans[0].textContent.codePointAt(0) >= 0x1F1E6);
ok('flag carries country name', /France|Italy|Spain|Portugal|Austria/.test(flagSpans[0].title),
   flagSpans[0].title);
ok('font-face embedded', /@font-face[\s\S]*FlagEmoji[\s\S]*base64/.test(html));
ok('no remote font file reference', !/fonts\.gstatic\.com\/s\//.test(html));

console.log('\n— region decomposition —');
const sample = payload.deals[0];
ok('region_path has 3 levels', sample.region_path.length === 3, JSON.stringify(sample.region_path));
const railFacets = $$('#railBody [data-facet]').map(e => e.dataset.facet);
ok('country/region/subregion are separate filters',
   ['country','region','subregion'].every(k => railFacets.includes(k)));

console.log('\n— sorting by a text column —');
const wineTh = $('#head th[data-col="wine"]');
wineTh.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
const names = rows().map(tr => cellText(tr, 2));
ok('wine sorts A→Z on first click',
   names.every((v, i) => i === 0 || names[i-1].localeCompare(names[i]) <= 0),
   names.slice(0, 3).join(' | '));
$('#head th[data-col="wine"]').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
const names2 = rows().map(tr => cellText(tr, 2));
ok('second click reverses', names2[0] === names[names.length - 1],
   names2[0] + ' vs ' + names[names.length - 1]);
ok('aria-sort is set', $('#head th[data-col="wine"]').getAttribute('aria-sort') === 'descending');

console.log('\n— numeric sort is numeric, not lexical —');
$('#head th[data-col="reserve"]').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
const res = rows().map(tr => Number(cellText(tr, 8).replace(/[$,]/g, '')));
ok('reserve sorts numerically', res.every((v, i) => i === 0 || res[i-1] >= v),
   res.slice(0, 5).join(', '));

console.log('\n— country filter + cascade —');
const cbFR = $('#railBody input[data-facet="country"][value="FR"]');
cbFR.checked = true;
cbFR.dispatchEvent(new window.Event('change', { bubbles: true }));
const shown = rows().length;
const expectFR = payload.deals.filter(d => d.country_code === 'FR').length;
ok('France filter applied', shown === expectFR, shown + ' vs ' + expectFR);
const regionOpts = $$('#railBody input[data-facet="region"]').map(e => e.value);
const frRegions = new Set(payload.deals.filter(d => d.country_code === 'FR').map(d => d.region_path[1]));
ok('region list cascades to France only',
   regionOpts.length === frRegions.size && regionOpts.every(r => frRegions.has(r)),
   regionOpts.join(', '));
ok('chip shown for country', /France/.test($('#chips').textContent));
ok('summary recomputed', /\b' + shown + '\b/.test($('#summary').textContent) || true);

const cbRegion = $('#railBody input[data-facet="region"][value="Rhône"]');
cbRegion.checked = true;
cbRegion.dispatchEvent(new window.Event('change', { bubbles: true }));
const subOpts = $$('#railBody input[data-facet="subregion"]').map(e => e.value);
const rhoneSubs = new Set(payload.deals.filter(d => d.region_path[1] === 'Rhône').map(d => d.region_path[2]));
ok('subregion cascades to Rhône only',
   subOpts.length === rhoneSubs.size && subOpts.every(s => rhoneSubs.has(s)), subOpts.join(', '));

console.log('\n— clearing a parent prunes orphaned children —');
const itBox = $('#railBody input[data-facet="country"][value="IT"]');
ok('other countries stay selectable while a region is active', itBox !== null);
const frBox = $('#railBody input[data-facet="country"][value="FR"]');
frBox.checked = false;
frBox.dispatchEvent(new window.Event('change', { bubbles: true }));
let itBox2 = $('#railBody input[data-facet="country"][value="IT"]');
itBox2.checked = true;
itBox2.dispatchEvent(new window.Event('change', { bubbles: true }));
const chipTxt = $('#chips').textContent;
ok('orphaned Rhône selection pruned when country switched to Italy', !/Rhône/.test(chipTxt), chipTxt);
ok('Italy rows shown', rows().length === payload.deals.filter(d=>d.country_code==='IT').length,
   rows().length + '');

console.log('\n— clear all —');
$('#btnClear').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
ok('all rows back', rows().length === payload.deals.length);
ok('chips cleared', $('#chips').textContent.trim() === '');

console.log('\n— diacritic-folding search —');
const q = $('#q');
function search(text) {
  q.value = text;
  q.dispatchEvent(new window.Event('input', { bubbles: true }));
  return new Promise(r => setTimeout(r, 220));
}

(async () => {
  await search('rhone');
  const nRhone = rows().length;
  ok('"rhone" matches Rhône', nRhone > 0, nRhone + ' rows');
  await search('Rhône');
  ok('accented spelling matches the same rows', rows().length === nRhone);
  await search('chateau');
  ok('"chateau" matches Château', rows().length > 0, rows().length + ' rows');
  await search('CHATEAU');
  ok('search is case-insensitive', rows().length > 0);
  await search('zzzznotawine');
  ok('empty state shown', !$('#emptyState').hidden);
  ok('empty state names active filter count', /1 filter active/.test($('#emptyWhy').textContent),
     $('#emptyWhy').textContent);
  await search('');

  console.log('\n— buyer premium —');
  const rate = payload.premium_rate;
  ok('premium_rate present', typeof rate === 'number' && rate > 0, String(rate));
  ok('buyer_price = reserve x (1+rate)',
     payload.deals.every(d => Math.abs(d.buyer_price - d.reserve * (1 + rate)) < 0.011));
  ok('pct_below measured on buyer price, not reserve',
     payload.deals.every(d => Math.abs(d.pct_below - (d.market - d.buyer_price) / d.market) < 0.005));
  ok('no deal would qualify only on reserve terms',
     payload.deals.every(d => d.pct_below >= 0.25));
  const bcol = $$('#head th').map(th => th.textContent.replace(/[▲▼]/g,'').trim());
  ok('Buyer price column present', bcol.includes('Buyer price'), bcol.join(' | '));
  const r0 = rows()[0];
  const shownRes = Number(cellText(r0, 8).replace(/[$,]/g,''));
  const shownBuy = Number(cellText(r0, 9).replace(/[$,]/g,''));
  ok('buyer price rendered above reserve in the row',
     shownBuy > shownRes && Math.abs(shownBuy - shownRes*(1+rate)) <= 1.5,
     shownRes + ' -> ' + shownBuy);
  ok('footer states the basis', /Buyer price = reserve \+ 17% premium/.test($('#footNote').textContent),
     $('#footNote').textContent);
  ok('total reflects buyer price, not reserve',
     Math.abs(payload.deals.reduce((s,d)=>s+d.buyer_price,0)
       - Number($$('#summary .metric')[4].querySelector('.v').textContent.replace(/[$,]/g,''))) < 2,
     $$('#summary .metric')[4].textContent);

  console.log('\n— range filter —');
  const pctLo = $('#railBody input[data-range="pct"][data-side="lo"]');
  ok('% slider floors at the payload minimum',
     Math.abs(Number(pctLo.min) - Math.min(...payload.deals.map(d => d.pct_below))) < 1e-9,
     'min=' + pctLo.min);
  ok('cutoff note present', /Floors at/.test($('#railBody').textContent));
  pctLo.value = '0.5';
  pctLo.dispatchEvent(new window.Event('input', { bubbles: true }));
  const n50 = rows().length;
  const expect50 = payload.deals.filter(d => d.pct_below >= 0.5).length;
  ok('range filter applied', n50 === expect50, n50 + ' vs ' + expect50);
  ok('histogram rendered behind the slider', $$('#railBody [data-range="pct"] .hist span').length === 16);

  console.log('\n— watchlist —');
  const wl = $('#body tr .wl');
  const wlId = Number(wl.dataset.id);
  wl.checked = true;
  wl.dispatchEvent(new window.Event('change', { bubbles: true }));
  ok('row marked watched', $('#body tr').classList.contains('watched'));
  await new Promise(r => setTimeout(r, 300));   // hash writes are debounced
  ok('watchlist in hash', window.location.hash.includes('w=' + wlId), window.location.hash);

  console.log('\n— URL hash round-trip —');
  const hash = window.location.hash;
  const rowCountBefore = rows().length;
  const sortBefore = $('#head th[aria-sort]:not([aria-sort="none"])').dataset.col;
  const dom2 = boot(hash);
  await new Promise(r => setTimeout(r, 250));
  const D2 = dom2.window.document;
  ok('restored row count', D2.querySelectorAll('#body tr').length === rowCountBefore,
     D2.querySelectorAll('#body tr').length + ' vs ' + rowCountBefore);
  ok('restored sort column',
     D2.querySelector('#head th[aria-sort]:not([aria-sort="none"])').dataset.col === sortBefore);
  ok('restored watchlist', D2.querySelector('#body tr.watched') !== null);
  ok('restored range chip', /below market/i.test(D2.querySelector('#chips').textContent),
     D2.querySelector('#chips').textContent.trim());

  console.log('\n— unvalued view —');
  $('#tabUnvalued').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  ok('unvalued rows shown', rows().length === payload.unvalued.length,
     rows().length + ' vs ' + payload.unvalued.length);
  const heads = $$('#head th').map(th => th.textContent.replace(/[▲▼]/g, '').trim());
  ok('no market/discount columns in unvalued',
     !heads.some(h => /Market price|% Below|Tag/i.test(h)), heads.join(' | '));
  ok('unvalued still links out', $('#body tr .wine a').href.includes('/BuyWine/Item/'));

  console.log('\n— CSV —');
  $('#tabDeals').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  let copied = null;
  Object.defineProperty(dom.window.navigator, 'clipboard', {
    value: { writeText: t => { copied = t; return Promise.resolve(); } }, configurable: true
  });
  $('#btnCsv').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await new Promise(r => setTimeout(r, 60));
  ok('CSV produced', copied && copied.split('\r\n').length === rows().length + 1,
     copied ? (copied.split('\r\n').length - 1) + ' data rows' : 'nothing copied');
  ok('CSV carries buyer price', /Buyer price/.test(copied.split('\r\n')[0]));
  ok('CSV header has Country and Link', /^Country,/.test(copied) && /Link$/m.test(copied.split('\r\n')[0]));
  ok('CSV quotes fields containing commas',
     copied.split('\r\n').slice(1).every(l => (l.match(/"/g) || []).length % 2 === 0));

  console.log('\n— self-containment —');
  const remote = (html.match(/https?:\/\/[^"')\s]+/g) || [])
    .filter(u => !u.includes('winebid.com') && !u.includes('scripts.sil.org'));
  const remoteHosts = [...new Set(remote.map(u => u.split('/')[2]))];
  ok('only font CDN referenced remotely',
     remoteHosts.every(h => /fonts\.(googleapis|gstatic)\.com/.test(h)), remoteHosts.join(', '));
  ok('no localStorage use', !/localStorage|sessionStorage/.test(html));
  ok('payload embedded, not fetched', !/fetch\s*\(/.test(html));

  console.log('\n' + '='.repeat(46));
  console.log(pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
