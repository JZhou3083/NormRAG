# V0 data

Corpus for V0 development: automotive annual reports (BMW, Ford, Tesla) and a news file.
The gold question set is in [`eval/`](eval/README.md).

## Document registry: `manifest.csv`

One row per file. It is the single source of truth for document metadata; ingestion copies these fields onto every chunk so retrieval can filter by company and year.

Keep it in sync with the files using the registry script (never edit derived fields by hand):

```bash
PYTHONPATH=src python -m normrag.ingestion.registry data/v0          # sync and write
PYTHONPATH=src python -m normrag.ingestion.registry data/v0 --check  # CI: exit 1 if out of date or invalid
```

- Derived fields (`doc_id`, `pages`, `sha1`) are recomputed from the files on every run.
- Curated fields are kept as reviewed. New files get a best-effort guess from the filename (`<Company>_Annual_Report_<YYYY>.pdf`) with `enabled=false`, `reviewed=false`; fill in the rest, then set `reviewed=true` and `enabled=true`.
- A moved or renamed file is matched by `sha1` and keeps its curated fields. Changed content is reported so the document can be re-ingested.

| Column | Meaning |
|---|---|
| `doc_id` | Path relative to `data/v0/`; same key as `doc` in the gold set |
| `doc_type` | `annual_report` or `news` |
| `company` | Canonical company name used for routing (`BMW`, `Ford`, `Tesla`); empty for news |
| `entity` | Legal entity the report covers. BMW 2022/2023 are `BMW Finance N.V.`, not `BMW Group` |
| `report_year` | Fiscal year the report covers |
| `period_end` | End of the fiscal year |
| `currency` | Reporting currency |
| `pages` | Physical page count |
| `sha1` | SHA-1 of the file; detects changed files |
| `enabled` | `false` = registered but not ingested (e.g. DOCX until V2) |
| `reviewed` | `true` once a person has checked the curated fields; an enabled row must be reviewed |
| `notes` | Known quirks of the document |
