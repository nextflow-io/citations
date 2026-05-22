#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///
"""
Fetch per-year citation counts from Scopus for WfMS papers.

Requires an institutional Scopus API key with access to the Citation
Overview API (/content/abstract/citations). Note that Elsevier's
Scopus Integration Team must specifically enable ("augment") this
endpoint on the key — a standard institutional key is not always
enough. If in doubt, email integrationsupport@elsevier.com.

Usage (on the institution's network):
    export SCOPUS_API_KEY=your_key
    # Optional: only needed if running off-campus
    # export SCOPUS_INSTTOKEN=your_insttoken
    uv run fetch_scopus.py

Send the resulting scopus/ directory (or just citation_data.json) back
to whoever is assembling the plots.

Outputs:
    scopus/citation_data.json  - same schema as openalex/, icite/
    scopus/citations.tsv       - doi, title, total_citations (one row per paper)

After running, the main repo's generate_plots.py will pick up the
scopus/ directory automatically and produce the same plots and CSVs
as for OpenAlex/Dimensions/iCite.
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

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

# Keep in sync with fetch_openalex.py / fetch_icite.py
YEAR_MIN = 2018
YEAR_MAX = 2025
YEARS = list(range(YEAR_MIN, YEAR_MAX + 1))

CITATION_OVERVIEW_URL = "https://api.elsevier.com/content/abstract/citations"
ABSTRACT_URL = "https://api.elsevier.com/content/abstract/doi/{}"
RATE_LIMIT_SEC = 0.5  # ~2 req/sec
MAX_RETRIES = 4


def build_headers(api_key: str, insttoken: str | None) -> dict:
    headers = {"Accept": "application/json", "X-ELS-APIKey": api_key}
    if insttoken:
        headers["X-ELS-Insttoken"] = insttoken
    return headers


def request_with_retry(url, headers, params, session):
    """GET with 429/5xx retry + exponential backoff. Returns requests.Response or None."""
    backoff = 1.0
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(url, headers=headers, params=params, timeout=30)
        except requests.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                print(f"    request failed: {e}")
                return None
            time.sleep(backoff)
            backoff *= 2
            continue

        if r.status_code == 429:
            wait = float(r.headers.get("Retry-After", backoff))
            print(f"    429 rate-limited; sleeping {wait:.1f}s")
            time.sleep(max(wait, backoff))
            backoff *= 2
            continue
        if 500 <= r.status_code < 600:
            time.sleep(backoff)
            backoff *= 2
            continue
        return r
    return None


def fetch_citation_overview(doi: str, headers: dict, session: requests.Session) -> tuple[dict | None, str | None]:
    """Fetch per-year citation data for a single DOI. Returns (parsed, error)."""
    params = {
        "doi": doi,
        "date": f"{YEAR_MIN}-{YEAR_MAX}",
        "httpAccept": "application/json",
    }
    r = request_with_retry(CITATION_OVERVIEW_URL, headers, params, session)
    if r is None:
        return None, "request failed after retries"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:300]}"

    try:
        data = r.json()
    except ValueError:
        return None, f"non-JSON response: {r.text[:200]}"

    try:
        resp = data["abstract-citations-response"]
        matrix = resp["citeInfoMatrix"]["citeInfoMatrixXML"]["citationMatrix"]
        entries = matrix.get("citeInfo") or []
        if not entries:
            return None, "empty citeInfo (DOI not in Scopus?)"
        entry = entries[0]

        # Per-year counts — 'cc' is a list of {"$": "N"} in order of YEARS
        cc = entry.get("cc") or []
        by_year_list = [int(c.get("$", 0) or 0) for c in cc]
        # Pad or truncate defensively to match our year range
        if len(by_year_list) < len(YEARS):
            by_year_list += [0] * (len(YEARS) - len(by_year_list))
        by_year_list = by_year_list[: len(YEARS)]
        by_year = {str(y): n for y, n in zip(YEARS, by_year_list)}

        total = int(entry.get("rowTotal", 0) or 0)
        title = entry.get("title", "") or ""
        # Pre-range and post-range counts (for completeness)
        pcc = int(entry.get("pcc", 0) or 0)
        lcc = int(entry.get("lcc", 0) or 0)
    except (KeyError, ValueError, TypeError) as e:
        return None, f"parse error: {e}"

    return {"title": title, "total": total, "by_year": by_year, "pcc": pcc, "lcc": lcc}, None


def fetch_title_fallback(doi: str, headers: dict, session: requests.Session) -> str:
    """Abstract Retrieval call used only to recover a title if Citation Overview doesn't return one."""
    r = request_with_retry(ABSTRACT_URL.format(doi), headers, None, session)
    if r is None or r.status_code != 200:
        return ""
    try:
        core = r.json().get("abstracts-retrieval-response", {}).get("coredata", {})
        return core.get("dc:title", "") or ""
    except ValueError:
        return ""


