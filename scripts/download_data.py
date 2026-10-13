"""Refresh data/air_quality.csv with the latest release from NYC Open Data.

    python scripts/download_data.py

The repo already ships a snapshot, so this is only needed to pick up newer years.
After downloading, rerun scripts/run_analysis.py; the README numbers come from
results/summary.json and may change.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

URL = "https://data.cityofnewyork.us/api/views/c3uy-2p5r/rows.csv?accessType=DOWNLOAD"
DEST = Path(__file__).resolve().parents[1] / "data" / "air_quality.csv"


def main() -> None:
    tmp = DEST.with_suffix(".csv.part")
    print(f"Downloading {URL}")
    try:
        urllib.request.urlretrieve(URL, tmp)
    except OSError as err:
        sys.exit(f"Download failed: {err}")
    header = tmp.read_text(encoding="utf-8").splitlines()[0]
    if "Geo Type Name" not in header:
        tmp.unlink()
        sys.exit("Downloaded file does not look like the Air Quality dataset; kept the old copy.")
    tmp.replace(DEST)
    print(f"Saved {DEST.relative_to(DEST.parents[1])}")


if __name__ == "__main__":
    main()
