#!/usr/bin/env python3
"""Download a public SNAP directed graph; preserve provenance and content hashes."""
import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import shutil
import urllib.request

from benchmark import sha256

CATALOG = {
    "wiki-Vote": ("https://snap.stanford.edu/data/wiki-Vote.txt.gz", "https://snap.stanford.edu/data/wiki-Vote.html"),
    "web-Google": ("https://snap.stanford.edu/data/web-Google.txt.gz", "https://snap.stanford.edu/data/web-Google.html"),
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("name", choices=CATALOG)
    p.add_argument("--directory", type=Path, default=Path("data"))
    a = p.parse_args()
    url, source = CATALOG[a.name]
    a.directory.mkdir(parents=True, exist_ok=True)
    archive = a.directory / (a.name + ".txt.gz")
    output = a.directory / (a.name + ".txt")
    metadata = a.directory / (a.name + ".metadata.json")
    if any(path.exists() for path in [archive, output, metadata]):
        p.error("Dataset artifacts already exist; choose a new directory to preserve them")
    with urllib.request.urlopen(url, timeout=120) as response, archive.open("xb") as f:
        shutil.copyfileobj(response, f)
    with gzip.open(archive, "rb") as src, output.open("xb") as dst:
        shutil.copyfileobj(src, dst)
    metadata.write_text(json.dumps({"source": source, "url": url, "downloaded_utc": datetime.now(timezone.utc).isoformat(),
                                    "archive_sha256": sha256(archive), "graph_sha256": sha256(output),
                                    "semantics": "Unweighted directed multigraph; raw zero-based IDs, gaps retained as isolated vertices."}, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
