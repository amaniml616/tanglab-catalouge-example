#!/usr/bin/env python3
"""
Build the lab equipment catalogue website from optics_catalog.csv.

  python3 build.py            -> index.html, images referenced from crops/
  python3 build.py --embed    -> catalog_standalone.html, images base64-embedded
                                 (one big file you can email; no folder needed)

Also regenerates optics_catalog_for_import.csv (the Google-Sheets import copy,
which is the same data minus the Photo Ref column).
"""
import csv, html, base64, os, sys, json, datetime

HERE   = os.path.dirname(os.path.abspath(__file__))
CSV    = os.path.join(HERE, "optics_catalog.csv")
CROPS  = os.path.join(HERE, "crops")
EMBED  = "--embed" in sys.argv
OUT    = os.path.join(HERE, "catalog_standalone.html" if EMBED else "index.html")

SHEET  = "https://docs.google.com/spreadsheets/d/1d92698n1JM8UJEF29RsjkiPd1mzv89443yTh9XvHD_I/edit"

# ---------------------------------------------------------------- taxonomy
GROUPS = [
    ("Objectives",           "Objective"),
    ("Eyepieces",            "Eyepiece"),
    ("Mirrors",              "Mirror"),
    ("Prisms",               "Prism"),
    ("Beamsplitters & Dichroics","Beamsplitter"),
    ("Nonlinear Crystals",   "Nonlinear"),
    ("Lasers",               "Laser"),
    ("Laser Safety Eyewear", "Safety"),
    ("Light Sources",        "Light Source"),
    ("Meters & Instruments", "Meter"),
    ("Detectors & Receivers","Detector"),
    ("Polarizers",           "Polarizer"),
    ("Waveplates",           "Waveplate"),
    ("Lenses",               "Lens"),
    ("Stages & Actuators",   "Actuator"),
    ("Cameras",              "Camera"),
    ("Filters",              "Filter"),
    ("Instruments & Tools",  "Instrument"),
    ("Gratings & Apertures", "Grating"),
    ("Major Instruments",    "Major Instrument"),
    ("Chemicals",            "Chemical"),
    ("Wafers & Substrates",  "Wafer"),
    ("Fab Tools & Handling", "Fab Tool"),
    ("Cleanroom Supplies",   "Cleanroom"),
    ("Electronics",          "Electronics"),
    ("Tools",                "Tool - Workshop"),
    ("Unidentified",         "Misc"),
]

SUPER = [
    ("Optics Components", ["Objectives","Eyepieces","Mirrors","Prisms","Nonlinear Crystals",
                           "Lasers","Laser Safety Eyewear","Light Sources","Polarizers","Waveplates",
                           "Lenses","Filters","Beamsplitters & Dichroics","Gratings & Apertures","Detectors & Receivers",
                           "Cameras","Stages & Actuators","Meters & Instruments",
                           "Instruments & Tools","Unidentified"]),
    ("Major Instruments",  ["Major Instruments"]),
    ("Electronics",        ["Electronics"]),
    ("Tools",              ["Tools"]),
    ("Chemicals",          ["Chemicals"]),
    ("Wafers",             ["Wafers & Substrates"]),
    ("Fab Tools",          ["Fab Tools & Handling"]),
    ("Cleanroom Supplies", ["Cleanroom Supplies"]),
]
SUPER_OF = {g: s for s, gs in SUPER for g in gs}

def group_of(cat):
    if cat.startswith("Beamsplitter"):   return "Beamsplitters & Dichroics"
    if cat.startswith("Cleanroom"):      return "Cleanroom Supplies"
    if cat.startswith("Fab Tool"):       return "Fab Tools & Handling"
    if cat.startswith("Wafer"):          return "Wafers & Substrates"
    if cat.startswith("Chemical"):       return "Chemicals"
    if cat.startswith("Major"):          return "Major Instruments"
    if cat.startswith("Tool - Workshop"):return "Tools"
    if cat.startswith("Electronics"):    return "Electronics"
    if cat.startswith("Controller"):     return "Stages & Actuators"
    if cat.startswith("Tool") or cat.startswith("Accessory"): return "Instruments & Tools"
    if cat.startswith("Aperture"):       return "Gratings & Apertures"
    if cat.startswith("Stage"):          return "Stages & Actuators"
    for label, key in GROUPS:
        if cat.startswith(key): return label
    return "Unidentified"

FLAGWORDS = ("FLAG","TBD","MEASURE","UNOPENED","UNVERIFIED","NOT CONFIRMED","NOT MARKED","UNKNOWN")

