#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""
Fetch per-year citation counts from NIH iCite (PubMed-based).

Uses NCBI E-utilities to find PMIDs from DOIs, then iCite API to get
per-year citation data from the citedByPmidsByYear field.

Usage:
    uv run fetch_icite.py

Output:
    icite/citation_data.json - per-paper and summary data

Note: Only covers papers indexed in PubMed. Preprints and non-PubMed
sources (Figshare, some conference proceedings) will be missing.
"""

import json
import time
import urllib.request
from collections import Counter
from pathlib import Path

# fmt: off
PAPERS = [
    # (WfMS group, DOI, Label, PMID override or None)
    # PMIDs that can't be found by DOI search need manual overrides.
    # --- Galaxy ---
    ("Galaxy", "10.1093/nar/gkae410",             "Galaxy 2024",          None),
    ("Galaxy", "10.1093/nar/gkac247",             "Galaxy 2022",          None),
    ("Galaxy", "10.1093/nar/gkaa434",             "Galaxy 2020",          None),
    ("Galaxy", "10.1093/nar/gky379",              "Galaxy 2018",          None),
    ("Galaxy", "10.1093/nar/gkw343",              "Galaxy 2016",          None),
    ("Galaxy", "10.1186/gb-2012-13-10-r86",       "Galaxy 2012",         None),
    ("Galaxy", "10.1186/gb-2010-11-8-r86",        "Galaxy 2010",         None),
    ("Galaxy", "10.1101/gr.4086505",              "Galaxy 2005",          None),
    # --- Nextflow ---
    ("Nextflow", "10.1038/s41587-020-0439-x",     "nf-core framework",   None),
    ("Nextflow", "10.1038/nbt.3820",              "Nextflow enables reproducible workflows", None),
    ("Nextflow", "10.1186/s13059-025-03673-9",    "Empowering bioinformatics communities 2025", None),
    ("Nextflow", "10.1101/2024.05.10.592912",     "Empowering bioinformatics communities preprint", None),
    # --- Snakemake ---
    ("Snakemake", "10.12688/f1000research.29032.2", "Snakemake 2021",    "34035898"),  # DOI lookup fails, found by title
    ("Snakemake", "10.1093/bioinformatics/bts480",  "Snakemake 2012",    None),
    # --- CWL ---
    ("CWL", "10.1038/nbt.3772",                   "Toil",                None),
    ("CWL", "10.6084/m9.figshare.3115156.v2",     "CWL v1.0",           None),
    # --- Other ---
    ("Other", "10.1016/j.jbiotec.2017.07.028",    "KNIME reproducible",  None),
    ("Other", "10.1145/1656274.1656280",           "KNIME 2.0",          None),
    ("Other", "10.1007/978-3-030-28954-6_1",      "KNIME data analysis", None),
    ("Other", "10.1093/bioinformatics/bts167",     "Bpipe",              None),
    ("Other", "10.1093/bioinformatics/btx152",     "Pachyderm",          None),
    ("Other", "10.1093/gigascience/giz044",        "SciPipe",            None),
    ("Other", "10.1101/201178",                    "Cromwell/GATK4",     None),
]
# fmt: on

# Adjust this range when re-running in future years
YEAR_MIN = 2018
YEAR_MAX = 2025
YEARS = list(range(YEAR_MIN, YEAR_MAX + 1))

HEADERS = {"User-Agent": "CitationFetcher/1.0 (mailto:phil.ewels@seqera.io)"}


def doi_to_pmid(doi: str) -> str | None:
    """Look up a PMID from a DOI via NCBI E-utilities."""
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={doi}[doi]&retmode=json"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        pmids = data["esearchresult"]["idlist"]
        return pmids[0] if pmids else None
    except Exception:
        return None


def fetch_icite(pmid: str) -> dict | None:
    """Fetch citation data from iCite for a given PMID."""
    url = f"https://icite.od.nih.gov/api/pubs?pmids={pmid}&format=json"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        if data.get("data"):
            return data["data"][0]
    except Exception:
        pass
    return None


def extract_by_year(pub: dict) -> dict[str, int]:
    """Extract per-year citation counts from iCite citedByPmidsByYear field."""
    by_year = Counter()
    for entry in pub.get("citedByPmidsByYear", []):
        for _, year in entry.items():
            by_year[year] += 1
    return {str(y): by_year.get(y, 0) for y in YEARS}


def main():
    outdir = Path(__file__).parent / "icite"
    outdir.mkdir(exist_ok=True)

    results = {}
    for wfms, doi, label, pmid_override in PAPERS:
        print(f"Fetching {wfms:10s} | {label}...")

        # Get PMID
        pmid = pmid_override
        if not pmid:
            pmid = doi_to_pmid(doi)
            time.sleep(0.35)

        if not pmid:
            print(f"  No PMID found - skipping")
            results[label] = {"wfms": wfms, "doi": doi, "error": "no PMID in PubMed"}
            continue

        # Get iCite data
        pub = fetch_icite(pmid)
        time.sleep(0.35)

        if not pub:
            print(f"  iCite lookup failed for PMID {pmid}")
            results[label] = {"wfms": wfms, "doi": doi, "pmid": pmid, "error": "iCite lookup failed"}
            continue

        by_year = extract_by_year(pub)
        total = pub.get("citation_count", 0)
        results[label] = {
            "wfms": wfms,
            "doi": doi,
            "pmid": pmid,
            "total": total,
            "by_year": by_year,
        }
        print(f"  OK PMID={pmid} total={total}")

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

    # Report coverage
    total_papers = len(PAPERS)
    found = sum(1 for info in results.values() if "by_year" in info)
    missing = [label for label, info in results.items() if "by_year" not in info]
    print(f"\nCoverage: {found}/{total_papers} papers")
    if missing:
        print(f"Missing: {', '.join(missing)}")

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
