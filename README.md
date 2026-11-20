# Tang Lab — Equipment Catalogue

A photographed inventory of the lab's optics, instruments, chemicals, wafers and tools.
**522 entries**, each with a photo, an identification, specifications, and notes on what
it does and what will go wrong if you use it carelessly.

---

## How to use it

**Just looking something up?** Open `index.html` in a browser after cloning. Search by ID,
name, manufacturer, part number, wavelength, or anything in the notes. It works on a
phone.

**Adding or correcting an item?** Read on.

---

## Editing — with your AI assistant

The intended workflow is that you clone the repo and let your own AI assistant (Claude
Code, or whatever you use) do the work. The repo contains a `CLAUDE.md` that tells the
assistant the schema, the conventions, and the checks to run — so you can hand it a
photo and a sentence, and it will do the identification, the research, the crop, and the
CSV edit correctly.

```bash
git clone https://github.com/haoningtang/catalog.git
cd catalog
```

Then, in your assistant:

> "Here's a photo of a new objective on the SHG bench. Add it to the catalogue."

or

> "OBJ-019 and OBJ-005 are flagged as possible duplicates. I checked — the engraving is
> `DIN 10 0.25` on both. Merge them."

or

> "Measure list: I measured LEN-124, it's fused silica, f = 50 mm. Update it and clear
> the flag."

When it's done:

```bash
git add -A
git commit -m "Add Olympus UMPlanFl 50x/0.80 (OBJ-021) to the SHG bench"
git push
```

**Everyone works from their own GitHub account, so git tracks who changed what and when.**
`git log`, `git blame optics_catalog.csv`, and the GitHub history view all work normally —
that is the whole point of keeping this in version control rather than in a shared
spreadsheet.

### If you'd rather edit by hand

Open `optics_catalog.csv` in Excel, Numbers, or Google Sheets. **Save as CSV with UTF-8
encoding** — otherwise `°`, `µ` and `Ø` get mangled. Or use GitHub's web editor: click
the pencil icon on the file.

---

## The one rule

**`optics_catalog.csv` is the single source of truth.**

`index.html` and `optics_catalog_for_import.csv` are **generated**. Never hand-edit them —
a GitHub Action rebuilds both on every push and will overwrite your changes.

To rebuild locally:

```bash
python3 build.py            # -> index.html  (loads photos from crops/)
python3 build.py --embed    # -> catalog_standalone.html, one 28 MB self-contained file
```

No dependencies beyond the Python standard library.

> **`index.html` needs the `crops/` folder beside it.** If you copy the HTML somewhere on
> its own, the photos will be missing — use the `--embed` build for that instead.

---

## Photos

`crops/<ID>.jpg` — the filename must equal the item's ID exactly (`crops/OBJ-021.jpg`).
That is the only linkage; there is no path stored in the CSV.

Keep them small: long edge ~460 px, quality ~88, well under 200 KB. Git keeps every
version of every file forever, so a 4 MB phone photo is a permanent cost.

---

## Columns

| Column | Contents |
|---|---|
| `ID` | `PREFIX-NNN`. **Never reuse or renumber** — people cite these. |
| `Category` | Decides which section the item appears in |
| `Item Name` | What it is, in plain words |
| `Manufacturer` | Maker, or `Unmarked` |
| `Part Number` | Catalogue number, serial, engraving — transcribed exactly |
| `Wavelength Range` | Optical band, or `n/a` |
| `Aperture / Size` | Dimensions, thread, mount |
| `Focal Length / Key Spec` | The number that matters most |
| `Notes (Function & Operating Range)` | What it does, how to use it, what to watch for |
| `Qty` | How many |
| `Loss` | **Left empty on purpose** — for the lab to fill in |
| `Setup` | Which bench it belongs to |
| `Photo Ref` | Internal note; not shown on the site |

---

## Two conventions worth keeping

The catalogue is written to be trustworthy, which means being explicit about what is
*not* known:

- **`NOT CONFIRMED`** marks anything inferred rather than read off the part or a
  manufacturer datasheet.
- **`FLAG:`** marks something that still needs checking or measuring.

Both feed the **Needs check** filter on the site, so open questions stay visible instead
of quietly becoming folklore. There are currently a lot of them — unmeasured focal
lengths, unread model numbers, suspected duplicates. Clearing them is the highest-value
tidying work left.

---

## Publishing the site (optional)

**Settings → Pages → Source: Deploy from a branch → `main` / `/ (root)`**

Note that **GitHub Pages requires a public repository on a free account.** If this repo
stays private, Pages will 404 — clone the repo and open `index.html` locally instead,
which works fine and keeps the inventory private.
