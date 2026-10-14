"""Document registry: keeps manifest.csv in sync with the files on disk.

Derived fields (doc_id, pages, sha1) are always recomputed from the files.
Curated fields (company, entity, report_year, ...) are kept as reviewed by a
human; for new files they are inferred from the filename and marked
reviewed=false until someone checks them.

Usage:
    python -m normrag.ingestion.registry data/v0            # sync and write
    python -m normrag.ingestion.registry data/v0 --check    # fail if out of date
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pypdfium2 as pdfium

MANIFEST_NAME = "manifest.csv"
SUPPORTED_SUFFIXES = {".pdf", ".docx"}
EXCLUDED_DIRS = {"eval"}

DERIVED_FIELDS = ["doc_id", "pages", "sha1"]
CURATED_FIELDS = [
    "doc_type", "company", "entity", "report_year", "period_end",
    "currency", "enabled", "reviewed", "notes",
]
COLUMNS = [
    "doc_id", "doc_type", "company", "entity", "report_year", "period_end",
    "currency", "pages", "sha1", "enabled", "reviewed", "notes",
]

# Naming convention for annual reports: <Company>_Annual_Report_<YYYY>.pdf
ANNUAL_REPORT_RE = re.compile(r"^(?P<company>[A-Za-z]+)_Annual_Report_(?P<year>\d{4})\.pdf$")


@dataclass
class SyncReport:
    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    moved: list[tuple[str, str]] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unreviewed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.changed or self.moved or self.removed)


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def page_count(path: Path) -> str:
    if path.suffix.lower() != ".pdf":
        return ""  # DOCX has no fixed pages
    doc = pdfium.PdfDocument(path)
    try:
        return str(len(doc))
    finally:
        doc.close()


def scan(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if rel.parts[0] in EXCLUDED_DIRS:
            continue
        files.append(path)
    return files


def infer_curated(doc_id: str) -> dict[str, str]:
    """Best-effort guess for a new file. Always needs human review."""
    name = Path(doc_id).name
    row = {f: "" for f in CURATED_FIELDS}
    row.update(enabled="false", reviewed="false")
    m = ANNUAL_REPORT_RE.match(name)
    if m:
        row.update(
            doc_type="annual_report",
            company=m["company"],
            report_year=m["year"],
            notes="auto-added from filename; check entity, period_end, currency",
        )
    else:
        row["notes"] = "auto-added; filename does not match a known convention"
    return row


def read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in sorted(rows, key=lambda r: r["doc_id"]):
            writer.writerow({c: row.get(c, "") for c in COLUMNS})


def validate(rows: list[dict[str, str]]) -> list[str]:
    errors = []
    for r in rows:
        if r["enabled"] not in {"true", "false"} or r["reviewed"] not in {"true", "false"}:
            errors.append(f"{r['doc_id']}: enabled/reviewed must be true or false")
        if r["enabled"] == "true" and r["reviewed"] != "true":
            errors.append(f"{r['doc_id']}: enabled but not reviewed")
        if r["enabled"] == "true" and r["doc_type"] == "annual_report":
            missing = [f for f in ("company", "entity", "report_year", "currency") if not r[f]]
            if missing:
                errors.append(f"{r['doc_id']}: missing {', '.join(missing)}")
    return errors


def sync(root: Path) -> tuple[list[dict[str, str]], SyncReport]:
    report = SyncReport()
    old = {r["doc_id"]: r for r in read_manifest(root / MANIFEST_NAME)}
    on_disk = {p.relative_to(root).as_posix(): p for p in scan(root)}

    hashes = {doc_id: sha1_of(p) for doc_id, p in on_disk.items()}
    gone = {doc_id: r for doc_id, r in old.items() if doc_id not in on_disk}
    gone_by_sha1 = {r["sha1"]: doc_id for doc_id, r in gone.items()}

    rows = []
    for doc_id, path in on_disk.items():
        derived = {"doc_id": doc_id, "pages": page_count(path), "sha1": hashes[doc_id]}
        if doc_id in old:
            prev = old[doc_id]
            if prev.get("sha1") and prev["sha1"] != derived["sha1"]:
                report.changed.append(doc_id)
            curated = {f: prev.get(f, "") for f in CURATED_FIELDS}
            # Rows written before the `reviewed` column existed were curated by hand.
            curated["reviewed"] = curated["reviewed"] or "true"
        elif derived["sha1"] in gone_by_sha1:
            src = gone_by_sha1.pop(derived["sha1"])
            gone.pop(src)
            report.moved.append((src, doc_id))
            curated = {f: old[src].get(f, "") for f in CURATED_FIELDS}
        else:
            report.added.append(doc_id)
            curated = infer_curated(doc_id)
        row = {**curated, **derived}
        if row["reviewed"] != "true":
            report.unreviewed.append(doc_id)
        rows.append(row)

    report.removed = sorted(gone)
    report.errors = validate(rows)
    return rows, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path, help="data directory, e.g. data/v0")
    parser.add_argument("--check", action="store_true",
                        help="do not write; exit 1 if the manifest is out of date or invalid")
    args = parser.parse_args(argv)

    rows, report = sync(args.root)
    manifest = args.root / MANIFEST_NAME
    current = read_manifest(manifest)
    out_of_date = report.has_changes or current != [
        {c: r.get(c, "") for c in COLUMNS} for r in sorted(rows, key=lambda r: r["doc_id"])
    ]

    for doc_id in report.added:
        print(f"added      {doc_id}")
    for doc_id in report.changed:
        print(f"changed    {doc_id}  (content differs; re-ingest)")
    for src, dst in report.moved:
        print(f"moved      {src} -> {dst}")
    for doc_id in report.removed:
        print(f"removed    {doc_id}")
    for doc_id in report.unreviewed:
        print(f"unreviewed {doc_id}  (fill in fields, then set reviewed=true)")
    for err in report.errors:
        print(f"error      {err}", file=sys.stderr)

    if args.check:
        if out_of_date:
            print(f"{manifest} is out of date; run without --check", file=sys.stderr)
        return 1 if out_of_date or report.errors else 0

    if out_of_date:
        write_manifest(manifest, rows)
        print(f"wrote {manifest} ({len(rows)} documents)")
    else:
        print(f"{manifest} is up to date ({len(rows)} documents)")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
