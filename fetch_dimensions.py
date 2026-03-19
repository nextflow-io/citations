#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright"]
# ///
"""
Fetch per-year citation counts from Dimensions via their public badge pages.

This script uses Playwright to browse badge.dimensions.ai and extract
citation-by-year data from the Highcharts charts on each publication page.

Usage:
    # Install browser if needed (first time only):
    #   uv run fetch_dimensions.py  # will error with install instructions
    #   uv run --with playwright python -m playwright install chromium
    #
    # Then run:
    uv run fetch_dimensions.py

Output:
    dimensions/citation_data.json - per-paper and summary data
"""

import asyncio
import json
from pathlib import Path

# fmt: off
PAPERS = [
    # (WfMS group, DOI, Label)
    # --- Galaxy ---
    ("Galaxy", "10.1093/nar/gkae410",             "Galaxy 2024"),
    ("Galaxy", "10.1093/nar/gkac247",             "Galaxy 2022"),
    ("Galaxy", "10.1093/nar/gkaa434",             "Galaxy 2020"),
    ("Galaxy", "10.1093/nar/gky379",              "Galaxy 2018"),
    ("Galaxy", "10.1093/nar/gkw343",              "Galaxy 2016"),
    ("Galaxy", "10.1186/gb-2012-13-10-r86",       "Galaxy 2012"),
    ("Galaxy", "10.1186/gb-2010-11-8-r86",        "Galaxy 2010"),
    ("Galaxy", "10.1101/gr.4086505",              "Galaxy 2005"),
    # --- Nextflow ---
    ("Nextflow", "10.1038/s41587-020-0439-x",     "nf-core framework"),
    ("Nextflow", "10.1038/nbt.3820",              "Nextflow enables reproducible workflows"),
    ("Nextflow", "10.1186/s13059-025-03673-9",    "Empowering bioinformatics communities 2025"),
    ("Nextflow", "10.1101/2024.05.10.592912",     "Empowering bioinformatics communities preprint"),
    # --- Snakemake ---
    ("Snakemake", "10.12688/f1000research.29032.2", "Snakemake 2021"),
    ("Snakemake", "10.1093/bioinformatics/bts480",  "Snakemake 2012"),
    # --- CWL ---
    ("CWL", "10.1038/nbt.3772",                   "Toil"),
    ("CWL", "10.6084/m9.figshare.3115156.v2",     "CWL v1.0"),
    # --- Other ---
    ("Other", "10.1016/j.jbiotec.2017.07.028",    "KNIME reproducible"),
    ("Other", "10.1145/1656274.1656280",           "KNIME 2.0"),
    ("Other", "10.1007/978-3-030-28954-6_1",      "KNIME data analysis"),
    ("Other", "10.1093/bioinformatics/bts167",     "Bpipe"),
    ("Other", "10.1093/bioinformatics/btx152",     "Pachyderm"),
    ("Other", "10.1093/gigascience/giz044",        "SciPipe"),
    ("Other", "10.1101/201178",                    "Cromwell/GATK4"),
]
# fmt: on

YEAR_MIN = 2018
YEAR_MAX = 2025
YEARS = list(range(YEAR_MIN, YEAR_MAX + 1))

# JS to extract Highcharts data after clicking the Citations tab
EXTRACT_JS = """
() => {
    const HC = window._Highcharts;
    if (!HC || !HC.charts) return null;
    const charts = HC.charts.filter(c => c);
    if (charts.length === 0) return null;
    const chart = charts[0];
    const series = chart.series[0];
    return series.data.map(p => ({year: p.category, citations: p.y}));
}
"""


async def fetch_paper(page, doi: str, label: str) -> dict | None:
    """Navigate to a Dimensions badge page and extract citation-by-year data."""
    url = f"https://badge.dimensions.ai/details/doi/{doi}"
    try:
        await page.goto(url, wait_until="networkidle", timeout=20000)
    except Exception:
        await page.goto(url, timeout=20000)

    # Accept cookies if the dialog appears (first visit only)
    try:
        accept_btn = page.get_by_role("button", name="Accept all")
        if await accept_btn.is_visible(timeout=2000):
            await accept_btn.click()
            await page.wait_for_timeout(500)
    except Exception:
        pass

    # Check for 404
    content = await page.content()
    if "404" in content and "NOT FOUND" in content:
        print(f"  404 - not found on Dimensions")
        return None

    # Click the Citations tab
    try:
        citations_link = page.get_by_role("link", name="Citations")
        await citations_link.click()
        await page.wait_for_timeout(2000)
    except Exception as e:
        print(f"  Could not click Citations tab: {e}")
        return None

    # Extract chart data
    data = await page.evaluate(EXTRACT_JS)
    if not data:
        print(f"  No chart data found")
        return None

    by_year = {}
    for point in data:
        y = point["year"]
        if YEAR_MIN <= y <= YEAR_MAX:
            by_year[str(y)] = point["citations"]

    return by_year


async def main():
    from playwright.async_api import async_playwright

    outdir = Path(__file__).parent / "dimensions"
    outdir.mkdir(exist_ok=True)

    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for wfms, doi, label in PAPERS:
            print(f"Fetching {wfms:10s} | {label}...")
            by_year = await fetch_paper(page, doi, label)
            if by_year:
                # Ensure all years present
                for y in YEARS:
                    by_year.setdefault(str(y), 0)
                results[label] = {"wfms": wfms, "doi": doi, "by_year": by_year}
                total = sum(by_year.values())
                print(f"  OK total={total}")
            else:
                results[label] = {"wfms": wfms, "doi": doi, "error": "not found or no chart"}

        await browser.close()

    # Build per-WfMS summary
    wfms_groups = sorted(set(p[0] for p in PAPERS))
    summary = {}
    for wfms in wfms_groups:
        totals = {str(y): 0 for y in YEARS}
        for label, info in results.items():
            if info.get("wfms") == wfms and "by_year" in info:
                for y in YEARS:
                    totals[str(y)] += info["by_year"].get(str(y), 0)
        summary[wfms] = totals

    output = {"papers": results, "summary": summary}
    outfile = outdir / "citation_data.json"
    outfile.write_text(json.dumps(output, indent=2))
    print(f"\nSaved to {outfile}")

    # Print summary table
    print(f"\n{'WfMS':<12}", end="")
    for y in YEARS:
        print(f" {y:>6}", end="")
    print()
    print("-" * (12 + 7 * len(YEARS)))
    for wfms in wfms_groups:
        print(f"{wfms:<12}", end="")
        for y in YEARS:
            print(f" {summary[wfms][str(y)]:>6}", end="")
        print()


if __name__ == "__main__":
    asyncio.run(main())
