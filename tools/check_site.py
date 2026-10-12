#!/usr/bin/env python3
"""check_site.py — independent checks on the built site: links, Scholar tags, PDF checksums, size, scripts, markers, DOIs."""
import os, re, sys, json, hashlib, glob
from html.parser import HTMLParser
SITE, DATA = sys.argv[1], sys.argv[2]
BASE = "https://matthewschulz.net"
v2c = json.load(open(f"{DATA}/version_to_concept.json"))
concepts = set(v2c.values())
class P(HTMLParser):
    def __init__(s): super().__init__(); s.links=[]; s.meta={}; s.scripts=0; s.text=[]
    def handle_starttag(s,t,a):
        a=dict(a)
        if t=="a" and "href" in a: s.links.append(a["href"])
        if t=="link" and "href" in a: s.links.append(a["href"])
        if t=="meta" and "name" in a: s.meta.setdefault(a["name"],[]).append(a.get("content",""))
        if t=="script": s.scripts+=1
    def handle_data(s,d): s.text.append(d)
problems=[]; ext=set(); pages=glob.glob(f"{SITE}/**/*.html",recursive=True)
def resolve(page, href):
    href=href.split("#")[0]
    if href.startswith("/"): path=SITE+href
    else: path=os.path.join(os.path.dirname(page),href)
    if path.endswith("/"): path+="index.html"
    return os.path.normpath(path)
marker=re.compile(r"(TODO|TBD|FIXME|\bDRAFT\b|REVIEW COPY|SCAFFOLD|\[stated\]|handover|working note|\bcrate\b|gmail|let me|I will now|as requested)",re.I)
ntag=0; links_total=0; marker_hits=[]
for pg in sorted(pages):
    p=P(); p.feed(open(pg,encoding="utf-8").read())
    if p.scripts: problems.append(f"script tag in {pg}")
    for h in p.links:
        links_total+=1
        if h.startswith("http"):
            ext.add(h)
            m=re.search(r"doi\.org/(10\.5281/zenodo\.\d+)",h)
            if m and m.group(1) not in concepts: problems.append(f"non-concept DOI {m.group(1)} in {pg}")
        elif h.startswith("mailto:"): problems.append(f"mailto in {pg}")
        else:
            if not os.path.exists(resolve(pg,h)): problems.append(f"broken link {h} in {pg}")
    txt=" ".join(p.text)
    for m in re.finditer(r"zenodo\.(\d{6,})",txt):
        d=f"10.5281/zenodo.{m.group(1)}"
        if d in v2c and d not in concepts: problems.append(f"version DOI in text {d} {pg}")
    for m in marker.finditer(txt):
        marker_hits.append((os.path.relpath(pg,SITE), m.group(0), txt[max(0,m.start()-60):m.end()+60].replace("\n"," ")))
    if "/papers/" in pg and not pg.endswith("papers/index.html"):
        ntag+=1
        for req in ["citation_title","citation_author","citation_publication_date"]:
            if req not in p.meta: problems.append(f"missing {req} in {pg}")
        if not re.fullmatch(r"\d{4}/\d{1,2}/\d{1,2}",p.meta.get("citation_publication_date",[""])[0]): problems.append(f"bad date {pg}")
        pdfu=p.meta.get("citation_pdf_url")
        if pdfu:
            u=pdfu[0]; page_url=BASE+"/"+os.path.relpath(os.path.dirname(pg),SITE)+"/"
            if not u.startswith(page_url) or "/" in u[len(page_url):]: problems.append(f"pdf_url not in same dir {pg}")
            f=os.path.join(os.path.dirname(pg),u[len(page_url):])
            if not os.path.exists(f): problems.append(f"pdf missing {f}")
# PDFs vs Zenodo md5
man=json.load(open(sys.argv[3] if len(sys.argv)>3 else f"{SITE}/../pdf_manifest.json")); md5_ok=0; big=[]
for slug,name,size,chk in man:
    f=f"{SITE}/papers/{slug}/{name}"
    h=hashlib.md5(open(f,"rb").read()).hexdigest()
    if "md5:"+h==chk and os.path.getsize(f)==size: md5_ok+=1
    else: problems.append(f"checksum mismatch {f}")
    if size>5_000_000: big.append((slug,name,size))
# reachability: home -> papers -> each paper
home=P(); home.feed(open(f"{SITE}/index.html").read())
lst=P(); lst.feed(open(f"{SITE}/papers/index.html").read())
paper_pages={os.path.normpath(x) for x in pages if "/papers/" in x and not x.endswith("papers/index.html")}
home_to_list=os.path.normpath(f"{SITE}/papers/index.html") in {resolve(f"{SITE}/index.html",h) for h in home.links if not h.startswith("http")}
listed={resolve(f"{SITE}/papers/index.html",h) for h in lst.links if not h.startswith("http")}
print("html pages",len(pages),"| paper pages",ntag,"| links checked",links_total,"| external links",len(ext))
print("pdfs matching Zenodo md5 and size:",md5_ok,"of",len(man),"| over 5 MB:",big)
print("home links to papers page:", home_to_list, "| paper pages linked from papers page:",len(paper_pages & listed),"of",len(paper_pages),"| unlisted:",sorted(paper_pages-listed))
rob=open(f"{SITE}/robots.txt").read(); print("robots.txt:",repr(rob))
sm=open(f"{SITE}/sitemap.xml").read(); print("sitemap urls:",sm.count("<loc>"))
print("PROBLEMS:",len(problems)); [print("  ",x) for x in problems]
print("MARKER HITS:",len(marker_hits)); [print("  ",x) for x in marker_hits]
