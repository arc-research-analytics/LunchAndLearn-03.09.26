# demo_2.py — Presentation demo script
# This is a condensed version of the full pipeline for demonstration purposes.
# It fetches a small sample of projects from the GDOT API (Step 1)
# and then scrapes the detail page for each one (Step 2).
#
# Resume logic:
#   - Neither CSV exists        → fresh start: API call → pause → scrape all 10
#   - Only 1_demo_api_only.csv    → skip API call, show URLs, pause, scrape all 10
#   - 2_demo_scraped.csv exists   → skip API call + pause, scrape only remaining projects

import requests
import pandas as pd
import time
import csv
import os
from playwright.sync_api import sync_playwright

HEADLESS = True   # False = show the browser window
SAMPLE_SIZE = 10
API_CSV = "1_demo_api_only.csv"
SCRAPED_CSV = "2_demo_scraped.csv"

SCRAPE_FIELDNAMES = ["ID", "URL", "Status", "Desc_short",
                     "Description", "Cost_estimate", "Type", "Manager"]

# ─────────────────────────────────────────────
# STARTUP — determine where we left off vs. start from scratch
# ─────────────────────────────────────────────

# Scenario 1: Partial scrape exists, load project list from API CSV, skip pause
if os.path.exists(SCRAPED_CSV):

    print(f"Resuming — {SCRAPED_CSV} found.")
    # Load the API CSV into a DataFrame, since we don't need to hit the API again
    projects_sample = pd.read_csv(API_CSV, dtype={"ID": str})
    already_scraped_ids = set(pd.read_csv(
        SCRAPED_CSV, dtype={"ID": str})["ID"].tolist())
    print(f"  {len(already_scraped_ids)} project(s) already scraped, {SAMPLE_SIZE - len(already_scraped_ids)} remaining.")
    do_pause = False

# Scenario 2: API data exists, but scraping hasn't yet begun
elif os.path.exists(API_CSV):
    print(f"Resuming — {API_CSV} found, scraping not yet started.")
    projects_sample = pd.read_csv(API_CSV, dtype={"ID": str})
    already_scraped_ids = set()
    do_pause = True

# Scenario 3: Fresh start — collect new data from the API
else:
    print("Starting fresh — fetching projects from the GDOT API 🥳🎸🦄🔥🚗")
    base_url = "https://enterprisegis.dot.ga.gov/hosting/rest/services/GDOT_Public_Outreach/Hub_Project_Search/MapServer/2/query"
    params = {
        "where": "CONSTRUTION_STATUS_DERIVED = 'PRE-CONSTRUCTION'",
        "outFields": "*",
        "f": "geojson",
        "returnGeometry": "true",
        "resultOffset": 0,
        "resultRecordCount": 100,
    }

    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        raise RuntimeError(
            f"API request failed: {response.status_code} — {response.text}")

    data = response.json()
    df = pd.DataFrame([f["properties"] for f in data["features"]])
    df = df.sample(SAMPLE_SIZE)

    # Light cleanup
    df["CONTRACT_DESCRIPTION"] = df["CONTRACT_DESCRIPTION"].fillna(
        df["SHORT_DESCR"])
    df = df.dropna(axis=1, how="all")
    df["CONSTRUTION_STATUS_DERIVED"] = df["CONSTRUTION_STATUS_DERIVED"].str.replace(
        " ", "-").str.strip()
    df["URL"] = "https://www.dot.ga.gov/applications/geopi/Pages/Dashboard.aspx?ProjectId=" + \
        df["PROJ_ID"].astype(str)

    projects_sample = df[["PROJ_ID", "URL", "CONSTRUTION_STATUS_DERIVED", "CONTRACT_DESCRIPTION"]].rename(columns={
        "PROJ_ID": "ID",
        "CONSTRUTION_STATUS_DERIVED": "Status",
        "CONTRACT_DESCRIPTION": "Desc_short",
    })
    projects_sample = projects_sample.drop_duplicates(
        subset=["ID"]).reset_index(drop=True)

    # Save API-only CSV (used to show why scraping is needed)
    projects_sample.to_csv(API_CSV, index=False)
    print(
        f"  Saved {len(projects_sample)} pre-construction projects to {API_CSV}")

    already_scraped_ids = set()
    do_pause = True