def main():
    api_key = os.environ.get("SCOPUS_API_KEY")
    if not api_key:
        print("ERROR: set SCOPUS_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)
    insttoken = os.environ.get("SCOPUS_INSTTOKEN")  # optional, off-campus use
    headers = build_headers(api_key, insttoken)

    outdir = Path(__file__).parent / "scopus"
    outdir.mkdir(exist_ok=True)

    session = requests.Session()
    results = {}
    failed = []
    tsv_rows = []

    for wfms, doi, label in PAPERS:
        print(f"Fetching {wfms:10s} | {label} ({doi})")
        parsed, err = fetch_citation_overview(doi, headers, session)
        time.sleep(RATE_LIMIT_SEC)

        if parsed is None:
            # First-pass diagnostic: is this an access issue, or a missing DOI?
            hint = ""
            if err and ("401" in err or "403" in err):
                hint = "  (key may lack Citation Overview access — contact integrationsupport@elsevier.com)"
            print(f"  FAILED: {err}{hint}")
            failed.append((doi, label, err))
            results[label] = {"wfms": wfms, "doi": doi, "error": err}
            tsv_rows.append((doi, "", ""))
            continue

        title = parsed["title"]
        if not title:
            title = fetch_title_fallback(doi, headers, session)
            time.sleep(RATE_LIMIT_SEC)

        results[label] = {
            "wfms": wfms,
            "doi": doi,
            "title": title,
            "total": parsed["total"],
            "by_year": parsed["by_year"],
            "pcc": parsed["pcc"],
            "lcc": parsed["lcc"],
        }
        tsv_rows.append((doi, title, parsed["total"]))
        print(f"  OK total={parsed['total']}  in-range={sum(parsed['by_year'].values())}")

    # Build per-WfMS summary (matches schema of openalex/icite citation_data.json)
    wfms_groups = sorted({p[0] for p in PAPERS})
    summary = {}
    for wfms in wfms_groups:
        totals = {str(y): 0 for y in YEARS}
        for info in results.values():
            if info.get("wfms") == wfms and "by_year" in info:
                for y in YEARS:
                    totals[str(y)] += info["by_year"][str(y)]
        summary[wfms] = totals

    output = {"papers": results, "summary": summary}
    (outdir / "citation_data.json").write_text(json.dumps(output, indent=2))
    print(f"\nSaved {outdir / 'citation_data.json'}")

    # TSV of per-paper totals
    tsv_path = outdir / "citations.tsv"
    with open(tsv_path, "w") as f:
        f.write("doi\ttitle\tcitation_count\n")
        for doi, title, count in tsv_rows:
            clean_title = (title or "").replace("\t", " ").replace("\n", " ").strip()
            f.write(f"{doi}\t{clean_title}\t{count}\n")
    print(f"Saved {tsv_path}")

    # Coverage + summary table
    total_papers = len(PAPERS)
    ok = sum(1 for info in results.values() if "by_year" in info)
    print(f"\nCoverage: {ok}/{total_papers} papers")

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

    if failed:
        print(f"\n{len(failed)} DOIs failed:")
        for doi, label, err in failed:
            print(f"  {doi}  ({label})  -  {err}")


if __name__ == "__main__":
    main()
