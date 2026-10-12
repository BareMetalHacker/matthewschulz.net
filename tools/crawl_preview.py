import asyncio, sys
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
START = sys.argv[1]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        seen, queue, bad, nocss = set(), [START], [], []
        while queue:
            u = queue.pop()
            if u in seen: continue
            seen.add(u)
            if not (u.endswith(".html") or u.endswith("/")):
                rr = await pg.request.get(u)
                if rr.status != 200: bad.append((u, rr.status))
                continue
            r = await pg.goto(u)
            if r is None or r.status != 200: bad.append((u, r.status if r else None)); continue
            css = await pg.evaluate("getComputedStyle(document.body).backgroundColor")
            if css in ("rgba(0, 0, 0, 0)", "transparent"): nocss.append(u)
            for h in await pg.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))"):
                v = urljoin(u, h)
                if urlparse(v).netloc == urlparse(START).netloc and v.startswith(START): queue.append(v.split("#")[0])
        print("urls fetched:", len(seen), "| non-200:", bad, "| pages without stylesheet:", nocss)
        await b.close()
asyncio.run(main())
