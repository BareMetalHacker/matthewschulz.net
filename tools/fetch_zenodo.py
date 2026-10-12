#!/usr/bin/env python3
"""fetch_zenodo.py — downloads the author's Zenodo records and PDFs into a data folder for build_site.py.

usage: python3 fetch_zenodo.py DATA_DIR

Writes DATA_DIR/zen/name_pN.json (latest version of every record), records_68.csv (one row per record,
sorted by publication date), versions.json (first-published date and version count per record),
version_to_concept.json (every version DOI mapped to its concept DOI), main_pdfs.json (the largest PDF
of each record) and pdfs/<record id>.pdf (checked against Zenodo's md5)."""
import csv, glob, hashlib, json, os, subprocess, sys, time, urllib.parse

ORCID = "0009-0000-0956-5743"
NAME_QUERY = 'creators.name:"Schulz, Matthew"'
NO_ORCID_RECORDS = {"10.5281/zenodo.19860845"}   # the author's records deposited without the ORCID link
API = "https://zenodo.org/api/records"
D = sys.argv[1]
os.makedirs(f"{D}/zen", exist_ok=True); os.makedirs(f"{D}/pdfs", exist_ok=True)

def get(url, out=None):
    for attempt in range(7):
        cmd = ["curl", "-sS", "-m", "120", "-L", "--fail"] + (["-o", out] if out else []) + [url]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode == 0:
            return None if out else json.loads(r.stdout)
        time.sleep(5 * (attempt + 1))
    raise SystemExit(f"failed: {url}\n{r.stderr.decode()[:300]}")

def search(q, all_versions=False, sort="newest"):
    hits, page = [], 1
    while True:
        url = f"{API}?q={urllib.parse.quote(q)}&size=25&page={page}&sort={sort}" + ("&all_versions=true" if all_versions else "")
        d = get(url); hits += d["hits"]["hits"]
        if len(hits) >= d["hits"]["total"] or not d["hits"]["hits"]: return hits, d
        page += 1

def mine(h):
    return any(c.get("orcid") == ORCID for c in h["metadata"]["creators"]) or h.get("conceptdoi") in NO_ORCID_RECORDS

# 1. latest version of every record
latest, _ = search(NAME_QUERY)
latest = [h for h in latest if mine(h)]
for f in glob.glob(f"{D}/zen/name_p*.json"): os.remove(f)
json.dump({"hits": {"total": len(latest), "hits": latest}}, open(f"{D}/zen/name_p1.json", "w"))

# 2. one row per record, oldest first
rows = []
for h in latest:
    m = h["metadata"]
    rows.append(dict(id=h["id"], concept=h["conceptdoi"], date=m.get("publication_date", ""), title=m["title"]))
rows.sort(key=lambda r: (r["date"], int(r["id"])))
with open(f"{D}/records_68.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

# 3. version history of each record
by_id = {h["id"]: h for h in latest}
vers = []
for n, r in enumerate(rows, 1):
    vs, d = search(f"conceptrecid:{by_id[r['id']]['conceptrecid']}", all_versions=True, sort="oldest")
    first = min(vs, key=lambda v: v["created"])
    vers.append(dict(n=n, id=str(r["id"]), concept=r["concept"], nver=d["hits"]["total"],
                     first_created=first["created"][:10], first_pubdate=first["metadata"].get("publication_date"),
                     latest_pubdate=r["date"], title=r["title"][:60]))
json.dump(vers, open(f"{D}/versions.json", "w"), indent=1)

# 4. every version DOI -> concept DOI
allv, _ = search(NAME_QUERY, all_versions=True, sort="oldest")
json.dump({h["doi"]: h["conceptdoi"] for h in allv if mine(h)}, open(f"{D}/version_to_concept.json", "w"), indent=0)

# 5. largest PDF of each record, downloaded and checked
main = []
for r in rows:
    pdfs = [x for x in by_id[r["id"]]["files"] if x["key"].lower().endswith(".pdf")]
    if not pdfs: continue
    x = max(pdfs, key=lambda x: x["size"])
    main.append((str(r["id"]), x["key"], x["links"]["self"], x["size"]))
    fn = f"{D}/pdfs/{r['id']}.pdf"
    if not (os.path.exists(fn) and os.path.getsize(fn) == x["size"]):
        get(x["links"]["self"], fn)
    if "md5:" + hashlib.md5(open(fn, "rb").read()).hexdigest() != x["checksum"]:
        raise SystemExit(f"checksum mismatch {fn}")
json.dump(main, open(f"{D}/main_pdfs.json", "w"), indent=0)
print(f"records {len(rows)} | versions {len(allv)} | pdfs {len(main)} (md5 checked) -> {D}")
