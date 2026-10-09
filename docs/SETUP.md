# One-time setup: GitHub Pages + 101domain

## 1. Create the repository
Done: https://github.com/chicco4life/msra (must be **Public** for free GitHub Pages).

## 2. Upload the site
On the repository page click **Add file → Upload files** (or **uploading an existing file** if it is empty).
Open the `msralab-site` folder on your Mac, select everything inside it (not the folder itself) and drag it in.
Use Chrome or Edge so the sub-folders upload with their structure. Click **Commit changes**.

Terminal alternative (needs `git` and the GitHub CLI `gh`):
```
cd ~/Desktop/MSRA/MSRA网站/msralab-site
git init -b main && git add . && git commit -m "MSRA website"
git remote add origin https://github.com/chicco4life/msra.git
git push -u origin main --force   # --force replaces the starter README GitHub may have created
```

## 3. Turn on GitHub Pages
Repository **Settings → Pages**:
- Source: **Deploy from a branch** → branch **main**, folder **/ (root)** → Save.
- Custom domain: **msralab.com** → Save. (Do this before changing DNS.)

## 4. Verify the domain (recommended, protects against takeover)
Your GitHub **profile Settings → Pages → Add a domain** → `msralab.com`.
GitHub shows a TXT record; add it at 101domain (step 5), then click **Verify**.

## 5. DNS at 101domain
In the DNS settings for msralab.com:
- Remove any existing **A / AAAA records for @** and any **www** record or URL forwarding that points to the old site.
- Add **A** records for **@**: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
- Add **AAAA** records for **@**: `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`
- Add **CNAME** for **www** → `chicco4life.github.io`
- **Do not touch MX or other TXT records** — they carry your email (li@msralab.com).

## 6. Switch on HTTPS
Changes can take up to 24 hours. When **Settings → Pages** shows the domain as working, tick **Enforce HTTPS**.
