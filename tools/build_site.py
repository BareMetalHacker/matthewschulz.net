#!/usr/bin/env python3
"""build_site.py — builds the static site for matthewschulz.net from Zenodo API records.
Inputs (in DATA dir): zen/name_p*.json (latest versions), versions.json (first-published dates),
version_to_concept.json, main_pdfs.json, pdfs/<recid>.pdf.  Output: SITE dir."""
import json, glob, csv, re, os, sys, shutil, html, hashlib, datetime as dt
from html.parser import HTMLParser

DATA, SITE = sys.argv[1], sys.argv[2]
BASE = "https://matthewschulz.net"
ORCID = "0009-0000-0956-5743"
AUTHOR_DISPLAY = 'Matthew “Bear” Schulz'
AUTHOR_META = "Schulz, Matthew"
BUILD_DATE = sys.argv[3] if len(sys.argv) > 3 else dt.date.today().isoformat()

recs = {}
for f in sorted(glob.glob(f"{DATA}/zen/name_p*.json")):
    for h in json.load(open(f))["hits"]["hits"]:
        recs[h["id"]] = h
rows = list(csv.DictReader(open(f"{DATA}/records_68.csv")))
vers = {o["n"]: o for o in json.load(open(f"{DATA}/versions.json"))}
v2c = json.load(open(f"{DATA}/version_to_concept.json"))
mainpdf = {r[0]: r for r in json.load(open(f"{DATA}/main_pdfs.json"))}

# Records are singled out by concept DOI (zenodo record number), never by position in the list.
ERRATUM_C, ERRATUM_TARGET_C = "21845073", "21449569"   # erratum folds onto the Integer Forest page
BUNDLE_C = {"20502057", "20550751"}                    # records with no single paper PDF
OFF_C = {"19846409", "19860845", "19846663", "19846969", "19847170", "19847428", "19848346", "19848691", "19862821", "19860356", "19860724", "19861371", "20174565", "19860623", "19872703", "19925891", "19926336", "19874109", "19874868", "19873060", "19872860", "19904202", "20353275", "20353230", "20353205", "20353001", "20352098", "19904307", "19903526", "19880364", "19928925"}  # 31 records the author keeps off the site
_n_of = {r["concept"].split(".")[-1]: i for i, r in enumerate(rows, 1)}
assert len(OFF_C) == 31 and all(c in _n_of for c in OFF_C | BUNDLE_C | {ERRATUM_C, ERRATUM_TARGET_C})
ERRATUM_N, ERRATUM_TARGET_N = _n_of[ERRATUM_C], _n_of[ERRATUM_TARGET_C]
BUNDLE_N = {_n_of[c] for c in BUNDLE_C}
OFF = {_n_of[c] for c in OFF_C}


# ---------- abstract sanitiser: keep p, br, em, strong, h2->h3, sub, sup, a(href) ----------
class San(HTMLParser):
    OK = {"p", "br", "em", "strong", "i", "b", "sub", "sup", "ul", "ol", "li"}
    def __init__(self):
        super().__init__(convert_charrefs=True); self.out = []
    def handle_starttag(self, t, a):
        if t in self.OK: self.out.append("<br>" if t == "br" else f"<{t}>")
        elif t == "h2": self.out.append("<p><strong>")
        elif t == "a":
            href = dict(a).get("href", "")
            self.out.append(f'<a href="{html.escape(href)}">' if href.startswith("http") else "<a>")
    def handle_endtag(self, t):
        if t in self.OK and t != "br": self.out.append(f"</{t}>")
        elif t == "h2": self.out.append("</strong></p>")
        elif t == "a": self.out.append("</a>")
    def handle_data(self, d): self.out.append(html.escape(d, quote=False))
def sanitise(s):
    p = San(); p.feed(s); p.close()
    t = "".join(p.out).strip()
    t = re.sub(r"(<br>\s*){2,}", "</p><p>", t)
    t = re.sub(r"<p>\s*</p>", "", t)
    return t
