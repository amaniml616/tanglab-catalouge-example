#!/usr/bin/env python3
"""
Build the Tang Lab catalogue site (index.html + crops/) from the inventory repository.

  python3 handbook/build_catalogue.py                 -> handbook/_site/catalogue/
  python3 handbook/build_catalogue.py --out /var/www/html/catalogue
  python3 handbook/build_catalogue.py --out DIR --extra /var/lib/tanglab/extra
  python3 handbook/build_catalogue.py --out DIR --config handbook/handbook.pages.json   (stand-alone, e.g. GitHub Pages)

--extra DIR adds items entered through the website's "Add an item" form:
  DIR/added.csv            same 13 columns as optics_catalog.csv
  DIR/crops/<ID>.jpg       their photos

Reads (all in this repository):
  optics_catalog.csv       the inventory (single source of truth)
  crops/<ID>.jpg           one photo per item
  build.py                 only for its category table (GROUPS / SUPER), so the
                           sections match the repository's own site
  handbook/manuals.csv     ID,Manual URL  - shown in each item's expanded row
  handbook/handbook.json   where the wiki lives, and the sidebar menu

Standard library only.
"""
import csv, html, json, os, re, shutil, sys
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
args = sys.argv[1:]
def opt(name, default):
    return args[args.index(name) + 1] if name in args else default
OUT = os.path.abspath(opt('--out', os.path.join(HERE, '_site', 'catalogue')))
EXTRA = os.path.abspath(opt('--extra', '')) if '--extra' in args else None

CFGFILE = os.path.abspath(opt('--config', os.path.join(HERE, 'handbook.json')))
cfg = json.load(open(CFGFILE, encoding='utf-8'))
WIKI = cfg.get('wiki_url', '/wiki/doku.php?id=')

# ---- taxonomy, taken from the repository's own build.py so the two never disagree
src = open(os.path.join(REPO, 'build.py'), encoding='utf-8').read()
ns = {}
exec('import re\n' + src[src.index('GROUPS = ['):src.index('FLAGWORDS')], ns)
group_of, SUPER, SUPER_OF = ns['group_of'], ns['SUPER'], ns['SUPER_OF']
FLAGWORDS = ("FLAG", "TBD", "MEASURE", "UNOPENED", "UNVERIFIED", "NOT CONFIRMED", "NOT MARKED", "UNKNOWN")

rows = list(csv.DictReader(open(os.path.join(REPO, 'optics_catalog.csv'), encoding='utf-8')))
repo_ids = {r['ID'] for r in rows}
added_ids = set()
if EXTRA and os.path.exists(os.path.join(EXTRA, 'added.csv')):
    for r in csv.DictReader(open(os.path.join(EXTRA, 'added.csv'), encoding='utf-8')):
        if r['ID'] in repo_ids or r['ID'] in added_ids:
            print('WARNING: skipping site-added item', r['ID'], '- ID already in the inventory repository; renumber it in added.csv', file=sys.stderr)
            continue
        added_ids.add(r['ID']); rows.append(r)
byid = {r['ID']: r for r in rows}

manuals = {}
mp = os.path.join(HERE, 'manuals.csv')
if os.path.exists(mp):
    for r in csv.DictReader(open(mp, encoding='utf-8')):
        i, u = (r.get('ID') or '').strip(), (r.get('Manual URL') or '').strip()
        if i and urlparse(u).scheme in ('http', 'https'):
            manuals[i] = u

e = html.escape

def link_ids(text):
    return re.sub(r'\b([A-Z]{3}-\d{3})\b',
                  lambda m: f'<a class="idl" href="#{m.group(1)}">{m.group(1)}</a>' if m.group(1) in byid else m.group(1),
                  e(text))

def photo_path(i):
    for base in (os.path.join(REPO, 'crops'), os.path.join(EXTRA, 'crops') if EXTRA else None):
        if base and os.path.exists(os.path.join(base, i + '.jpg')): return os.path.join(base, i + '.jpg')
