# WfMS Citation Analysis

Regenerates Supplementary Figure 1 from [Langer et al. 2025, _Genome Biology_,
"Empowering bioinformatics communities with Nextflow and nf-core"][paper] —
per-year citation counts for bioinformatics workflow management systems.

[paper]: https://doi.org/10.1186/s13059-025-03673-9
[supplement]: https://static-content.springer.com/esm/art%3A10.1186%2Fs13059-025-03673-9/MediaObjects/13059_2025_3673_MOESM1_ESM.docx

The original figure (and methodology) is in the [published supplementary file][supplement] (DOCX).

### Scopus (primary)

![WfMS citation counts from Scopus, 2018-2025](scopus/fig1_nogalaxy_absolute.png)

**Note:** Two DOIs are mis-indexed in Scopus and have been excluded (Galaxy 2012, Pachyderm — see [Notes](#notes)). Four further DOIs are missing (preprints, Figshare, ACM conference proceedings), so 17/23 papers contribute.

|                    | Absolute                                                                            | Percentage                                                                        | Data                                            |
| ------------------ | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------- |
| **Without Galaxy** | [PNG](scopus/fig1_nogalaxy_absolute.png) / [SVG](scopus/fig1_nogalaxy_absolute.svg) | [PNG](scopus/fig1_nogalaxy_percent.png) / [SVG](scopus/fig1_nogalaxy_percent.svg) | [CSV](scopus/plot_data_nogalaxy.csv)            |
| **With Galaxy**    | [PNG](scopus/fig1_absolute.png) / [SVG](scopus/fig1_absolute.svg)                   | [PNG](scopus/fig1_percent.png) / [SVG](scopus/fig1_percent.svg)                   | [CSV](scopus/plot_data_with_galaxy.csv)         |

### Other sources

| OpenAlex | Dimensions | iCite |
| :------: | :--------: | :---: |
| ![WfMS citation counts from OpenAlex, 2018-2025](openalex/fig1_nogalaxy_absolute.png) | ![WfMS citation counts from Dimensions, 2018-2025](dimensions/fig1_nogalaxy_absolute.png) | ![WfMS citation counts from iCite, 2018-2025](icite/fig1_nogalaxy_absolute.png) |
| OpenAlex is slow to update, so the most recent year's citation counts will typically lag behind reality for several months after publication. | Snakemake counts are underrepresented: Dimensions splits F1000Research paper revisions into separate records, and only v1 of the Snakemake 2021 paper (311 citations) has per-year data — v2 (1,643 citations) has no per-year chart. See [Notes](#notes). | Limited to PubMed-indexed papers, so 4 papers without PMIDs (preprints, Figshare, some conference proceedings) are missing. |
| CSV: [with Galaxy](openalex/plot_data_with_galaxy.csv) / [no Galaxy](openalex/plot_data_nogalaxy.csv) — [all plots](openalex/) | CSV: [with Galaxy](dimensions/plot_data_with_galaxy.csv) / [no Galaxy](dimensions/plot_data_nogalaxy.csv) — [all plots](dimensions/) | CSV: [with Galaxy](icite/plot_data_with_galaxy.csv) / [no Galaxy](icite/plot_data_nogalaxy.csv) — [all plots](icite/) |

## Quick start

```bash
# 1. Fetch citation data from OpenAlex (free API, ~30 seconds)
uv run fetch_openalex.py

# 2. Fetch citation data from Dimensions (browser scraping, ~5 minutes)
uv run fetch_dimensions.py

# 3. Fetch citation data from NIH iCite (free API, ~30 seconds)
uv run fetch_icite.py

# 4. (Optional) Fetch citation data from Scopus (requires institutional API key)
#    See scopus_instructions.md for setup. Must run from the institution's network.
export SCOPUS_API_KEY=your_key
uv run fetch_scopus.py

# 5. Generate plots and CSVs for all sources
uv run generate_plots.py
```

## Data sources

| Source           | Per-year data | API key needed | Method                                                            | Coverage |
| ---------------- | ------------- | -------------- | ----------------------------------------------------------------- | -------- |
| **OpenAlex**     | Yes           | No             | REST API                                                          | 23/23 papers |
| **Dimensions**   | Yes           | No             | Browser scraping (Highcharts extraction from badge.dimensions.ai) | 22/23 papers |
| **iCite**        | Yes           | No             | NIH iCite API (PubMed-based)                                      | 19/23 papers |
| **Scopus**       | Yes           | Yes (institutional) | Scopus Citation Overview API (`fetch_scopus.py`)             | 17/23 papers |
| CrossRef         | Totals only   | No             | REST API                                                          | — |
| Google Scholar   | Totals only   | No             | `scholarly` library (very slow, gets rate-limited)                | — |
| Semantic Scholar | Unreliable    | No             | Free API returns incomplete citation subsets                      | — |
| Altmetric        | No            | Yes (403)      | N/A                                                               | — |

**OpenAlex**, **Dimensions**, and **iCite** are free and need no API key. **Scopus** is included for parity with the original paper but needs an institutional API key with Citation Overview access — see [`scopus_instructions.md`](scopus_instructions.md). OpenAlex has the best coverage.

## Papers included

### Galaxy
| DOI                         | Label              |
| --------------------------- | ------------------ |
| `10.1093/nar/gkae410`       | Galaxy 2024 update |
| `10.1093/nar/gkac247`       | Galaxy 2022 update |
| `10.1093/nar/gkaa434`       | Galaxy 2020 update |
| `10.1093/nar/gky379`        | Galaxy 2018 update |
| `10.1093/nar/gkw343`        | Galaxy 2016 update |
| `10.1186/gb-2012-13-10-r86` | Galaxy 2012        |
| `10.1186/gb-2010-11-8-r86`  | Galaxy 2010        |
| `10.1101/gr.4086505`        | Galaxy 2005        |

### Nextflow
| DOI                          | Label                                          |
| ---------------------------- | ---------------------------------------------- |
| `10.1038/s41587-020-0439-x`  | nf-core framework (2020)                       |
| `10.1038/nbt.3820`           | Nextflow enables reproducible workflows (2017) |
| `10.1186/s13059-025-03673-9` | Empowering bioinformatics communities (2025)   |
| `10.1101/2024.05.10.592912`  | Same paper, preprint version                   |

### Snakemake
| DOI                              | Label                                           |
| -------------------------------- | ----------------------------------------------- |
| `10.12688/f1000research.29032.2` | Sustainable data analysis with Snakemake (2021) |
| `10.1093/bioinformatics/bts480`  | Snakemake workflow engine (2012)                |

### CWL (shown separately from Other)
| DOI                              | Label    |
| -------------------------------- | -------- |
| `10.1038/nbt.3772`               | Toil     |
| `10.6084/m9.figshare.3115156.v2` | CWL v1.0 |

### Other
| DOI                             | Label               |
| ------------------------------- | ------------------- |
| `10.1016/j.jbiotec.2017.07.028` | KNIME reproducible  |
| `10.1145/1656274.1656280`       | KNIME 2.0           |
| `10.1007/978-3-030-28954-6_1`   | KNIME data analysis |
| `10.1093/bioinformatics/bts167` | Bpipe               |
| `10.1093/bioinformatics/btx152` | Pachyderm           |
| `10.1093/gigascience/giz044`    | SciPipe             |
| `10.1101/201178`                | Cromwell/GATK4      |

## Plot description

- **Stacked area charts** with Nextflow (#2DC09C) on top, then Galaxy (blue), Snakemake, CWL, and Other in grey shades
- **Two variants**: with Galaxy as a separate category, and without Galaxy
- **Two scales**: absolute citation counts and 100% stacked (percentage)

## Notes

- **Source comparison**: All four sources agree on the overall trend. OpenAlex has the best coverage (23/23 papers). Dimensions is missing CWL v1.0 (Figshare DOI, not indexed). iCite is missing 4 papers without PMIDs (preprints, Figshare, some conference proceedings). Scopus is missing 4 DOIs (preprints, Figshare, ACM proceedings) and has two mis-indexed records (see below), giving 17/23 effective coverage.
- **F1000Research versions**: Dimensions treats each F1000Research revision as a separate record with its own DOI. `fetch_dimensions.py` handles this by fetching all versions and summing their citations. Currently only v1 of Snakemake 2021 renders a per-year chart; v2 has the majority of citations but no chart.
- **Year range**: Edit `YEAR_MIN` / `YEAR_MAX` in each script to extend the range.
- **Adding papers**: Add new entries to the `PAPERS` list in all four `fetch_*.py` scripts, then re-run all five scripts.
- **Dimensions scraping**: The `fetch_dimensions.py` script extracts data from Highcharts charts on badge.dimensions.ai. If their page structure changes, the JS extraction (`window._Highcharts`) may need updating. As a fallback, use the Playwright MCP in Claude Code to manually navigate and extract data (see below).
- **iCite**: Only covers PubMed-indexed papers. Uses the `citedByPmidsByYear` field which gives exact per-year counts. Some papers need PMID overrides (DOI lookup fails) — these are hardcoded in `fetch_icite.py`.
- **Scopus DOI mismatches**: Scopus returned the wrong record for two DOIs — `10.1186/gb-2012-13-10-r86` (Galaxy 2012) resolved to a histone PTM paper, and `10.1093/bioinformatics/btx152` (Pachyderm) resolved to HiC-spector. Both have been excluded from the Scopus summary in `scopus/citation_data.json` (their `by_year` data is removed; the entries are kept with an `error` field). If Scopus fixes this in future, re-run `fetch_scopus.py`.

## Manual Dimensions extraction (Claude Code fallback)

If `fetch_dimensions.py` breaks, use the Playwright MCP interactively:

1. Navigate to `https://badge.dimensions.ai/details/doi/{DOI}`
2. Accept cookies if prompted
3. Click the "Citations" tab
4. Extract data with JS: `window._Highcharts.charts.filter(c=>c)[0].series[0].data.map(p=>({year:p.category,citations:p.y}))`
5. Repeat for each DOI

## License

Code and data in this repository are licensed under the [Apache License 2.0](LICENSE).
