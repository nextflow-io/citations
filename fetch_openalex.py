#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""
Fetch per-year citation counts from OpenAlex for WfMS papers.

Usage:
    uv run fetch_openalex.py

Output:
    openalex/citation_data.json - per-paper and summary data
"""

import json
import time
import urllib.request
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

# Adjust this range when re-running in future years
YEAR_MIN = 2018
YEAR_MAX = 2025
YEARS = list(range(YEAR_MIN, YEAR_MAX + 1))

HEADERS = {"User-Agent": "CitationFetcher/1.0 (mailto:phil.ewels@seqera.io)"}
API_BASE = "https://api.openalex.org/works/doi:{}?select=title,counts_by_year,cited_by_count"


def fetch_paper(doi: str) -> dict | None:
    url = API_BASE.format(doi)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def main():
    outdir = Path(__file__).parent / "openalex"
    outdir.mkdir(exist_ok=True)

    results = {}
    for wfms, doi, label in PAPERS:
        print(f"Fetching {wfms:10s} | {label}...")
        data = fetch_paper(doi)
        if data:
            counts = {e["year"]: e["cited_by_count"] for e in data.get("counts_by_year", [])}
            by_year = {str(y): counts.get(y, 0) for y in YEARS}
            results[label] = {
                "wfms": wfms,
                "doi": doi,
                "total": data.get("cited_by_count", 0),
                "by_year": by_year,
            }
            print(f"  OK total={data.get('cited_by_count', 0)}")
        else:
            results[label] = {"wfms": wfms, "doi": doi, "error": "not found"}
        time.sleep(0.5)

    # Build per-WfMS summary
    wfms_groups = sorted(set(p[0] for p in PAPERS))
    summary = {}
    for wfms in wfms_groups:
        totals = {str(y): 0 for y in YEARS}
        for label, info in results.items():
            if info.get("wfms") == wfms and "by_year" in info:
                for y in YEARS:
                    totals[str(y)] += info["by_year"][str(y)]
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
    main()
