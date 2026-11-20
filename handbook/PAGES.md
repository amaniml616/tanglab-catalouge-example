# Publishing the catalogue on GitHub Pages

This puts the searchable, photo catalogue on the web with no server. It rebuilds on every push to the inventory.

**The site is public.** Anyone with the link can open it, including every item, photo and note. Check with the PI that the inventory (lasers, chemicals, safety notes) may be public. Do not put anything in `optics_catalog.csv` or `crops/` that should stay private.

## Steps
1. Your GitHub plan decides whether this works for a private repo:
   - Free: Pages works only for public repositories, which would make the whole repo (CSV, photos, history) public.
   - Pro, Team or Enterprise: Pages works for a private repo; the site is public but the source stays private.
2. Copy `handbook/` and `.github/workflows/pages.yml` into the repo and push.
3. On GitHub: repo Settings > Pages > Source = **GitHub Actions**.
4. Open the Actions tab, run "Publish catalogue to GitHub Pages", and wait for green. The address is shown under Settings > Pages (https://ACCOUNT.github.io/catalog/).
5. Day to day: edit `optics_catalog.csv` / `crops/`, push, and the site updates in a minute or two. Manual links go in `handbook/manuals.csv`.

To change the sidebar of the public page, edit `handbook/handbook.pages.json` (for example, add a link to the lab's Confluence space: `{"id": "@wiki", "title": "Lab wiki", "url": "https://..."}`).

Test on your laptop: `python3 handbook/build_catalogue.py --out _site --config handbook/handbook.pages.json`, then open `_site/index.html`.

## Adding items from the website

The public page has an **Add an item** tab: take a photo, optionally let AI fill in the form, check it, and save. It commits the new row to `optics_catalog.csv` and the photo to `crops/<ID>.jpg`, and the site rebuilds by itself.

Each person sets this up once per browser (the tab has a "Keys and repository" box):
- **GitHub token** (needed to save): github.com/settings/personal-access-tokens/new, restricted to this repository, with *Contents: Read and write*. The person needs write access to the repo.
- **Anthropic API key** (optional, for the AI fill-in): console.anthropic.com/settings/keys. Usage is billed to the key's owner.

Keys are stored only in that browser and sent only to api.github.com and api.anthropic.com. The AI only sees the photo, so everything it fills in is marked as unconfirmed and the item gets a "needs check" flag until someone verifies it.