# ---------------------------------------------------------------- load
rows = list(csv.DictReader(open(CSV, encoding="utf-8")))

# regenerate the Google-Sheets import copy (everything except Photo Ref)
with open(CSV, encoding="utf-8") as f:
    raw = list(csv.reader(f))
ip = raw[0].index("Photo Ref")
with open(os.path.join(HERE, "optics_catalog_for_import.csv"), "w",
          newline="", encoding="utf-8") as f:
    csv.writer(f).writerows([[c for j, c in enumerate(r) if j != ip] for r in raw])

def esc(s): return html.escape(str(s or ""))

def img_src(pid):
    p = os.path.join(CROPS, pid + ".jpg")
    if not os.path.exists(p): return ""
    if EMBED:
        return "data:image/jpeg;base64," + base64.b64encode(open(p, "rb").read()).decode()
    return "crops/" + pid + ".jpg"

cards = []
for r in rows:
    pid  = r["ID"]
    blob = " ".join(str(v or "") for v in r.values())
    cards.append({
        "id": pid, "grp": group_of(r["Category"]), "cat": r["Category"],
        "name": r["Item Name"], "mfr": r["Manufacturer"], "pn": r["Part Number"],
        "wl": r["Wavelength Range"], "ap": r["Aperture / Size"],
        "ks": r["Focal Length / Key Spec"],
        "notes": r["Notes (Function & Operating Range)"],
        "qty": r["Qty"] or "1", "setup": r.get("Setup", ""),
        "img": img_src(pid),
        "flag": any(w in blob for w in FLAGWORDS),
    })
for c in cards:
    c["sup"] = SUPER_OF.get(c["grp"], "Optics Components")

total_units = sum(int(c["qty"] or 1) for c in cards)
built = datetime.date.today().isoformat()

# ---------------------------------------------------------------- body
GROUP_ORDER = [g for g, _ in GROUPS]
body = []
for sup, glist in SUPER:
    sup_items = [c for c in cards if c["sup"] == sup]
    if not sup_items: continue
    sn = sum(int(c["qty"] or 1) for c in sup_items)
    body.append(f'<h1 class="sup" data-sup="{esc(sup)}">{esc(sup)}'
                f'<span class="sc">{len(sup_items)} entries &middot; {sn} units</span></h1>')
    for label in [g for g in GROUP_ORDER if g in glist]:
        items = [c for c in cards if c["grp"] == label]
        if not items: continue
        n = sum(int(c["qty"] or 1) for c in items)
        body.append(f'<h2 class="grp" data-grp="{esc(label)}" data-sup="{esc(sup)}">'
                    f'{esc(label)}<span class="gc">{len(items)} &middot; {n} units</span></h2>')
        for c in items:
            img = (f'<img src="{c["img"]}" alt="{esc(c["id"])}" loading="lazy" decoding="async" '
                   f'onclick="zoom(this.src,{json.dumps(c["id"]+" — "+c["name"])})">'
                   ) if c["img"] else '<div class="noimg">no photo</div>'
            flag = '<span class="fl">needs check</span>' if c["flag"] else ''
            qty  = f'<span class="qty">×{esc(c["qty"])}</span>' if c["qty"] not in ("1","") else ''
            setup= f'<span class="stp">{esc(c["setup"])}</span>' if c["setup"] else ''
            search = (c["id"]+" "+c["name"]+" "+c["mfr"]+" "+c["pn"]+" "+c["wl"]+" "+
                      c["ks"]+" "+c["cat"]+" "+c["notes"]).lower()
            body.append(f'''
<article class="card" data-grp="{esc(label)}" data-sup="{esc(sup)}" data-s="{esc(search)}">
  <div class="ph">{img}</div>
  <div class="info">
    <div class="hd"><span class="pid">{esc(c["id"])}</span>{qty}{flag}{setup}</div>
    <h3>{esc(c["name"])}</h3>
    <div class="mfr">{esc(c["mfr"])}</div>
    <div class="pn">{esc(c["pn"])}</div>
    <dl>
      <dt>Wavelength</dt><dd class="wl">{esc(c["wl"])}</dd>
      <dt>Size</dt><dd>{esc(c["ap"])}</dd>
      <dt>Key spec</dt><dd>{esc(c["ks"])}</dd>
    </dl>
    <div class="ntw"><p class="nt">{esc(c["notes"])}</p><button class="more" type="button">Show more</button></div>
    <div class="blanks"><span>Loss <i>—</i></span><span>Setup <i>—</i></span></div>
  </div>
</article>''')