def plain(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

def slugify(title):
    t = re.split(r"\s[-—–:]\s|:\s", title)[0]
    t = t.replace("’", "").replace("'", "")
    t = re.sub(r"[^A-Za-z0-9]+", "-", t.lower()).strip("-")
    words = [w for w in t.split("-") if w]
    return "-".join(words[:7])

def nice_date(s):
    d = dt.date.fromisoformat(s); return f"{d.day} {d.strftime('%B')} {d.year}"
def meta_date(s):
    d = dt.date.fromisoformat(s); return f"{d.year}/{d.month}/{d.day}"
def mb(n): return f"{n/1e6:.2f} MB"

# ---------- assemble paper list ----------
papers = []
for n, r in enumerate(rows, 1):
    if n in OFF or n == ERRATUM_N: continue
    h = recs[int(r["id"])]; m = h["metadata"]
    papers.append(dict(n=n, recid=r["id"], concept=h["conceptdoi"], title=m["title"].strip(),
        first=vers[n]["first_pubdate"], latest=m["publication_date"], nver=vers[n]["nver"],
        abstract=sanitise(m.get("description", "")), abstract_plain=plain(m.get("description", "")),
        keywords=m.get("keywords", []), related=m.get("related_identifiers", []),
        zenodo_url=f"https://doi.org/{h['conceptdoi']}", bundle=n in BUNDLE_N,
        files=h["files"]))
# Permanent URLs: GitHub Pages cannot send 301 redirects, so these names are fixed once indexed.
SLUG_BY_CONCEPT = {"20502057": "comparative-biosonar", "20587337": "topological-winding-memory",
    "21331651": "reading-the-sky-through-loops", "21351574": "linking-number-heredity", "21367632": "bifrost-memory-bridge",
    "21448986": "walking-the-loop", "21815319": "nucleic-acid-backbones", "21845002": "twelve-answers-problem",
    "21857701": "memory-by-subtraction", "21449569": "integer-forest-loop-walk", "22105828": "two-checks-moving-environment",
    "22652934": "auditory-pathway-data-channel", "21811588": "loop-walking-field-guide", "22908909": "jellyfish-holonomist-of-the-sea"}
SLUG_OVERRIDE = {_n_of[c]: s for c, s in SLUG_BY_CONCEPT.items()}
slugs = {}
for p in papers:
    s = SLUG_OVERRIDE.get(p["n"]) or re.sub(r"^(the|a)-", "", slugify(p["title"]))
    assert s not in slugs.values(), s
    slugs[p["n"]] = s; p["slug"] = s
by_concept = {p["concept"]: p for p in papers}
err_rec = recs[int(rows[ERRATUM_N - 1]["id"])]
mainpdf_err = next(r[0] for r in mainpdf.values() if r[0] == rows[ERRATUM_N - 1]["id"] or r[0] == str(err_rec["id"]))
erratum = dict(concept=err_rec["conceptdoi"], title=err_rec["metadata"]["title"],
               first=vers[ERRATUM_N]["first_pubdate"], abstract=sanitise(err_rec["metadata"]["description"]),
               files=err_rec["files"])

CSS = """:root{--ink:#1d1d1b;--soft:#5b5b57;--line:#d9d6cf;--bg:#fbfaf7;--accent:#2a5d8f;--note:#f3efe4}
@media (prefers-color-scheme:dark){:root{--ink:#e9e6df;--soft:#a9a59c;--line:#3a3934;--bg:#181816;--accent:#8db8e3;--note:#24231f}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 Georgia,"Times New Roman",serif}
.wrap{max-width:46rem;margin:0 auto;padding:1.25rem 1rem 3rem}
header.site{border-bottom:1px solid var(--line);margin-bottom:1.5rem;padding-bottom:.6rem;display:flex;flex-wrap:wrap;gap:.3rem 1.2rem;align-items:baseline}
header.site .name{font-weight:bold;color:var(--ink);text-decoration:none;font-size:1.05rem}
header.site nav a{margin-right:1rem}
a{color:var(--accent)}h1{font-size:1.6rem;line-height:1.25;margin:.2rem 0 .6rem}
h2{font-size:1.15rem;margin:1.8rem 0 .5rem}
.byline{font-size:1.05rem;margin:0 0 .3rem}.meta{color:var(--soft);font-size:.92rem;margin:.15rem 0}
.status{display:inline-block;font:600 .78rem/1.4 system-ui,sans-serif;letter-spacing:.02em;border:1px solid var(--line);border-radius:3px;padding:.05rem .45rem;color:var(--soft)}
.actions{margin:1rem 0;display:flex;flex-wrap:wrap;gap:.6rem}
.actions a{font:600 .92rem/1 system-ui,sans-serif;text-decoration:none;border:1px solid var(--accent);border-radius:4px;padding:.55rem .8rem}
.actions a.primary{background:var(--accent);color:var(--bg)}
.box{background:var(--note);border-left:3px solid var(--accent);padding:.6rem .9rem;margin:1.2rem 0;font-size:.95rem}
.abstract p{margin:.6rem 0}
ul.list{list-style:none;padding:0;margin:0}ul.list li{padding:.7rem 0;border-bottom:1px solid var(--line)}
ul.list .d{display:block;color:var(--soft);font-size:.85rem;font-family:system-ui,sans-serif}
.cite{font-size:.9rem;color:var(--soft);word-break:break-word}
footer{border-top:1px solid var(--line);margin-top:2.5rem;padding-top:.8rem;color:var(--soft);font-size:.85rem}
"""

def head(title, desc, canonical, extra="", root=""):
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc[:300])}">
<link rel="canonical" href="{canonical}">
<link rel="stylesheet" href="{root}style.css">
{extra}</head><body><div class="wrap">
<header class="site"><a class="name" href="{root or './'}">{AUTHOR_DISPLAY}</a>
<nav><a href="{root}papers/">Papers</a><a href="https://orcid.org/{ORCID}">ORCID</a></nav></header>
"""
FOOT = f"""<footer>Preprints from an independent, part-time research team, free to the world under CC BY 4.0.
None of this work has been peer reviewed, and each paper's literature search is limited; each paper says so and lists its own limits.
Corrections are shown on the page of the paper they correct.</footer>
</div></body></html>
"""

def related_links(p):
    seen, out = set(), []
    for x in p["related"]:
        if x.get("scheme") != "doi": continue
        ident = x["identifier"].lower()
        if not ident.startswith("10.5281/zenodo"): continue
        c = v2c.get(ident, ident)
        if c == p["concept"] or c in seen: continue
        seen.add(c)
        if c in by_concept:
            q = by_concept[c]; out.append(f'<li><a href="../{q["slug"]}/">{html.escape(q["title"])}</a><span class="d">{nice_date(q["first"])}</span></li>')
        elif c == erratum["concept"]:
            continue
        else:
            out.append(f'<li><a href="https://doi.org/{c}">doi.org/{c}</a><span class="d">another record by the author on Zenodo</span></li>')
    return out

os.makedirs(SITE, exist_ok=True)
open(f"{SITE}/style.css", "w").write(CSS)
manifest = []
for p in papers:
    d = f"{SITE}/papers/{p['slug']}"; os.makedirs(d, exist_ok=True)
    url = f"{BASE}/papers/{p['slug']}/"
    pdf_name = f"{p['slug']}.pdf"
    tags = [f'<meta name="citation_title" content="{html.escape(p["title"])}">',
            f'<meta name="citation_author" content="{AUTHOR_META}">',
            f'<meta name="citation_publication_date" content="{meta_date(p["first"])}">',
            f'<meta name="citation_online_date" content="{meta_date(p["latest"])}">',
            f'<meta name="citation_doi" content="{p["concept"]}">',
            f'<meta name="citation_abstract_html_url" content="{url}">',
            '<meta name="citation_language" content="en">',
            '<meta name="DC.rights" content="https://creativecommons.org/licenses/by/4.0/">']
    for k in p["keywords"][:12]:
        tags.append(f'<meta name="citation_keywords" content="{html.escape(k)}">')
    pdf_html = ""
    if not p["bundle"]:
        rid, key, link, size = mainpdf[p["recid"]]
        src = f"{DATA}/pdfs/{rid}.pdf"
        shutil.copyfile(src, f"{d}/{pdf_name}")
        tags.append(f'<meta name="citation_pdf_url" content="{url}{pdf_name}">')
        pdf_html = f'<a class="primary" href="{pdf_name}">Read the paper (PDF, {mb(size)})</a>'
        zchk = next(x["checksum"] for x in p["files"] if x["key"] == key)
        manifest.append((p["slug"], pdf_name, size, zchk))
    else:
        npdf = sum(1 for x in p["files"] if x["key"].lower().endswith(".pdf"))
        pdf_html = ""
    box = ""
    if p["n"] == ERRATUM_TARGET_N:
        ekey = next(x for x in erratum["files"] if x["key"].lower().endswith(".pdf"))
        shutil.copyfile(f"{DATA}/pdfs/{mainpdf_err}.pdf", f"{d}/erratum.pdf")
        manifest.append((p["slug"], "erratum.pdf", ekey["size"], ekey["checksum"]))
        box = (f'<div class="box"><strong>Correction.</strong> The first edition of this paper was corrected by an erratum published on {nice_date(erratum["first"])}, shown below; '
               f'the erratum states that the version of {nice_date(p["latest"])} carries the same corrections. <a href="erratum.pdf">Erratum (PDF)</a> · '
               f'<a href="https://doi.org/{erratum["concept"]}">doi.org/{erratum["concept"]}</a>'
               f'<div class="abstract">{erratum["abstract"]}</div></div>')
    if p["bundle"]:
        box += ('<div class="box">This record is a set of linked documents rather than a single paper. '
                f'Its files are on <a href="{p["zenodo_url"]}">Zenodo</a>.</div>')
    rel = related_links(p)
    rel_html = f'<h2>Related papers</h2><ul class="list">{"".join(rel)}</ul>' if rel else ""
    dates = f"First published {nice_date(p['first'])}"
    if p["latest"] != p["first"] and p["nver"] > 1:
        dates += f" · this version {nice_date(p['latest'])}"
    year = p["first"][:4]
    actions = f'<div class="actions">{pdf_html}<a href="{p["zenodo_url"]}">Record on Zenodo</a></div>'
    page = head(f"{p['title']} — {AUTHOR_DISPLAY}", p["abstract_plain"], url, "\n".join(tags) + "\n", root="../../") + f"""<main>
