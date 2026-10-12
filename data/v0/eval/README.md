# Evaluation

`questions.jsonl` is the hand-labelled gold set: one question per line.

## Fields

| Field | Meaning |
|---|---|
| `id` | Stable question id (`q01`, ...) |
| `intent` | `lookup`, `compare`, `trend` or `qualitative` |
| `question` | The user question |
| `history` | Optional prior turns for follow-up questions |
| `companies`, `years` | Expected routing output of the Query Analyzer |
| `answer.value` | Expected answer; `null` means the system should answer N/A |
| `answer.unit` | Unit of numeric answers (e.g. `USD million`) |
| `answer.details` / `answer.key_points` | Per-company/per-year values, or facts a free-text answer must contain |
| `tolerance` | Relative tolerance for numeric match (`0.005` = 0.5%) |
| `sources` | Every location that contains the answer; any hit counts for recall |
| `notes` | Why the question is tricky |

`doc` is the path relative to `data/v0/` (e.g. `Ford/Ford_Annual_Report_2022.pdf`).

A PDF source has two page numbers:

- `page`: physical PDF page, 1-indexed. Used for retrieval metrics, since parsers and the index work on physical pages.
- `printed_page`: the number printed on the page. Shown to users in citations, since that is what they look up. It is a string because printed labels are not always numeric or unique, and `null` when the page has no printed number.

## Corpus notes

What we have is what we use:

- BMW 2021 is the BMW Group Report (excerpt). BMW 2022/2023 are reports of BMW Finance N.V., a financing subsidiary, not BMW Group.
- Tesla has only 2022 and 2023 reports (10-K excerpts); the 2022 report contains 2021 comparatives. Printed page = physical page + 29 (2022) / + 30 (2023).
- `news.pdf` holds 20 short, undated, fictional news articles (no companies); questions on them have empty `companies`/`years`. `news.docx` has the same content and is not used in V0 (DOCX support is planned for V2). `news.pdf` has no printed page numbers, and page 8 is blank.
- Ford changed segments in 2023 (Ford Blue / Model e / Pro replace Automotive).
