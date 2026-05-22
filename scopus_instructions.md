# Scopus citation data fetcher

Fetches per-year citation counts from the Scopus Citation Overview API for a hardcoded list of ~23 bioinformatics workflow manager papers (Nextflow, Galaxy, Snakemake, CWL, and others). Used to generate a comparison plot alongside data from OpenAlex, Dimensions, and iCite.

The DOI list is hardcoded at the top of `fetch_scopus.py`.

## Requirements

- Python 3.10+
- `requests` (via `uv` or `pip install requests`)
- A Scopus API key from https://dev.elsevier.com/apikey/manage, obtained with an institutional account
- The key must have access to the Citation Overview API (`/content/abstract/citations`). Standard institutional keys often include it, but if not, email `integrationsupport@elsevier.com` asking them to augment your key for this endpoint.
- Must be run from the institution's network — Scopus keys are IP-locked to the subscriber's range. Off-network access requires an InstToken (set as `SCOPUS_INSTTOKEN`).

## Usage

```
export SCOPUS_API_KEY=your_key_here
uv run fetch_scopus.py
```

Or without `uv`:

```
pip install requests
python fetch_scopus.py
```

Takes about 15 seconds (~25 requests, rate-limited to 2/sec).

## Output

Creates a `scopus/` directory containing:

- `citation_data.json` — per-paper totals and per-year breakdowns, matching the schema used by the other citation sources in this project (~20 KB)
- `citations.tsv` — flat table of DOI, title, total citation count (for eyeballing the results)

Only `citation_data.json` is needed downstream.

## Troubleshooting

- **401 or 403 on every paper**: the key doesn't have Citation Overview access. Email Elsevier integration support to request it.
- **A few specific DOIs fail**: usually because they aren't indexed in Scopus. Preprints (bioRxiv DOIs, `10.1101/...`) in particular often aren't. Partial results are fine.
- **429 responses**: the script retries with exponential backoff automatically.
