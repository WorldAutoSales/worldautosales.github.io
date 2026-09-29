"""
Generates a public-safe copy of the manufacturer/model data assets.

GoodCarBadCar (GCBC) and BestSellingCarsBlog (BSCB) both restrict use of their
figures to personal, non-commercial purposes. Rows sourced from either are
tagged in the source data with "source_type":"gcbc" or "source_type":"bscb".
This script strips those rows out and writes the result to public/assets/,
so the public site build never republishes restricted-source data while the
personal/local copy (assets/) keeps everything.

Usage:
    python scripts/build_public_data.py

Output: public/assets/<same filenames>, each a drop-in replacement for the
corresponding file in assets/ (same `const NAME = {...};` wrapper).
"""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "assets"
OUTPUT_DIR = REPO_ROOT / "public" / "assets"

# Only these files carry row-level source_type tags; every other asset file
# is copied by the site's normal deploy process untouched.
TARGET_FILES = [
    "manufacturer-yearly-data.js",
    "manufacturer-monthly-data.js",
    "manufacturer-model-yearly-data.js",
    "manufacturer-model-monthly-data.js",
]

RESTRICTED_SOURCE_TYPES = {"gcbc", "bscb"}


def strip_restricted_rows(data):
    total_kept = 0
    total_dropped = 0
    for country, rows in data.items():
        kept = [r for r in rows if r.get("source_type") not in RESTRICTED_SOURCE_TYPES]
        total_dropped += len(rows) - len(kept)
        total_kept += len(kept)
        data[country] = kept
    return data, total_kept, total_dropped


def process_file(filename):
    src_path = SOURCE_DIR / filename
    with open(src_path, encoding="utf-8") as f:
        content = f.read()

    m = re.match(r"(const\s+\w+\s*=\s*)(\{.*\})(;\s*)$", content, re.S)
    if not m:
        raise ValueError(f"{filename}: did not match expected 'const NAME = {{...}};' wrapper")
    prefix, body, suffix = m.group(1), m.group(2), m.group(3)

    data = json.loads(body)
    data, kept, dropped = strip_restricted_rows(data)

    new_body = json.dumps(data, separators=(",", ":"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / filename
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(prefix + new_body + suffix)

    print(f"{filename}: kept {kept} rows, dropped {dropped} restricted (gcbc/bscb) rows -> {out_path}")


def main():
    for filename in TARGET_FILES:
        process_file(filename)


if __name__ == "__main__":
    main()