has_photo = lambda i: photo_path(i) is not None
items, nflag = [], 0
for r in rows:
    g = group_of(r['Category']); s = SUPER_OF.get(g, 'Optics Components')
    blob = ' '.join(str(v or '') for v in r.values())
    flag = any(w in blob for w in FLAGWORDS); nflag += flag
    notes = r['Notes (Function & Operating Range)']
    spec = [('Maker', r['Manufacturer']), ('Part no.', r['Part Number']), ('Wavelength', r['Wavelength Range']),
            ('Size', r['Aperture / Size']), ('Key spec', r['Focal Length / Key Spec']), ('Bench', r['Setup'])]
    spec_h = ''.join(f'<dt>{k}</dt><dd>{e(v)}</dd>' for k, v in spec if v and v.strip() and v.strip().lower() != 'n/a')
    ph = (f'<img class="ph" loading="lazy" alt="" src="crops/{r["ID"]}.jpg">' if has_photo(r['ID']) else '<span class="ph none"></span>')
    hay = e(' '.join([r['ID'], r['Item Name'], r['Manufacturer'], r['Part Number'], r['Setup'], g, notes]).lower())
    url = manuals.get(r['ID'])
    if url:
        man = f'<div class="man"><span class="lbl">Manual</span><div class="mrow"><a href="{e(url)}" target="_blank" rel="noopener noreferrer">Open manual</a><span class="mhost">{e(urlparse(url).hostname or "")}</span></div></div>'
    else:
        man = '<div class="man"><span class="lbl">Manual</span><div class="mrow"><span class="nomanual">No manual linked yet. Add one line to <code>handbook/manuals.csv</code>.</span></div></div>'
    items.append(f'<details class="it{" flagged" if flag else ""}" id="{r["ID"]}" data-s="{e(s)}" data-g="{e(g)}" data-f="{int(flag)}" data-h="{hay}"><summary>{ph}<span class="iid">{r["ID"]}</span><span class="inm">{e(r["Item Name"])}</span><span class="imk">{e(r["Manufacturer"])}</span><span class="iq">×{e(r["Qty"])}</span>{"<span class=itag>check</span>" if flag else ""}{"<span class=itagnew>added here</span>" if r["ID"] in added_ids else ""}</summary><div class="ib"><dl>{spec_h}</dl><p>{link_ids(notes)}</p>{man}</div></details>')

supers = [s for s, _ in SUPER]
sc = {s: sum(1 for r in rows if SUPER_OF.get(group_of(r['Category']), 'Optics Components') == s) for s in supers}
chips = ''.join(f'<button class="chip" data-s="{e(s)}">{e(s)} <i>{sc[s]}</i></button>' for s in supers)
groups = sorted({group_of(r['Category']) for r in rows})

n = 0; nav = []
for item in cfg['nav']:
    href = item['url'] if item.get('url') else ((WIKI + item['id']) if not item['id'].startswith('@') else '#top')
    if item.get('sub'):
        nav.append(f'<a href="{e(href)}" data-p="x" class="sub"><span></span>{e(item["title"])}</a>')
    else:
        n += 1; on = ' class="on"' if item['id'] == '@catalogue' else ''
        nav.append(f'<a href="{e(href)}" data-p="x"{on}><span>{n:02d}</span>{e(item["title"])}</a>')

add_html, add_js = '', ''
add_cfg = cfg.get('add_item')
if add_cfg:
    from collections import Counter as _C
    _k = {}
    for r in rows: _k.setdefault(r['ID'].split('-')[0], _C())[r['Category']] += 1
    add_data = {'repo': add_cfg.get('repo') or os.environ.get('GITHUB_REPOSITORY', ''),
                'branch': add_cfg.get('branch') or os.environ.get('GITHUB_REF_NAME', '') or 'main',
                'model': add_cfg.get('model', 'claude-sonnet-5-5'),
                'types': [{'prefix': k, 'category': c.most_common(1)[0][0], 'group': group_of(c.most_common(1)[0][0])} for k, c in sorted(_k.items())]}
    add_html = open(os.path.join(HERE, 'assets', 'add.html'), encoding='utf-8').read() + \
        '<script id="add-data" type="application/json">' + json.dumps(add_data).replace('</', '<\\/') + '</script>'
    add_js = open(os.path.join(HERE, 'assets', 'add.js'), encoding='utf-8').read()

side_html = f'''<nav class="side"><a class="brand" href="{e(cfg.get('brand_url', WIKI + 'start'))}">{e(cfg.get('title', 'Tang Lab'))}<br><small>{e(cfg.get('subtitle', 'Wiki'))}</small></a>{''.join(nav)}</nav>'''
body = f'''<div class="shell">{side_html}
<main><section class="page" id="p-catalogue" style="max-width:900px">
<h1 id="top">Catalogue</h1>
<p class="lede"><span class="tot">{len(rows)}</span> items, each with a photo, an identification and notes on how not to break it. Rows marked <span class="itag">check</span> contain something unconfirmed or unmeasured (<span class="nfl">{nflag}</span> of them). {"" if cfg.get('standalone') else '<a href="' + e(cfg.get('add_url', '/wiki/add_item.php')) + '">Add an item</a> (wiki login needed) or see <a href="' + e(WIKI + 'adding_items') + '">how the inventory is kept</a>.'}</p>
<div class="tools"><input id="q" type="search" placeholder="Search name, maker, part number, notes" aria-label="Search the catalogue"><label class="fl"><input id="onlyf" type="checkbox"> Needs check only</label><select id="grp" aria-label="Category"><option value="">All categories</option>{''.join(f'<option>{e(g)}</option>' for g in groups)}</select></div>
<div class="chips"><button class="chip on" data-s="">All <i>{len(rows)}</i></button>{chips}</div>
<p id="cnt" class="cnt"></p>
<div id="list">{''.join(items)}</div>
</section>{add_html}</main></div>'''

