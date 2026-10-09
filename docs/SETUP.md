# One-time setup: website repo + GitHub Pages + 101domain

Two repositories:
- `chicco4life/msra`: the open research knowledge base (notes, library). Not a website.
- `chicco4life/msra-website`: this folder. Serves msralab.com and reads research from `msra`.

## 1. Create the website repository
`gh repo create chicco4life/msra-website --public` (or github.com/new → name **msra-website** → Public → no README).

## 2. Push this folder to it
```
cd ~/Desktop/MSRA/MSRA网站/msralab-site
git add -A && git commit -m "Website: separate from the knowledge base"
git remote set-url origin https://github.com/chicco4life/msra-website.git
git push -u origin main --force
```

## 3. Turn on GitHub Pages
```
gh api -X POST repos/chicco4life/msra-website/pages -f "source[branch]=main" -f "source[path]=/"
gh api -X PUT repos/chicco4life/msra-website/pages -f cname=msralab.com
```
Or Settings → Pages → Deploy from a branch → main, / (root) → custom domain msralab.com.

## 4. DNS at 101domain
- Edit the existing **A** record for msralab.com (currently 52.60.87.163) to `185.199.108.153`.
- Add three more **A** records for msralab.com: `185.199.109.153`, `185.199.110.153`, `185.199.111.153`.
- Add a **CNAME** for **www** → `chicco4life.github.io`.
- Leave MX and email TXT records alone (li@msralab.com).

## 5. HTTPS
After the domain resolves (up to the record's TTL, 6 hours at present), Settings → Pages → tick **Enforce HTTPS**.
