(function(){
'use strict';

var P = JSON.parse(document.getElementById('payload').textContent);
var DEALS = P.deals || [];
var UNVAL = P.unvalued || [];

/* ---------- helpers ---------- */
function fold(s){
  return (s==null?'':String(s)).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
}
function usd(n){
  if(n==null||isNaN(n)) return '';
  return '$'+Number(n).toLocaleString('en-US',{minimumFractionDigits:0,maximumFractionDigits:0});
}
function pct(n){ return n==null?'':Math.round(n*100)+'%'; }
function esc(s){
  return String(s==null?'':s).replace(/[&<>"']/g,function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
  });
}
var CC_NAME = {FR:'France',IT:'Italy',ES:'Spain',PT:'Portugal',AT:'Austria'};
var dn = null;
try{ dn = new Intl.DisplayNames(['en'],{type:'region'}); }catch(e){}
function ccName(cc){
  if(!cc) return '';
  if(CC_NAME[cc]) return CC_NAME[cc];
  try{ return dn ? dn.of(cc) : cc; }catch(e){ return cc; }
}
var FLAG_OK = {FR:1,IT:1,ES:1,PT:1,AT:1};
function ccEmoji(cc){
  return String.fromCodePoint(0x1F1E6+(cc.charCodeAt(0)-65), 0x1F1E6+(cc.charCodeAt(1)-65));
}
function flagCell(cc){
  if(!cc) return '<span class="dash">—</span>';
  var name = esc(ccName(cc));
  if(FLAG_OK[cc]) return '<span class="cflag" title="'+name+'" role="img" aria-label="'+name+'">'+ccEmoji(cc)+'</span>';
  return '<span class="cflag fallback" title="'+name+'">'+esc(cc)+'</span>';
}
var SRC_LABEL = {
  ws_vintage:'Wine-Searcher, vintage',
  ws_adjacent:'Wine-Searcher, adjacent vintage',
  ws_allvintage:'Wine-Searcher, all vintages',
  ws_single_retailer:'Single retailer',
  auction:'Auction hammer',
  estimate:'Model estimate'
};
function lvl(r,i){ return (r.region_path && r.region_path[i]) || ''; }
function link(id){ return 'https://www.winebid.com/BuyWine/Item/'+id; }

/* ---------- wine type ---------- */
/* The analyst's judgment of what is in the bottle -- the export has no such
   column. Stored unaccented so it survives a URL hash and a CSV round-trip;
   rendered with the accent. Ordered the way a list reads rather than
   alphabetically, so Red sits at one end and Dessert at the other. */
var WT_ORDER = ['Red','Rose','Orange','White','Sparkling','Dessert'];
var WT_LABEL = {Red:'Red',Rose:'Rosé',Orange:'Orange',White:'White',
                Sparkling:'Sparkling',Dessert:'Dessert'};
var WT_RANK = {};
WT_ORDER.forEach(function(t,i){ WT_RANK[t] = i+1; });
function wtLabel(t){ return WT_LABEL[t] || t || ''; }
function wtSwatch(t){
  if(!t) return '<span class="dash">—</span>';
  var n = esc(wtLabel(t));
  return '<span class="wt wt-'+esc(t)+'" title="'+n+'" role="img" aria-label="'+n+'"></span>';
}

/* ---------- searchable text ---------- */
[DEALS,UNVAL].forEach(function(set){
  set.forEach(function(r){
    r._country = ccName(r.country_code);
    r._search = fold([r.wine,r.region_raw,r.condition,r.flag,r.source,r._country,
                      r.vintage,r.format,wtLabel(r.wine_type)].join(' '));
  });
});

/* ---------- view definitions ---------- */
var COLS_DEALS = [
  {k:'country', label:'', hint:'country', type:'text', get:function(r){return r._country;},
   render:function(r){ return flagCell(r.country_code); }},
  {k:'wine_type', label:'', hint:'wine type', type:'rank', cls:'wtcell',
   get:function(r){return WT_RANK[r.wine_type]||0;},
   render:function(r){ return wtSwatch(r.wine_type); }},
  {k:'wine',  label:'Wine',    type:'text', cls:'wine', get:function(r){return fold(r.wine);},
   render:function(r){ return '<a href="'+link(r.id)+'" target="_blank" rel="noopener noreferrer">'+esc(r.wine)+'</a>'; }},
  {k:'vintage',label:'Vint',   type:'num', cls:'num', get:function(r){return r.vintage==null?-1:r.vintage;},
   render:function(r){ return r.vintage==null?'<span class="dash">NV</span>':r.vintage; }},
  {k:'format',label:'Format',  type:'text', get:function(r){return r.format||'';},
   render:function(r){ return esc(r.format||''); }},
  {k:'region',label:'Region',  type:'text', get:function(r){return fold(lvl(r,1));},
   render:function(r){ return esc(lvl(r,1))||'<span class="dash">—</span>'; }},
  {k:'subregion',label:'Subregion', type:'text', get:function(r){return fold(lvl(r,2));},
   render:function(r){ return esc(lvl(r,2))||'<span class="dash">—</span>'; }},
  {k:'qty',   label:'Qty',     type:'num', cls:'num', get:function(r){return r.qty||0;},
   render:function(r){ return r.qty==null?'':r.qty; }},
  {k:'reserve',label:'Reserve',type:'num', cls:'num', get:function(r){return r.reserve;},
   render:function(r){ return '<span class="soft">'+usd(r.reserve)+'</span>'; }},
  {k:'buyer_price',label:'Buyer price', type:'num', cls:'num', get:function(r){return r.buyer_price;},
   render:function(r){ return usd(r.buyer_price); }},
  {k:'market',label:'Market',  type:'num', cls:'num', get:function(r){return r.market;},
   render:function(r){ return usd(r.market); }},
  {k:'pct_below',label:'% Below', type:'num', cls:'pctcell', get:function(r){return r.pct_below;},
   render:function(r){
     var w = Math.max(2,Math.min(100,Math.round(r.pct_below*100)));
     var c = r.tag==='Steal'?'var(--steal-bar)':r.tag==='Great'?'var(--great-bar)':'var(--good-bar)';
     return '<span class="pctrow"><span class="v">'+pct(r.pct_below)+'</span>'+
            '<span class="bar"><i style="width:'+w+'%;background:'+c+'"></i></span></span>';
   }},
  {k:'tag',   label:'Tag',     type:'rank', get:function(r){return {Good:1,Great:2,Steal:3}[r.tag]||0;},
   render:function(r){ return '<span class="tag '+esc(r.tag)+'">'+esc(r.tag)+'</span>'; }},
  {k:'condition',label:'Condition', type:'text', get:function(r){return fold(r.condition);},
   render:function(r){ return r.condition ? '<span class="trunc" title="'+esc(r.condition)+'">'+esc(r.condition)+'</span>'
                                          : '<span class="dash">—</span>'; }},
  {k:'flag',  label:'Standout',type:'text', get:function(r){return fold(r.flag);},
   render:function(r){ return r.flag ? '<span class="standout" title="'+esc(r.flag)+'">'+esc(r.flag)+'</span>'
                                     : '<span class="dash">—</span>'; }},
  {k:'source',label:'Market source', type:'text', get:function(r){return fold(r.source);},
   render:function(r){ return '<span class="trunc" title="'+esc(r.source)+'">'+esc(r.source)+'</span>'; }}
];

var COLS_UNVAL = [
  {k:'country', label:'', hint:'country', type:'text', get:function(r){return r._country;},
   render:function(r){ return flagCell(r.country_code); }},
  {k:'wine_type', label:'', hint:'wine type', type:'rank', cls:'wtcell',
   get:function(r){return WT_RANK[r.wine_type]||0;},
   render:function(r){ return wtSwatch(r.wine_type); }},
  {k:'wine', label:'Wine', type:'text', cls:'wine', get:function(r){return fold(r.wine);},
   render:function(r){ return '<a href="'+link(r.id)+'" target="_blank" rel="noopener noreferrer">'+esc(r.wine)+'</a>'; }},
  {k:'vintage',label:'Vint', type:'num', cls:'num', get:function(r){return r.vintage==null?-1:r.vintage;},
   render:function(r){ return r.vintage==null?'<span class="dash">NV</span>':r.vintage; }},
  {k:'format',label:'Format', type:'text', get:function(r){return r.format||'';},
   render:function(r){ return esc(r.format||''); }},
  {k:'region',label:'Region', type:'text', get:function(r){return fold(lvl(r,1));},
   render:function(r){ return esc(lvl(r,1))||'<span class="dash">—</span>'; }},
  {k:'subregion',label:'Subregion', type:'text', get:function(r){return fold(lvl(r,2));},
   render:function(r){ return esc(lvl(r,2))||'<span class="dash">—</span>'; }},
  {k:'reserve',label:'Reserve', type:'num', cls:'num', get:function(r){return r.reserve;},
   render:function(r){ return usd(r.reserve); }},
  {k:'condition',label:'Condition', type:'text', get:function(r){return fold(r.condition);},
   render:function(r){ return r.condition ? '<span class="trunc" title="'+esc(r.condition)+'">'+esc(r.condition)+'</span>'
                                          : '<span class="dash">—</span>'; }}
];

/* facet + range definitions per view */
var FACETS = {
  country:  {label:'Country',    of:function(r){return r.country_code;}, disp:function(v){return ccName(v);}, cascade:0},
  region:   {label:'Region',     of:function(r){return lvl(r,1);},       disp:function(v){return v;},         cascade:1},
  subregion:{label:'Subregion',  of:function(r){return lvl(r,2);},       disp:function(v){return v;},         cascade:2},
  format:   {label:'Format',     of:function(r){return r.format;},       disp:function(v){return v;}},
  wtype:    {label:'Wine type',  of:function(r){return r.wine_type;},    disp:function(v){return wtLabel(v);},
             mark:function(v){return '<span class="wt wt-'+esc(v)+'" aria-hidden="true"></span>';},
             order:WT_ORDER},
  tag:      {label:'Deal tag',   of:function(r){return r.tag;},          disp:function(v){return v;}, order:['Steal','Great','Good']},
  src:      {label:'Market source', of:function(r){return r.source_type;}, disp:function(v){return SRC_LABEL[v]||v;}}
};
var RANGES = {
  pct:     {label:'% below market', of:function(r){return r.pct_below;}, fmt:function(v){return Math.round(v*100)+'%';}, step:0.01, hist:true},
  reserve: {label:'Reserve bid',    of:function(r){return r.reserve;},      fmt:usd, step:1},
  buyer:   {label:'Buyer price',    of:function(r){return r.buyer_price;},  fmt:usd, step:1},
  market:  {label:'Market price',   of:function(r){return r.market;},    fmt:usd, step:1},
  vintage: {label:'Vintage',        of:function(r){return r.vintage;},   fmt:function(v){return String(Math.round(v));}, step:1}
};
var VIEWS = {
  deals:   {rows:DEALS, cols:COLS_DEALS, facets:['country','region','subregion','wtype','format','tag','src'],
            ranges:['pct','buyer','reserve','market','vintage'], defaultSort:{col:'pct_below',dir:-1}},
  unvalued:{rows:UNVAL, cols:COLS_UNVAL, facets:['country','region','subregion','wtype','format'],
            ranges:['reserve','vintage'], defaultSort:{col:'reserve',dir:-1}}
};

/* ---------- state ---------- */
var state = {
  view:'deals', q:'',
  sel:{country:[],region:[],subregion:[],wtype:[],format:[],tag:[],src:[]},
  rng:{},               /* key -> [lo,hi] or null when untouched */
  sort:{col:'pct_below',dir:-1},
  standouts:false
};
var BOUNDS = {};        /* view -> key -> [min,max] */

function computeBounds(){
  Object.keys(VIEWS).forEach(function(v){
    BOUNDS[v] = {};
    VIEWS[v].ranges.forEach(function(k){
      var vals = VIEWS[v].rows.map(RANGES[k].of).filter(function(x){return x!=null && !isNaN(x);});
      BOUNDS[v][k] = vals.length ? [Math.min.apply(null,vals),Math.max.apply(null,vals)] : [0,1];
    });
  });
}
function bound(k){ return BOUNDS[state.view][k]; }
function rngOf(k){ return state.rng[k] || bound(k).slice(); }
function rngTouched(k){
  var r = state.rng[k]; if(!r) return false;
  var b = bound(k);
  return r[0]>b[0] || r[1]<b[1];
}

/* ---------- filtering ---------- */
function matches(r, except){
  var skip = except==null ? [] : (typeof except==='string' ? [except] : except);
  except = null;
  if(state.q){
    var terms = fold(state.q).split(/\s+/).filter(Boolean);
    for(var i=0;i<terms.length;i++) if(r._search.indexOf(terms[i])<0) return false;
  }
  if(state.view==='deals'){
    if(state.standouts && !r.flag) return false;
  }
  var cfg = VIEWS[state.view];
  for(var fi=0;fi<cfg.facets.length;fi++){
    var key = cfg.facets[fi];
    if(skip.indexOf(key)>=0) continue;
    var sel = state.sel[key];
    if(sel.length && sel.indexOf(FACETS[key].of(r))<0) return false;
  }
  for(var ri=0;ri<cfg.ranges.length;ri++){
    var rk = cfg.ranges[ri];
    if(skip.indexOf(rk)>=0) continue;
    if(!rngTouched(rk)) continue;
    var v = RANGES[rk].of(r);
    if(v==null || isNaN(v)) return false;
    var rr = rngOf(rk);
    if(v<rr[0] || v>rr[1]) return false;
  }
  return true;
}
function filtered(){ return VIEWS[state.view].rows.filter(function(r){return matches(r,null);}); }

function activeCount(){
  var n = 0, cfg = VIEWS[state.view];
  cfg.facets.forEach(function(k){ if(state.sel[k].length) n++; });
  cfg.ranges.forEach(function(k){ if(rngTouched(k)) n++; });
  if(state.q) n++;
  if(state.view==='deals' && state.standouts) n++;
  return n;
}

/* ---------- sorting ---------- */
function sorted(rows){
  var cfg = VIEWS[state.view];
  var col = cfg.cols.filter(function(c){return c.k===state.sort.col;})[0];
  if(!col) col = cfg.cols.filter(function(c){return c.k===cfg.defaultSort.col;})[0];
  var dir = state.sort.dir, get = col.get;
  return rows.slice().sort(function(a,b){
    var x = get(a), y = get(b);
    if(x==null) x = col.type==='text'?'':-Infinity;
    if(y==null) y = col.type==='text'?'':-Infinity;
    if(x<y) return -1*dir;
    if(x>y) return 1*dir;
    return (a.wine||'').localeCompare(b.wine||'');
  });
}

/* ---------- mobile sort select ----------
   The phone layout (<=640px, see template CSS) hides <thead>, so clicking a
   column header to sort isn't reachable there. This <select> drives the same
   state.sort/buildTable()/writeHash() path the desktop header click does --
   it's a second control on the same state, not a parallel implementation. */
var SORT_DIR_WORD = {
  text: {1:'A→Z', '-1':'Z→A'},
  num:  {1:'Low→High', '-1':'High→Low'},
  rank: {1:'Low→High', '-1':'High→Low'}
};
function buildMobileSort(){
  var sel = document.getElementById('mobileSort');
  if(!sel) return;
  var cfg = VIEWS[state.view];
  var opts = [];
  cfg.cols.forEach(function(c){
    if(c.sortable===false) return;
    var lbl = c.label || (c.hint ? c.hint.charAt(0).toUpperCase()+c.hint.slice(1) : c.k);
    var words = SORT_DIR_WORD[c.type] || SORT_DIR_WORD.num;
    var first = c.type==='text' ? 1 : -1;
    [first, -first].forEach(function(dir){
      opts.push('<option value="'+c.k+':'+dir+'">'+esc(lbl)+' ('+words[dir]+')</option>');
    });
  });
  sel.innerHTML = opts.join('');
  sel.value = state.sort.col+':'+state.sort.dir;
}

/* ---------- URL hash ---------- */
var HKEYS = {country:'c',region:'rg',subregion:'sr',wtype:'wt',format:'fmt',tag:'tag',src:'src'};
function writeHash(){
  var p = [];
  if(state.view!=='deals') p.push('v='+state.view);
  if(state.q) p.push('q='+encodeURIComponent(state.q));
  Object.keys(HKEYS).forEach(function(k){
    if(state.sel[k].length) p.push(HKEYS[k]+'='+state.sel[k].map(encodeURIComponent).join(','));
  });
  Object.keys(RANGES).forEach(function(k){
    if(VIEWS[state.view].ranges.indexOf(k)>=0 && rngTouched(k)){
      var r = rngOf(k); p.push(k+'='+r[0]+'~'+r[1]);
    }
  });
  var d = VIEWS[state.view].defaultSort;
  if(state.sort.col!==d.col || state.sort.dir!==d.dir) p.push('so='+state.sort.col+':'+(state.sort.dir>0?'a':'d'));
  if(state.standouts) p.push('st=1');
  var h = p.join('&');
  var target = h ? '#'+h : location.pathname+location.search;
  /* Chrome gives local files an opaque origin, and some builds reject
     replaceState there. Fall back to a plain fragment write, which is always
     allowed; never let a blocked history write break the render. */
  clearTimeout(writeHash._t);
  writeHash._t = setTimeout(function(){
    try{ history.replaceState(null,'',target); }
    catch(e){
      try{ if(location.hash !== (h?'#'+h:'')) location.hash = h; }catch(e2){}
    }
  },200);
}
function readHash(){
  var h = location.hash.replace(/^#/,''); if(!h) return;
  var rev = {}; Object.keys(HKEYS).forEach(function(k){ rev[HKEYS[k]] = k; });
  h.split('&').forEach(function(part){
    var i = part.indexOf('='); if(i<0) return;
    var k = part.slice(0,i), v = part.slice(i+1);
    if(k==='v' && VIEWS[v]) state.view = v;
    else if(k==='q') state.q = decodeURIComponent(v);
    else if(rev[k]) state.sel[rev[k]] = v.split(',').map(decodeURIComponent).filter(Boolean);
    else if(RANGES[k]){
      var mm = v.split('~').map(Number);
      if(mm.length===2 && !isNaN(mm[0]) && !isNaN(mm[1])) state.rng[k] = mm;
    }
    else if(k==='so'){
      var s = v.split(':'); state.sort = {col:s[0], dir:s[1]==='a'?1:-1};
    }
    else if(k==='st') state.standouts = v==='1';
  });
}

/* ---------- rendering: rail ---------- */
/* A parent level ignores its own children when counting options, so selecting
   a region never strands you unable to switch country. */
var CHILD_IGNORE = {country:['country','region','subregion'], region:['region','subregion'], subregion:['subregion']};

function facetOptions(key){
  var f = FACETS[key];
  var pool = VIEWS[state.view].rows.filter(function(r){ return matches(r, CHILD_IGNORE[key] || key); });
  var counts = {};
  pool.forEach(function(r){ var v = f.of(r); if(v) counts[v] = (counts[v]||0)+1; });
  state.sel[key].forEach(function(v){ if(!(v in counts)) counts[v] = 0; });
  var keys = Object.keys(counts);
  if(f.order) keys.sort(function(a,b){ return f.order.indexOf(a)-f.order.indexOf(b); });
  else keys.sort(function(a,b){ return String(f.disp(a)).localeCompare(String(f.disp(b))); });
  return keys.map(function(v){ return {v:v, n:counts[v], label:f.disp(v)}; });
}

function buildRail(){
  var cfg = VIEWS[state.view], html = '';
  cfg.facets.forEach(function(key){
    var opts = facetOptions(key), sel = state.sel[key];
    if(!opts.length) return;
    var open = sel.length>0 || key==='country' || key==='tag' || key==='wtype';
    html += '<details class="fgroup"'+(open?' open':'')+' data-facet="'+key+'">'+
      '<summary><span class="caret">▶</span>'+esc(FACETS[key].label)+
      (sel.length?'<span class="count">'+sel.length+'</span>':'')+'</summary>'+
      '<div class="fbody'+(opts.length>8?' scrolly':'')+'">';
    opts.forEach(function(o){
      var on = sel.indexOf(o.v)>=0;
      var mark = FACETS[key].mark ? FACETS[key].mark(o.v) : '';
      html += '<label class="opt'+(o.n===0&&!on?' off':'')+'">'+
        '<input type="checkbox" data-facet="'+key+'" value="'+esc(o.v)+'"'+(on?' checked':'')+'>'+
        mark+'<span class="lab">'+esc(o.label)+'</span><span class="n">'+o.n+'</span></label>';
    });
    html += '</div></details>';
  });

  cfg.ranges.forEach(function(key){
    var R = RANGES[key], b = bound(key), cur = rngOf(key);
    var histHtml = '';
    if(R.hist){
      var bins = 16, counts = new Array(bins).fill(0), max = 0;
      VIEWS[state.view].rows.forEach(function(r){
        var v = R.of(r); if(v==null) return;
        var i = Math.min(bins-1, Math.floor((v-b[0])/((b[1]-b[0])||1)*bins));
        counts[i]++;
      });
      max = Math.max.apply(null,counts)||1;
      histHtml = '<div class="hist">'+counts.map(function(c,i){
        var lo = b[0]+(b[1]-b[0])*i/bins, hi = b[0]+(b[1]-b[0])*(i+1)/bins;
        var on = hi>=cur[0] && lo<=cur[1];
        return '<span class="'+(on?'on':'')+'" style="height:'+Math.max(2,Math.round(c/max*100))+'%"></span>';
      }).join('')+'</div>';
    }
    var span = (b[1]-b[0])||1;
    var fl = (cur[0]-b[0])/span*100, fr = (cur[1]-b[0])/span*100;
    html += '<details class="fgroup" open data-range="'+key+'">'+
      '<summary><span class="caret">▶</span>'+esc(R.label)+
      (rngTouched(key)?'<span class="count">on</span>':'')+'</summary>'+
      '<div class="fbody"><div class="range">'+
        '<div class="vals"><span>'+esc(R.fmt(cur[0]))+'</span><span>'+esc(R.fmt(cur[1]))+'</span></div>'+
        '<div class="track">'+histHtml+
          '<div class="rail-line"></div><div class="fill" style="left:'+fl+'%;right:'+(100-fr)+'%"></div>'+
          '<input type="range" data-range="'+key+'" data-side="lo" min="'+b[0]+'" max="'+b[1]+'" step="'+R.step+'" value="'+cur[0]+'" aria-label="'+esc(R.label)+' minimum">'+
          '<input type="range" data-range="'+key+'" data-side="hi" min="'+b[0]+'" max="'+b[1]+'" step="'+R.step+'" value="'+cur[1]+'" aria-label="'+esc(R.label)+' maximum">'+
        '</div>'+
        (key==='pct' ? '<div class="note">Floors at '+Math.round(b[0]*100)+'% — lots below the deal cutoff are not in this file.</div>' : '')+
      '</div></div></details>';
  });

  if(state.view==='deals'){
    html += '<details class="fgroup" open><summary><span class="caret">▶</span>Shortlists</summary><div class="fbody">'+
      '<label class="opt"><input type="checkbox" id="fStandouts"'+(state.standouts?' checked':'')+'>'+
      '<span class="lab">Standouts only</span><span class="n">'+DEALS.filter(function(r){return r.flag;}).length+'</span></label>'+
      '</div></details>';
  }
  document.getElementById('railBody').innerHTML = html;
  document.getElementById('btnClear').disabled = activeCount()===0;
}

/* ---------- rendering: chips ---------- */
function buildChips(){
  var out = [], cfg = VIEWS[state.view];
  if(state.q) out.push(chip('Search','“'+state.q+'”','q',''));
  cfg.facets.forEach(function(k){
    state.sel[k].forEach(function(v){ out.push(chip(FACETS[k].label, FACETS[k].disp(v), 'facet', k+'|'+v)); });
  });
  cfg.ranges.forEach(function(k){
    if(rngTouched(k)){
      var r = rngOf(k);
      out.push(chip(RANGES[k].label, RANGES[k].fmt(r[0])+' – '+RANGES[k].fmt(r[1]), 'range', k));
    }
  });
  if(state.view==='deals' && state.standouts) out.push(chip('','Standouts only','standouts',''));
  document.getElementById('chips').innerHTML = out.join('');
}
function chip(label,val,kind,arg){
  return '<span class="chip">'+(label?'<b>'+esc(label)+':</b> ':'')+esc(val)+
         '<button data-chip="'+kind+'" data-arg="'+esc(arg)+'" aria-label="Remove filter">×</button></span>';
}

/* ---------- rendering: table ---------- */
/* Columns in this set form the compact "card header" line on the narrow
   (phone) layout -- flag, type swatch, wine name, deal tag -- instead of
   stacking as a labelled row like everything else. Desktop ignores this
   entirely; it only feeds the mobile CSS via data-label. */
var MOBILE_HEADER_COLS = {country:1, wine_type:1, wine:1, tag:1};
var lastRows = [];
function buildTable(){
  var cfg = VIEWS[state.view];
  var rows = sorted(filtered());
  lastRows = rows;

  document.getElementById('head').innerHTML = cfg.cols.map(function(c){
    if(c.sortable===false) return '<th style="width:26px"></th>';
    var on = state.sort.col===c.k;
    var ar = on ? (state.sort.dir>0?'ascending':'descending') : 'none';
    return '<th data-col="'+c.k+'" aria-sort="'+ar+'" title="Sort by '+esc(c.label||c.hint||c.k)+'">'+
      esc(c.label)+'<span class="arrow">'+(on&&state.sort.dir>0?'▲':'▼')+'</span></th>';
  }).join('');

  var body = document.getElementById('body');
  if(!rows.length){
    body.innerHTML = '';
    document.getElementById('emptyState').hidden = false;
    var n = activeCount();
    document.getElementById('emptyWhy').textContent =
      n ? n+' filter'+(n===1?'':'s')+' active. Remove one, or clear them all.'
        : 'This view has no lots.';
  } else {
    document.getElementById('emptyState').hidden = true;
    var html = new Array(rows.length);
    for(var i=0;i<rows.length;i++){
      var r = rows[i], tds = '';
      for(var j=0;j<cfg.cols.length;j++){
        var c = cfg.cols[j];
        var lbl = (c.label && !MOBILE_HEADER_COLS[c.k]) ? ' data-label="'+esc(c.label)+'"' : '';
        tds += '<td data-col="'+esc(c.k)+'"'+lbl+(c.cls?' class="'+c.cls+'"':'')+'>'+c.render(r)+'</td>';
      }
      html[i] = '<tr>'+tds+'</tr>';
    }
    body.innerHTML = html.join('');
  }
  buildMobileSort();

  var total = cfg.rows.length;
  document.getElementById('footCount').textContent =
    rows.length===total ? total+' lots' : rows.length+' of '+total+' lots';
  document.getElementById('footNote').textContent =
    state.view==='deals' ? ('Buyer price = reserve + '+Math.round((P.premium_rate||0)*100)+'% premium. Discount measured on buyer price; tax and shipping excluded.')
                         : 'No reliable market price found — excluded from deal ranking.';
}

/* ---------- rendering: summary ---------- */
function buildSummary(){
  var el = document.getElementById('summary');
  if(state.view!=='deals'){
    var n = filtered().length;
    el.innerHTML = metric('Unvalued lots', n+' <small>of '+UNVAL.length+'</small>')+
      metric('Total reserve', usd(filtered().reduce(function(s,r){return s+(r.reserve||0);},0)));
    return;
  }
  var rows = filtered();
  var by = {Good:0,Great:0,Steal:0};
  rows.forEach(function(r){ if(by[r.tag]!=null) by[r.tag]++; });
  var ps = rows.map(function(r){return r.pct_below;}).filter(function(x){return x!=null;}).sort(function(a,b){return a-b;});
  var med = ps.length ? (ps.length%2 ? ps[(ps.length-1)/2] : (ps[ps.length/2-1]+ps[ps.length/2])/2) : null;
  var best = ps.length ? ps[ps.length-1] : null;

  el.innerHTML =
    metric('Lots shown', rows.length+' <small>of '+DEALS.length+'</small>')+
    '<div class="metric"><span class="k">By tier</span><span class="v tierdots">'+
      '<i class="s">'+by.Steal+'</i><i class="r">'+by.Great+'</i><i class="g">'+by.Good+'</i></span></div>'+
    metric('Median discount', med==null?'—':pct(med))+
    metric('Best discount', best==null?'—':pct(best));
}
function metric(k,v){ return '<div class="metric"><span class="k">'+k+'</span><span class="v">'+v+'</span></div>'; }

/* ---------- funnel ---------- */
function buildFunnel(){
  var f = P.funnel;
  var host = document.getElementById('funnelPanel');
  if(!f){ host.hidden = true; return; }
  var steps = [
    ['In file','total'],['After country','after_country'],['After dessert','after_dessert'],
    ['After price','after_price'],['After condition','after_condition'],
    ['Valued','valued'],['Unvalued','unvalued'],['Deals','deals']
  ].filter(function(s){ return f[s[1]]!=null; });
  var prev = null;
  document.getElementById('funnelBody').innerHTML = steps.map(function(s){
    var v = f[s[1]], drop = (prev!=null && v<prev && s[1]!=='unvalued' && s[1]!=='deals') ? ('−'+(prev-v)) : '';
    if(['total','after_country','after_dessert','after_price','after_condition'].indexOf(s[1])>=0) prev = v;
    return '<div class="fstep"><span class="k">'+s[0]+'</span><span class="v">'+v+'</span>'+
           (drop?'<span class="d">'+drop+'</span>':'')+'</div>';
  }).join('');
}

/* ---------- CSV ---------- */
function csv(){
  var cfg = VIEWS[state.view];
  var cols = cfg.cols.filter(function(c){ return c.csv!==false; });
  var head = cols.map(function(c){
    return c.k==='country' ? 'Country' : c.k==='wine_type' ? 'Type' : c.label;
  }).concat(['Link']);
  function cell(r,c){
    if(c.k==='country') return r._country;
    if(c.k==='wine_type') return wtLabel(r.wine_type);
    if(c.k==='pct_below') return r.pct_below==null?'':(Math.round(r.pct_below*1000)/10)+'%';
    if(c.k==='reserve') return r.reserve==null?'':r.reserve;
    if(c.k==='buyer_price') return r.buyer_price==null?'':r.buyer_price;
    if(c.k==='market') return r.market==null?'':r.market;
    if(c.k==='region') return lvl(r,1);
    if(c.k==='subregion') return lvl(r,2);
    if(c.k==='vintage') return r.vintage==null?'NV':r.vintage;
    if(c.k==='source') return r.source||'';
    return r[c.k]==null?'':r[c.k];
  }
  function q(s){ s = String(s==null?'':s); return /[",\n]/.test(s) ? '"'+s.replace(/"/g,'""')+'"' : s; }
  return [head.map(q).join(',')].concat(lastRows.map(function(r){
    return cols.map(function(c){ return q(cell(r,c)); }).concat([link(r.id)]).join(',');
  })).join('\r\n');
}
function toast(msg){
  var t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('on');
  clearTimeout(t._t); t._t = setTimeout(function(){ t.classList.remove('on'); },2600);
}
function copyCsv(){
  var text = csv();
  var done = function(){ toast('Copied '+lastRows.length+' rows as CSV'); };
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(text).then(done, function(){ downloadCsv(text); });
  } else downloadCsv(text);
}
function downloadCsv(text){
  var blob = new Blob([text],{type:'text/csv'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'winebid-'+(P.auction_date||'export')+'-'+state.view+'.csv';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function(){ URL.revokeObjectURL(a.href); },1000);
  toast('Clipboard blocked — downloaded the CSV instead');
}

/* ---------- render orchestration ---------- */
var railScroll = 0;
function render(opts){
  opts = opts||{};
  if(!opts.keepRail){
    railScroll = document.getElementById('rail').scrollTop;
    buildRail();
    document.getElementById('rail').scrollTop = railScroll;
  }
  buildChips(); buildSummary(); buildTable(); writeHash();
}

/* ---------- events ---------- */
document.getElementById('railBody').addEventListener('change', function(e){
  var t = e.target;
  if(t.dataset.facet){
    var k = t.dataset.facet, v = t.value, arr = state.sel[k], i = arr.indexOf(v);
    if(t.checked){ if(i<0) arr.push(v); } else if(i>=0) arr.splice(i,1);
    if(k==='country') state.sel.region = state.sel.region.filter(function(x){
      return VIEWS[state.view].rows.some(function(r){ return lvl(r,1)===x && (!state.sel.country.length || state.sel.country.indexOf(r.country_code)>=0); });
    });
    if(k==='country'||k==='region') state.sel.subregion = state.sel.subregion.filter(function(x){
      return VIEWS[state.view].rows.some(function(r){
        return lvl(r,2)===x &&
          (!state.sel.country.length || state.sel.country.indexOf(r.country_code)>=0) &&
          (!state.sel.region.length || state.sel.region.indexOf(lvl(r,1))>=0);
      });
    });
    render();
  } else if(t.id==='fStandouts'){ state.standouts = t.checked; render(); }
});

document.getElementById('railBody').addEventListener('input', function(e){
  var t = e.target;
  if(!t.dataset.range) return;
  var k = t.dataset.range, b = bound(k), cur = rngOf(k).slice();
  var v = Number(t.value);
  if(t.dataset.side==='lo') cur[0] = Math.min(v, cur[1]);
  else cur[1] = Math.max(v, cur[0]);
  state.rng[k] = cur;
  /* update the visual track without rebuilding the rail (keeps the thumb grabbed) */
  var box = t.closest('.fgroup');
  var span = (b[1]-b[0])||1;
  box.querySelector('.fill').style.left = ((cur[0]-b[0])/span*100)+'%';
  box.querySelector('.fill').style.right = (100-(cur[1]-b[0])/span*100)+'%';
  var vals = box.querySelectorAll('.vals span');
  vals[0].textContent = RANGES[k].fmt(cur[0]); vals[1].textContent = RANGES[k].fmt(cur[1]);
  var hist = box.querySelectorAll('.hist span');
  if(hist.length){
    for(var i=0;i<hist.length;i++){
      var lo = b[0]+span*i/hist.length, hi = b[0]+span*(i+1)/hist.length;
      hist[i].classList.toggle('on', hi>=cur[0] && lo<=cur[1]);
    }
  }
  buildChips(); buildSummary(); buildTable(); writeHash();
});
document.getElementById('railBody').addEventListener('change', function(e){
  if(e.target.dataset.range) render();
});

document.getElementById('head').addEventListener('click', function(e){
  var th = e.target.closest('th'); if(!th || !th.dataset.col) return;
  var k = th.dataset.col;
  var col = VIEWS[state.view].cols.filter(function(c){return c.k===k;})[0];
  if(state.sort.col===k) state.sort.dir *= -1;
  else state.sort = {col:k, dir:(col.type==='text'?1:-1)};
  buildTable(); writeHash();
});

document.getElementById('mobileSort').addEventListener('change', function(e){
  var parts = e.target.value.split(':');
  state.sort = {col:parts[0], dir:Number(parts[1])};
  buildTable(); writeHash();
});

document.getElementById('chips').addEventListener('click', function(e){
  var b = e.target.closest('button[data-chip]'); if(!b) return;
  var kind = b.dataset.chip, arg = b.dataset.arg;
  if(kind==='q'){ state.q=''; document.getElementById('q').value=''; }
  else if(kind==='facet'){ var p = arg.split('|'); var k=p[0], v=p.slice(1).join('|');
    state.sel[k] = state.sel[k].filter(function(x){return x!==v;}); }
  else if(kind==='range') delete state.rng[arg];
  else if(kind==='standouts') state.standouts=false;
  render();
});

var qt;
document.getElementById('q').addEventListener('input', function(e){
  clearTimeout(qt); var v = e.target.value;
  qt = setTimeout(function(){ state.q = v; render(); },140);
});

Array.prototype.forEach.call(document.querySelectorAll('.views button'), function(btn){
  btn.addEventListener('click', function(){
    if(state.view===btn.dataset.view) return;
    state.view = btn.dataset.view;
    Array.prototype.forEach.call(document.querySelectorAll('.views button'), function(b){
      b.setAttribute('aria-selected', String(b===btn));
    });
    state.sort = Object.assign({}, VIEWS[state.view].defaultSort);
    render();
  });
});

function clearAll(){
  Object.keys(state.sel).forEach(function(k){ state.sel[k] = []; });
  state.rng = {}; state.q = ''; state.standouts = false;
  document.getElementById('q').value = '';
  render();
}
document.getElementById('btnClear').addEventListener('click', clearAll);
document.getElementById('btnClear2').addEventListener('click', clearAll);
document.getElementById('btnCsv').addEventListener('click', copyCsv);

/* Two buttons open the same filter rail: #railToggle lives in the masthead
   (tablet width) and #railToggleMobile sits above the results list (phone
   width, see template CSS) -- a search-results-page placement rather than a
   header button. Both drive the same .rail.open toggle.

   On phone width the CSS turns .rail into a bottom-sheet tray instead of an
   inline block (see template.html's @media max-width:640px), so opening it
   also needs a backdrop and a scroll lock. Those are harmless no-ops at
   tablet/desktop width -- .railBackdrop stays display:none there via CSS,
   and locking body scroll while an *inline* rail is open would be wrong, so
   the lock only takes effect under the same 640px query (body.no-scroll is
   inert outside it). setRail() is the one place that changes the open
   state; everything else (buttons, backdrop, Escape) calls into it. */
function setRail(on){
  document.getElementById('rail').classList.toggle('open', on);
  document.getElementById('railBackdrop').classList.toggle('open', on);
  document.body.classList.toggle('no-scroll', on);
  document.querySelectorAll('.railToggleBtn').forEach(function(b){
    b.setAttribute('aria-pressed', String(on));
  });
}
function toggleRail(){
  setRail(!document.getElementById('rail').classList.contains('open'));
}
Array.prototype.forEach.call(document.querySelectorAll('.railToggleBtn'), function(btn){
  btn.addEventListener('click', toggleRail);
});
document.getElementById('railClose').addEventListener('click', function(){ setRail(false); });
document.getElementById('railBackdrop').addEventListener('click', function(){ setRail(false); });
document.addEventListener('keydown', function(e){
  if(e.key==='Escape' && document.getElementById('rail').classList.contains('open')) setRail(false);
});

/* ---------- boot ---------- */
computeBounds();
readHash();
document.getElementById('auctionLabel').textContent =
  (P.auction_date ? 'Auction ending '+P.auction_date : '') + (P.sample ? ' · sample' : '');
document.title = 'WineBid Scout'+(P.auction_date?' — '+P.auction_date:'');
if(P.sample) document.getElementById('sampleBanner').hidden = false;
document.getElementById('q').value = state.q;
Array.prototype.forEach.call(document.querySelectorAll('.views button'), function(b){
  b.setAttribute('aria-selected', String(b.dataset.view===state.view));
});
if(!VIEWS[state.view].cols.some(function(c){return c.k===state.sort.col;}))
  state.sort = Object.assign({}, VIEWS[state.view].defaultSort);
buildFunnel();
render();
})();