<h1>{html.escape(p['title'])}</h1>
<p class="byline">{AUTHOR_DISPLAY} · <a href="https://orcid.org/{ORCID}">ORCID {ORCID}</a></p>
<p class="meta">{dates}</p>
<p class="meta">DOI <a href="https://doi.org/{p['concept']}">{p['concept']}</a> · licence <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a></p>
<p><span class="status">Preprint · not peer reviewed</span></p>
{actions}
{box}
<h2>Abstract</h2>
<div class="abstract">{p['abstract']}</div>
<h2>How to cite</h2>
<p class="cite">Schulz, M. ({year}). {html.escape(p['title'])}. Preprint, Zenodo. https://doi.org/{p['concept']}</p>
{rel_html}
</main>
""" + FOOT
    open(f"{d}/index.html", "w").write(page)

# ---------- papers list (newest first by first-published date) ----------
papers_sorted = sorted(papers, key=lambda p: (p["first"], p["n"]), reverse=True)
items = "".join(f'<li><a href="{p["slug"]}/">{html.escape(p["title"])}</a>'
                f'<span class="d">{nice_date(p["first"])} · doi.org/{p["concept"]}</span></li>' for p in papers_sorted)
os.makedirs(f"{SITE}/papers", exist_ok=True)
open(f"{SITE}/papers/index.html", "w").write(head(f"Papers — {AUTHOR_DISPLAY}", f"All preprints by {AUTHOR_DISPLAY}, newest first.", f"{BASE}/papers/", root="../") +
    f"""<main><h1>Papers</h1>
