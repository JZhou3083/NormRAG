# V1 data

Enterprise RAG Challenge (ERC) datasets, used after V0 to measure improvements.
Source: https://github.com/trustbit/enterprise-rag-challenge (Apache 2.0).

| Folder | What | Gold answers |
|---|---|---|
| `round1/` | Round 1 (Sep 2024): 40 questions over 20 PDFs. `answers.json` has a `category` per question (`hallucination`, `tricky`, `compare`, `retrieval`). `dataset.csv` lists all 7,496 reports in the ERC pool (sha1 → company). | yes, `answers.json` |
| `round2/` | Round 2 (Feb 2025): 100 questions over 100 PDFs (`subset.csv`). `answers.json` maps question text → `{kind, answers, reference_pools}`; references are `sha1:page`. | yes, `answers.json` |
| `erc2_set/` | Round 2 questions + answers of the winning system (Ilya Rice), with o3-mini and Llama 70B. | no, use as a baseline |
| `test_set/` | 5 of the Round 1 PDFs + the winning pipeline's intermediate outputs (parsed reports, chunks). | no |

## PDFs

Not committed (gitignored). Download when V1 starts and place them in `data/v1/round1/pdfs/` and `data/v1/round2/pdfs/`:

- Round 1: `round1/pdfs/` in the source repo (20 files, ~82 MB)
- Round 2: `round2/pdfs/` in the source repo (100 files, ~529 MB)

## Page numbering

Page indices are not consistent across these files (the winning system's answers file is 0-indexed, its debug file 1-indexed). Check each source before comparing against `page` (1-indexed) in our own gold set.
