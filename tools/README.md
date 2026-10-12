# Tools that build the site

The site in `docs/` is generated from the author's Zenodo records. Nothing in `docs/` is edited by hand.

## Rebuild after a new paper is published on Zenodo

```
python3 tools/fetch_zenodo.py ../site_data              # records, version history, PDFs (md5-checked)
python3 tools/build_site.py ../site_data docs YYYY-MM-DD cname
python3 tools/check_site.py docs ../site_data pdf_manifest.json
```

`fetch_zenodo.py` finds the author's records by name and keeps those carrying the author's ORCID
(plus the records listed in `NO_ORCID_RECORDS`). `build_site.py` writes one page per paper, a papers
list, the home page, `robots.txt`, `sitemap.xml` and `CNAME`; the date argument is the sitemap's
`lastmod`. `check_site.py` checks every internal link, the Google Scholar tags on every paper page,
that every PDF matches Zenodo's md5, and scans the text for working-note markers.
`crawl_preview.py URL` opens every page and PDF of a served copy in a headless browser.

## Decisions held in `build_site.py`

- Records are singled out by concept DOI, never by position: `OFF_C` (records the author keeps off
  the site), `BUNDLE_C` (records with no single paper PDF, given abstract-only pages) and the erratum
  that is shown on the Integer Forest page.
- A new record is included automatically unless its concept DOI is added to `OFF_C`.
- Page addresses are permanent once indexed (GitHub Pages cannot redirect), so `SLUG_BY_CONCEPT`
  fixes the shorter names, and every other name is derived from the title.
- Each paper page cites the concept DOI and dates the paper by its first published version.
- The home page text is `tools/about.html`.