<p>All {len(papers)} preprints, newest first by the date each first appeared. Every paper is open access under CC BY 4.0 and has a permanent DOI on Zenodo.</p>
<ul class="list">{items}</ul></main>
""" + FOOT)

# ---------- home ----------
latest5 = "".join(f'<li><a href="papers/{p["slug"]}/">{html.escape(p["title"])}</a><span class="d">{nice_date(p["first"])}</span></li>' for p in papers_sorted[:5])
ABOUT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "about.html")).read()
open(f"{SITE}/index.html", "w").write(head(AUTHOR_DISPLAY + " — research", "Preprints on coordinate-free holonomy instruments and their uses across many fields, by an independent researcher.", f"{BASE}/") +
    f"""<main><h1>{AUTHOR_DISPLAY}</h1>
{ABOUT}
<div class="actions"><a class="primary" href="papers/">All {len(papers)} papers</a><a href="https://orcid.org/{ORCID}">ORCID {ORCID}</a></div>
<h2>Most recent</h2><ul class="list">{latest5}</ul></main>
""" + FOOT)

# ---------- robots, sitemap, CNAME, 404, .nojekyll ----------
open(f"{SITE}/robots.txt", "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
urls = [f"{BASE}/", f"{BASE}/papers/"] + [f"{BASE}/papers/{p['slug']}/" for p in papers_sorted]
open(f"{SITE}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    "".join(f"  <url><loc>{u}</loc><lastmod>{BUILD_DATE}</lastmod></url>\n" for u in urls) + "</urlset>\n")
if len(sys.argv) > 4 and sys.argv[4] == "cname":
    open(f"{SITE}/CNAME", "w").write("matthewschulz.net\n")
open(f"{SITE}/.nojekyll", "w").write("")
open(f"{SITE}/404.html", "w").write(head("Page not found", "Page not found", f"{BASE}/404.html", root=BASE + "/") +
    f'<main><h1>Page not found</h1><p>The papers are listed on <a href="{BASE}/papers/">the papers page</a>.</p></main>\n' + FOOT)
json.dump([dict(slug=p["slug"], n=p["n"], concept=p["concept"], title=p["title"], first=p["first"], bundle=p["bundle"]) for p in papers_sorted],
          open(f"{SITE}/../site_index.json", "w"), indent=1)
json.dump(manifest, open(f"{SITE}/../pdf_manifest.json", "w"), indent=1)
print("papers", len(papers), "pdfs", len(manifest))
