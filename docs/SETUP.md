# One-time setup: website repo + GitHub Pages + 101domain

Two repositories:
- `chicco4life/MSRA-Open-Research`: the open research knowledge base. One folder per project. Not a website.
- `chicco4life/msra-website`: this folder. Serves msralab.com and reads research from MSRA-Open-Research.

## Turn on GitHub Pages
github.com/chicco4life/msra-website → **Settings → Pages**
- Source: **Deploy from a branch** → branch **main**, folder **/ (root)** → **Save**.
- Custom domain: **msralab.com** → **Save** (it may already be filled in from the CNAME file).

## DNS at 101domain
- Edit the existing **A** record for msralab.com (previously 52.60.87.163) to `185.199.108.153`.
- Add three more **A** records for msralab.com: `185.199.109.153`, `185.199.110.153`, `185.199.111.153`.
- Add a **CNAME** for **www** → `chicco4life.github.io`.
- Leave MX and email TXT records alone (li@msralab.com).

## HTTPS
Once msralab.com loads the new site (up to the old record's TTL, 6 hours), Settings → Pages → tick **Enforce HTTPS**.