chips = "\n".join(
    f'<button class="chip" data-sup="{esc(s)}">{esc(s)}</button>'
    for s, _ in SUPER if any(c["sup"] == s for c in cards))

# second-level chips: every subgroup, tagged with its parent so JS can show/hide
subchips = []
for sup, glist in SUPER:
    ordered = [g for g in GROUP_ORDER if g in glist]
    if len(ordered) < 2:      # no point offering sub-nav for a single-group super
        continue
    for g in ordered:
        k = sum(1 for c in cards if c["grp"] == g)
        if not k: continue
        subchips.append(f'<button class="chip sub" data-of="{esc(sup)}" data-grp="{esc(g)}">'
                        f'{esc(g)} <b>{k}</b></button>')
subchips = "\n".join(subchips)

HTML = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f7f7f5" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#161614" media="(prefers-color-scheme: dark)">
<title>Tang Lab — Equipment Catalogue</title>
<style>
:root{{--bg:#f7f7f5;--card:#fff;--ink:#1a1a18;--dim:#6b6b64;--line:#e3e3dd;--acc:#8a6a2f;--flag:#a8451f;--shadow:0 1px 2px #0000000d}}
@media(prefers-color-scheme:dark){{:root{{--bg:#161614;--card:#201f1c;--ink:#eceae4;--dim:#9d9a90;--line:#33312c;--acc:#d3a95c;--flag:#e07a52;--shadow:none}}}}
*{{box-sizing:border-box;-webkit-tap-highlight-color:transparent}}
html{{-webkit-text-size-adjust:100%}}
body{{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif;
  overflow-wrap:anywhere}}

header{{position:sticky;top:0;z-index:9;background:var(--bg);
  border-bottom:1px solid var(--line);padding:10px 16px 8px;
  padding-top:calc(10px + env(safe-area-inset-top))}}
.ttl{{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}}
h1.site{{margin:0;font-size:17px;letter-spacing:-.01em;font-weight:650}}
.sub{{color:var(--dim);font-size:12.5px}}
.sub a{{color:var(--acc)}}
#q{{width:100%;margin-top:8px;border:1px solid var(--line);background:var(--card);
  color:var(--ink);border-radius:10px;padding:11px 13px;font-size:16px;
  -webkit-appearance:none;appearance:none}}
#q:focus{{outline:2px solid var(--acc);outline-offset:-1px}}
.bar{{display:flex;gap:7px;margin-top:8px;overflow-x:auto;scrollbar-width:none;
  -webkit-overflow-scrolling:touch;padding-bottom:2px}}
.bar::-webkit-scrollbar{{display:none}}
.chip{{flex:0 0 auto;border:1px solid var(--line);background:var(--card);color:var(--ink);
  border-radius:99px;padding:7px 14px;font-size:13.5px;cursor:pointer;white-space:nowrap;
  font-family:inherit;min-height:34px}}
.chip.on{{background:var(--ink);color:var(--bg);border-color:var(--ink)}}
.bar.sub2{{display:none;margin-top:6px}}
.bar.sub2.on{{display:flex}}
.chip.sub{{font-size:12.5px;padding:6px 12px;min-height:31px}}
.chip.sub b{{font-weight:600;opacity:.55;margin-left:3px}}
.hits{{font-size:12.5px;color:var(--dim);margin-top:6px;min-height:1em}}

main{{padding:4px 16px 70px;max-width:1080px;margin:0 auto}}
.sup{{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink);
  margin:34px 0 4px;padding-bottom:8px;border-bottom:2px solid var(--acc);
  display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;font-weight:700}}
.sc{{font-weight:400;letter-spacing:0;text-transform:none;font-size:12px;color:var(--dim)}}
.grp{{font-size:11.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--dim);
  margin:24px 0 10px;display:flex;gap:9px;align-items:baseline;flex-wrap:wrap;font-weight:650}}
.gc{{font-weight:400;letter-spacing:0;text-transform:none;font-size:12px;opacity:.8}}

.card{{display:grid;grid-template-columns:150px 1fr;gap:16px;background:var(--card);
  border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:10px;
  box-shadow:var(--shadow)}}
.ph img{{width:100%;border-radius:8px;display:block;cursor:zoom-in;background:#0001}}
.noimg{{height:100px;display:grid;place-items:center;color:var(--dim);font-size:12px;
  border:1px dashed var(--line);border-radius:8px}}
.hd{{display:flex;gap:7px;align-items:center;margin-bottom:4px;flex-wrap:wrap}}
.pid{{font:650 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.05em;
  background:var(--ink);color:var(--bg);padding:5px 8px;border-radius:5px}}
.qty{{font-size:11.5px;font-weight:650;color:var(--acc);border:1px solid var(--acc);
  border-radius:99px;padding:2px 9px}}
.fl{{font-size:11.5px;color:var(--flag);border:1px solid var(--flag);border-radius:99px;padding:2px 9px}}
.stp{{font-size:11.5px;color:var(--dim);border:1px dashed var(--line);border-radius:99px;padding:2px 9px}}
h3{{margin:2px 0 4px;font-size:16.5px;font-weight:650;letter-spacing:-.01em;line-height:1.35}}
.mfr{{font-size:13.5px;color:var(--dim)}}
.pn{{font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--acc);margin:5px 0 10px}}
dl{{display:grid;grid-template-columns:auto 1fr;gap:4px 14px;margin:0 0 10px;font-size:13.5px}}
dt{{color:var(--dim);white-space:nowrap}}
dd{{margin:0}}
dd.wl{{font-weight:650}}

.ntw{{position:relative}}
.nt{{margin:0;font-size:14px;color:var(--ink);opacity:.92;
  display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden}}
.ntw.open .nt{{-webkit-line-clamp:unset;overflow:visible}}
.more{{margin-top:5px;border:0;background:none;color:var(--acc);font:inherit;font-size:13px;
  padding:4px 0;cursor:pointer;font-weight:600}}
.more.hide{{display:none}}

.blanks{{display:flex;gap:9px;margin-top:11px;padding-top:10px;border-top:1px dashed var(--line);
  font-size:12px;color:var(--dim);flex-wrap:wrap}}
.blanks span{{border:1px dashed var(--line);border-radius:6px;padding:3px 11px}}
.blanks i{{font-style:normal;opacity:.55;margin-left:6px}}

#lb{{position:fixed;inset:0;background:#000e;display:none;place-items:center;z-index:50;
  padding:20px;cursor:zoom-out}}
#lb.on{{display:grid}}
#lb img{{max-width:100%;max-height:80vh;border-radius:10px}}
#lb p{{color:#fff;text-align:center;font-size:13.5px;margin:14px 0 0;max-width:640px}}
.hide{{display:none!important}}
#top{{position:fixed;right:14px;bottom:calc(14px + env(safe-area-inset-bottom));z-index:8;
  border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:99px;
  width:44px;height:44px;font-size:17px;cursor:pointer;display:none;box-shadow:0 2px 8px #0002}}
#top.on{{display:block}}

@media(max-width:640px){{
  main{{padding:4px 12px 70px}}
  header{{padding:9px 12px 7px;padding-top:calc(9px + env(safe-area-inset-top))}}
  .card{{grid-template-columns:104px 1fr;gap:12px;padding:12px;border-radius:11px}}
  h3{{font-size:15.5px}}
  .nt{{-webkit-line-clamp:4;font-size:13.5px}}
  dl{{font-size:13px;gap:3px 10px}}
  .sup{{margin:26px 0 2px;font-size:12px}}
}}
@media(max-width:430px){{
  .card{{grid-template-columns:88px 1fr;gap:11px}}
  dl{{grid-template-columns:1fr;gap:1px 0}}
  dt{{font-size:11px;letter-spacing:.05em;text-transform:uppercase;margin-top:6px}}
  dd{{margin-bottom:2px}}
  h1.site{{font-size:15.5px}}
  .sub{{font-size:11.5px}}
  .ph img{{max-height:150px;object-fit:cover}}
}}
@media(max-width:330px){{
  .card{{grid-template-columns:1fr}}
  .ph img{{max-width:170px;max-height:none}}
}}
</style></head><body>
<header>
  <div class="ttl">
    <h1 class="site">Tang Lab — Equipment Catalogue</h1>
    <span class="sub">{len(cards)} entries · {total_units} units · built {built} · <a href="{SHEET}" target="_blank" rel="noopener">Sheet</a></span>
  </div>
  <input id="q" type="search" enterkeyhint="search" placeholder="Search ID, name, maker, part number, wavelength, notes…">
  <div class="bar">
    <button class="chip on" data-sup="all">All</button>
    {chips}
    <button class="chip" data-flag="1">Needs check</button>
  </div>
  <div class="bar sub2" id="sub2">
    <button class="chip sub suball on" data-grp="all">All</button>
    {subchips}
  </div>
  <div class="hits" id="hits"></div>
</header>
<main>{''.join(body)}</main>
<button id="top" title="Back to top">↑</button>
<div id="lb"><div><img id="lbi" alt=""><p id="lbc"></p></div></div>
<script>
var cards=[].slice.call(document.querySelectorAll('.card')),
    grps =[].slice.call(document.querySelectorAll('.grp')),
    sups =[].slice.call(document.querySelectorAll('.sup')),
    q=document.getElementById('q'), hits=document.getElementById('hits'),
    S=null, G=null, FLAGONLY=false, t=null,
    sub2=document.getElementById('sub2');

function apply(){{
  var s=q.value.trim().toLowerCase(), terms=s?s.split(/\\s+/):[], n=0;
  cards.forEach(function(c){{
    var hay=c.dataset.s, ok=true;
    if(S && c.dataset.sup!==S) ok=false;
    if(ok && G && c.dataset.grp!==G) ok=false;
    if(ok && FLAGONLY && !c.querySelector('.fl')) ok=false;
    if(ok) for(var i=0;i<terms.length;i++){{ if(hay.indexOf(terms[i])<0){{ok=false;break;}} }}
    c.classList.toggle('hide',!ok); if(ok) n++;
  }});
  grps.forEach(function(g){{
    g.classList.toggle('hide',!cards.some(function(c){{
      return c.dataset.grp===g.dataset.grp && !c.classList.contains('hide');}}));
  }});
  sups.forEach(function(h){{
    h.classList.toggle('hide',!cards.some(function(c){{
      return c.dataset.sup===h.dataset.sup && !c.classList.contains('hide');}}));
  }});
  hits.textContent=(s||S||G||FLAGONLY)? n+' of '+cards.length+' shown' : '';
}}
q.addEventListener('input',function(){{clearTimeout(t);t=setTimeout(apply,120);}});
function showSubs(){{
  var any=false;
  sub2.querySelectorAll('.chip.sub').forEach(function(x){{
    if(x.classList.contains('suball')) return;
    var m=(x.dataset.of===S); x.classList.toggle('hide',!m); if(m) any=true;
  }});
  sub2.classList.toggle('on',any);
  if(!any) G=null;
}}
document.querySelectorAll('.bar:not(.sub2) .chip').forEach(function(b){{
  b.onclick=function(){{
    document.querySelectorAll('.bar:not(.sub2) .chip').forEach(function(x){{x.classList.remove('on');}});
    b.classList.add('on');
    if(b.dataset.flag){{FLAGONLY=true;S=null;}}
    else{{FLAGONLY=false;S=(b.dataset.sup==='all')?null:b.dataset.sup;}}
    G=null;
    sub2.querySelectorAll('.chip.sub').forEach(function(x){{x.classList.remove('on');}});
    sub2.querySelector('.suball').classList.add('on');
    showSubs(); apply(); window.scrollTo({{top:0,behavior:'smooth'}});
  }};
}});
sub2.querySelectorAll('.chip.sub').forEach(function(b){{
  b.onclick=function(){{
    sub2.querySelectorAll('.chip.sub').forEach(function(x){{x.classList.remove('on');}});
    b.classList.add('on');
    G=(b.dataset.grp==='all')?null:b.dataset.grp;
    apply(); window.scrollTo({{top:0,behavior:'smooth'}});
  }};
}});
document.querySelectorAll('.ntw').forEach(function(w){{
  var p=w.querySelector('.nt'), b=w.querySelector('.more');
  if(p.scrollHeight<=p.clientHeight+2){{ b.classList.add('hide'); return; }}
  b.onclick=function(){{ w.classList.toggle('open');
    b.textContent=w.classList.contains('open')?'Show less':'Show more'; }};
}});
function zoom(s,c){{var i=document.getElementById('lbi');i.src=s;
  document.getElementById('lbc').textContent=c;document.getElementById('lb').classList.add('on');}}
document.getElementById('lb').onclick=function(){{this.classList.remove('on');}};
document.addEventListener('keydown',function(e){{
  if(e.key==='Escape')document.getElementById('lb').classList.remove('on');
  if(e.key==='/'&&document.activeElement!==q){{e.preventDefault();q.focus();}}
}});
var top=document.getElementById('top');
top.onclick=function(){{window.scrollTo({{top:0,behavior:'smooth'}});}};
addEventListener('scroll',function(){{top.classList.toggle('on',scrollY>800);}},{{passive:true}});
</script></body></html>'''

open(OUT, "w", encoding="utf-8").write(HTML)
print(f"wrote {os.path.basename(OUT)}: {len(HTML):,} bytes, {len(cards)} cards, {total_units} units")
