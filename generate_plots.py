#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib"]
# ///
"""
Generate stacked area plots from citation data (OpenAlex and/or Dimensions).

Usage:
    uv run generate_plots.py

Reads:
    openalex/citation_data.json   (if present)
    dimensions/citation_data.json (if present)

Outputs per source directory:
    fig1_absolute.png                - stacked area, all WfMS (Galaxy in Other)
    fig1_percent.png                 - 100% stacked area
    fig1_nogalaxy_absolute.png       - excludes Galaxy
    fig1_nogalaxy_percent.png        - excludes Galaxy, 100% stacked
    plot_data_with_galaxy.csv        - raw data including Galaxy
    plot_data_nogalaxy.csv           - raw data excluding Galaxy
"""

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Adjust when re-running in future years
YEAR_MIN = 2018
YEAR_MAX = 2025
YEARS = list(range(YEAR_MIN, YEAR_MAX + 1))
YS = [str(y) for y in YEARS]

# Plot styling
NEXTFLOW_COLOR = "#2DC09C"
COLORS_WITH_GALAXY = ["#D9D9D9", "#BDBDBD", "#9E9E9E", "#4285F4", NEXTFLOW_COLOR]
LABELS_WITH_GALAXY = ["Other", "CWL", "Snakemake", "Galaxy", "Nextflow"]
COLORS_NO_GALAXY = ["#D9D9D9", "#BDBDBD", "#9E9E9E", NEXTFLOW_COLOR]
LABELS_NO_GALAXY = ["Other", "CWL", "Snakemake", "Nextflow"]


def load_source(source_dir: Path) -> dict | None:
    """Load citation_data.json from a source directory."""
    datafile = source_dir / "citation_data.json"
    if not datafile.exists():
        return None
    with open(datafile) as f:
        return json.load(f)


def extract_series(data: dict) -> dict:
    """Extract per-WfMS yearly totals from citation data."""
    summary = data["summary"]
    result = {}
    for wfms in ["Galaxy", "Nextflow", "Snakemake", "CWL", "Other"]:
        if wfms in summary:
            result[wfms] = [summary[wfms].get(y, 0) for y in YS]
        else:
            result[wfms] = [0] * len(YEARS)
    return result


def make_plot(data_sets, labels, colors, footnote, outpath, version):
    """Create a single stacked area plot."""
    fig, ax = plt.subplots(figsize=(10, 6))

    if version == "percent":
        totals = [sum(d[i] for d in data_sets) for i in range(len(YEARS))]
        plot_data = [[d[i] / totals[i] * 100 for i in range(len(YEARS))] for d in data_sets]
        ax.set_ylabel("Share of citations (%)", fontsize=12)
        ax.set_ylim(0, 100)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    else:
        plot_data = data_sets
        ax.set_ylabel("Citations", fontsize=12)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"{int(v):,}"))

    ax.stackplot(YEARS, *plot_data, labels=labels, colors=colors)
    handles, lbls = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], lbls[::-1], loc="upper left", ncol=4, frameon=False, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xticks(YEARS)
    ax.set_xticklabels(YS, fontsize=11)
    if footnote:
        fig.text(0.13, 0.01, footnote, fontsize=9, color="gray")
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.06 if footnote else 0.03)
    plt.savefig(outpath, dpi=200, bbox_inches="tight")
    svg_path = outpath.with_suffix(".svg") if isinstance(outpath, Path) else Path(outpath).with_suffix(".svg")
    plt.savefig(svg_path, bbox_inches="tight")
    plt.close()
    print(f"  Saved {outpath} + .svg")


def write_csv(series: dict, outpath: Path, include_galaxy: bool):
    """Write plot data to CSV."""
    with open(outpath, "w", newline="") as f:
        writer = csv.writer(f)
        if include_galaxy:
            header = ["Year", "Nextflow", "Snakemake", "CWL", "Galaxy", "Other", "Total"]
        else:
            header = ["Year", "Nextflow", "Snakemake", "CWL", "Other", "Total"]
        writer.writerow(header)

        for i, y in enumerate(YS):
            nf = series["Nextflow"][i]
            snk = series["Snakemake"][i]
            cwl = series["CWL"][i]
            other = series["Other"][i]
            if include_galaxy:
                gal = series["Galaxy"][i]
                total = nf + snk + cwl + gal + other
                row = [y, nf, snk, cwl, gal, other, total]
            else:
                total = nf + snk + cwl + other
                row = [y, nf, snk, cwl, other, total]
            writer.writerow(row)
    print(f"  Saved {outpath}")


def generate_for_source(source_dir: Path, source_name: str):
    """Generate all plots and CSV for a single data source."""
    data = load_source(source_dir)
    if data is None:
        print(f"Skipping {source_name}: no citation_data.json found")
        return

    print(f"\n=== {source_name} ===")
    series = extract_series(data)

    # With Galaxy as separate category
    data_with = [series["Other"], series["CWL"], series["Snakemake"], series["Galaxy"], series["Nextflow"]]

    # Without Galaxy
    data_without = [series["Other"], series["CWL"], series["Snakemake"], series["Nextflow"]]

    for version in ["absolute", "percent"]:
        make_plot(data_with, LABELS_WITH_GALAXY, COLORS_WITH_GALAXY,
                  f"Source: {source_name}",
                  source_dir / f"fig1_{version}.png", version)
        make_plot(data_without, LABELS_NO_GALAXY, COLORS_NO_GALAXY,
                  "",
                  source_dir / f"fig1_nogalaxy_{version}.png", version)

    # CSV files
    write_csv(series, source_dir / "plot_data_with_galaxy.csv", include_galaxy=True)
    write_csv(series, source_dir / "plot_data_nogalaxy.csv", include_galaxy=False)


def main():
    base = Path(__file__).parent
    for subdir, name in [("openalex", "OpenAlex"), ("dimensions", "Dimensions"), ("icite", "iCite"), ("scopus", "Scopus")]:
        source_dir = base / subdir
        if source_dir.exists():
            generate_for_source(source_dir, name)


if __name__ == "__main__":
    main()