js = r'''(function(){
var q=document.getElementById('q'),grp=document.getElementById('grp'),onlyf=document.getElementById('onlyf'),cnt=document.getElementById('cnt'),chips=document.querySelectorAll('.chip'),its=document.querySelectorAll('.it'),sup='';
function apply(){var t=q.value.trim().toLowerCase().split(/\s+/).filter(Boolean),n=0;
 its.forEach(function(e){var ok=(!sup||e.dataset.s===sup)&&(!grp.value||e.dataset.g===grp.value)&&(!onlyf.checked||e.dataset.f==='1')&&t.every(function(w){return e.dataset.h.indexOf(w)>-1});e.hidden=!ok;if(ok)n++});
 cnt.textContent=n+' of '+its.length+' shown'}
function clear(){q.value='';grp.value='';onlyf.checked=false;sup='';chips.forEach(function(c){c.classList.toggle('on',c.dataset.s==='')});apply()}
q.addEventListener('input',apply);grp.addEventListener('change',apply);onlyf.addEventListener('change',apply);
chips.forEach(function(c){c.addEventListener('click',function(){sup=c.dataset.s;chips.forEach(function(x){x.classList.toggle('on',x===c)});apply()})});
function openItem(id){var it=id&&document.getElementById(id);if(it&&it.classList.contains('it')){clear();it.open=true;setTimeout(function(){it.scrollIntoView({block:'start'})},30);return true}return false}
function view(){var a=location.hash==='#add',pa=document.getElementById('p-add');if(!pa)return;document.getElementById('p-catalogue').hidden=a;pa.hidden=!a;
 document.querySelectorAll('.side a[data-p]').forEach(function(l){var h=l.getAttribute('href');l.classList.toggle('on',a?h==='#add':h==='#top')});if(a)window.scrollTo(0,0)}
function route(){view();var m=/[?&]item=([A-Za-z0-9-]+)/.exec(location.search),h=decodeURIComponent(location.hash.slice(1));if(!(m&&openItem(m[1])))openItem(h)}
window.addEventListener('hashchange',route);
apply();route();
})();'''
css = open(os.path.join(HERE, 'assets', 'catalogue.css'), encoding='utf-8').read()
page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tang Lab Catalogue</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{css}</style></head><body>{body}<script>{js}</script>{('<script>' + add_js + '</script>') if add_js else ''}</body></html>'''

def shareable(path):
    """Group-writable, so the wiki's web user and the GitHub runner user can both rebuild."""
    try: os.chmod(path, 0o2775 if os.path.isdir(path) else 0o664)
    except OSError: pass

def write(name, text):
    p = os.path.join(OUT, name)
    open(p, 'w', encoding='utf-8').write(text); shareable(p)

os.makedirs(OUT, exist_ok=True); shareable(OUT)
write('index.html', page)
write('catalogue.css', css)
write('nav.html', side_html)

# what the "Add an item" form needs: item types (ID prefix + Category value) and every ID in use
from collections import Counter
kinds = {}
for r in rows:
    kinds.setdefault(r['ID'].split('-')[0], Counter())[r['Category']] += 1
types = [{'prefix': k, 'category': c.most_common(1)[0][0], 'group': group_of(c.most_common(1)[0][0])} for k, c in sorted(kinds.items())]
write('catalogue.json', json.dumps({'types': types, 'ids': sorted(byid), 'repo_ids': sorted(repo_ids)}))

# photos: copy only what changed, never delete the folder (the web user may own some files)
dst = os.path.join(OUT, 'crops'); os.makedirs(dst, exist_ok=True); shareable(dst)
for base in (os.path.join(REPO, 'crops'), os.path.join(EXTRA, 'crops') if EXTRA else None):
    if not base or not os.path.isdir(base): continue
    for fn in os.listdir(base):
        a, b = os.path.join(base, fn), os.path.join(dst, fn)
        if not os.path.exists(b) or os.path.getsize(a) != os.path.getsize(b) or os.path.getmtime(a) > os.path.getmtime(b):
            shutil.copyfile(a, b); shareable(b)
print(f'{len(rows)} items ({len(added_ids)} added on site), {nflag} flagged, {len(manuals)} manual links -> {OUT}')