print()

# ─────────────────────────────────────────────
# PAUSE — show URLs to manually peruse before scraping
# ─────────────────────────────────────────────

if do_pause:
    print("#-#-#- Project URLs #-#-#-")
    print()
    for i, (_, project) in enumerate(projects_sample.iterrows(), start=1):
        print(f"  {i:2}. [{project['ID']}]  {project['URL']}")
    print()
    input("Press Enter to commence scraping...")

# ─────────────────────────────────────────────
# Functions to scrape & save the detail page for each project
# ─────────────────────────────────────────────


def scrape_project(page, project):
    """Fetch a GDOT project page with a headless browser and extract detail fields."""
    print(f"    [1/3] Fetching URL: {project['URL']}")
    try:
        page.goto(project["URL"], wait_until="networkidle", timeout=30000)
    except Exception as e:
        print(f"    !! Navigation failed — skipping ({e})")
        return {
            "ID": project["ID"],
            "URL": project["URL"],
            "Status": project["Status"],
            "Desc_short": project["Desc_short"],
            "Description": "No data found",
            "Cost_estimate": "No data found",
            "Type": "No data found",
            "Manager": "No data found",
        }

    print(f"    [2/3] Page loaded — extracting fields...")

    def safe_text(selector):
        loc = page.locator(selector)
        return loc.first.inner_text().strip() if loc.count() > 0 else None

    # --- Long project description (ProjectDescriptionTable) ---
    description = safe_text(
        "table.ProjectDescriptionTable tr:nth-child(2) td:first-child")

    # --- Project manager & project type (ProjectInformationTable) ---
    manager = safe_text(
        "table.ProjectInformationTable tr:nth-child(3) td:nth-child(2)")
    construction_type = safe_text(
        "table.ProjectInformationTable tr:nth-child(9) td:nth-child(2)")

    # --- Cost estimate (rgMasterTable — sums individual line items) ---
    cost_estimate = 0
    cost_rows = page.locator("table.rgMasterTable tbody tr")
    for row in cost_rows.all():
        cells = row.locator("td").all_inner_texts()
        clean_data = [c.replace("\xa0", " ").strip() for c in cells]
        if len(clean_data) == 4:
            try:
                cost_estimate += float(clean_data[2].replace("$",
                                       "").replace(",", ""))
            except ValueError:
                pass

    cost_display = f"${cost_estimate:,.0f}" if cost_estimate else "No data found"
    print(
        f"    [3/3] Manager: {manager or 'No data found'}  |  Type: {construction_type or 'No data found'}  |  Total Cost: {cost_display}")

    return {
        "ID": project["ID"],
        "URL": project["URL"],
        "Status": project["Status"],
        "Desc_short": project["Desc_short"],
        "Description": description,
        "Cost_estimate": cost_estimate,
        "Type": construction_type,
        "Manager": manager,
    }


def save_scraped_project(scraped):
    """Append one scraped project to the output CSV, writing the header if needed."""
    write_header = not os.path.exists(
        SCRAPED_CSV) or os.path.getsize(SCRAPED_CSV) == 0
    with open(SCRAPED_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SCRAPE_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(scraped)


# ─────────────────────────────────────────────
# Collect results and display a summary
# ─────────────────────────────────────────────

to_scrape = projects_sample[~projects_sample["ID"].astype(
    str).isin(already_scraped_ids)]
total = len(projects_sample)

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=HEADLESS)
    page = browser.new_page()

    for i, (_, project) in enumerate(to_scrape.iterrows(), start=len(already_scraped_ids) + 1):
        print()
        print('-#-#-#-#-#-#')
        print(
            f"Scraping {i}/{total}: Project {project['ID']} — {project['Desc_short'][:60]}")
        scraped = scrape_project(page, project)
        save_scraped_project(scraped)
        print('Pausing between scrapes...')
        time.sleep(2)

    browser.close()

# Display final results
results_df = pd.read_csv(SCRAPED_CSV)

print("\n" + "="*60)
print("DEMO RESULTS SUMMARY")
print("="*60)
print(results_df[["ID", "Status", "Type", "Manager",
      "Cost_estimate"]].to_string(index=False))
print(f"\n✅ Demo complete — scraped {len(results_df)} projects.")
