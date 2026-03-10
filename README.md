# Lunch & Learn — Web Scraping in Python

**March 9, 2026**

Two live demos showing different approaches to pulling data from the web with Python.

---

## demo_1.ipynb — Scraping a Wikipedia Table

The simplest case: a public webpage with data already formatted as an HTML table.

Uses `requests` to fetch the raw HTML from Wikipedia's [Metropolitan Statistical Areas](https://en.wikipedia.org/wiki/Metropolitan_statistical_area) page, then `pandas.read_html()` to parse all tables on the page and grab the one we want. The notebook also touches on:

- Setting a **User-Agent header** (best practice when making HTTP requests)
- Cleaning up Unicode characters (Wikipedia uses fancy dashes that can trip up CSV exports)
- Exporting the result to a CSV

**When to use this approach:** Any time your data lives in a plain HTML table on a public page — fast and minimal dependencies.

---

## demo_2.py — API + Headless Browser Scraping

A two-step pipeline targeting the [Georgia DOT project dashboard](https://www.dot.ga.gov/applications/geopi/Pages/Dashboard.aspx).

**Step 1 — API call:** Fetches a sample of 10 pre-construction road projects from a public GDOT GeoJSON API. The API returns basic fields (project ID, status, short description) and is used to build a list of project URLs. Results are saved to `1_demo_api_only.csv`.

**Step 2 — Headless browser scrape:** The project detail pages are JavaScript-rendered, so a plain HTTP request won't work. [Playwright](https://playwright.dev/python/) launches a headless Chromium browser, loads each page, and extracts richer fields: full description, project manager, construction type, and cost estimate. Results are saved to `2_demo_scraped.csv`.

The script also has **resume logic** — if it's interrupted mid-run, it picks up where it left off rather than starting over.

**When to use this approach:** When you need to use web scraping to collect a large amount of information that could take hours (or days) to complete.

---

## Dependencies

```
requests
pandas
playwright
```

Install Playwright's browser binaries after pip install:

```
playwright install chromium
```
