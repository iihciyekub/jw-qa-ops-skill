---
name: knowledge-ops
description: Structured ingestion, extraction, and Q&A from the packaged local knowledge base under this skill's references/knowledge_base directory. Use when a user adds or asks about PPT/PPTX, Excel, PDF, Word, or Markdown files and wants them auto-classified, preprocessed, and cited without hallucination.
---

# Knowledge Ops

## Overview

This skill is QA-first. Answer user questions by extracting verifiable content from the packaged knowledge base and return structured, source-cited responses.

Use `raw` processing only when the user has added new source files or when coverage needs to be checked. Day-to-day QA should rely on `references/processed/`, `references/registry.jsonl`, and `references/knowledge_base/`, not on `references/raw/`.

## Skill Layout

Use this directory layout when resolving files:

```text
knowledge-ops/
├── SKILL.md
├── agents/openai.yaml
├── inbox/
├── scripts/
│   ├── ingest.py
│   ├── process_inbox.py
│   ├── retrieve.py
│   └── build_index.py
└── references/
    ├── development_memo.md
    ├── knowledge_index.md
    ├── raw/
    │   ├── source_manifest.json
    │   ├── source_index.json
    │   └── sources/
    ├── processed/
    ├── registry.jsonl
    ├── taxonomy.md
    └── knowledge_base/
        ├── data_structure.md
        └── ...
```

## Workflow

1. Default to QA over processed knowledge  
For normal question answering, start from `references/processed/`, `references/registry.jsonl`, and `references/knowledge_index.md`.

2. Ingest new files before QA when needed  
If the user adds new files into `inbox/`, run `python3 scripts/process_inbox.py --rebuild-index` first. If the user points to an external file path directly, run `python3 scripts/ingest.py --source <path> --rebuild-index`.

2a. Retained raw source workflow  
If the user stores source files under `references/raw/sources/`, keep those files in place and use `python3 scripts/process_raw.py` as the default source-sync entrypoint.
- Check-only is the default: inspect whether each raw source already has corresponding knowledge-base and processed outputs.
- `--apply --rebuild-index` applies configured rules while preserving the raw file.
- `python3 scripts/sync_raw_sources.py` remains the lower-level script behind `process_raw.py`.
- Use `references/raw/source_manifest.json` for special processors such as chapter-splitting defect-catalog DOCX files.

3. Clarify the question scope  
If the user request is vague (product type, process stage, defect name), ask a brief clarifying question before searching.

4. Retrieve from processed outputs first  
Start with `python3 scripts/retrieve.py --query "<question>"`. Back it up with `references/registry.jsonl`, `references/knowledge_index.md`, and `references/processed/<doc_id>/chunks.jsonl`. Use raw files only when cache is missing or evidence needs verification.

5. Extract evidence  
Capture the exact statements needed to answer the question. Track file path and location (page/slide/section heading).

6. Compose the response  
Summarize clearly, then list evidence with citations. If the answer is not present, say so and point to what was checked.

7. Format the answer for chat and frontend  
Produce `answer_md` plus a lightweight block structure that follows `references/answer_schema.md`. Keep Markdown as the fallback rendering format.

## Ingestion Rules

- Supported file types: `pdf`, `ppt`, `pptx`, `doc`, `docx`, `xls`, `xlsx`, `md`
- Business categories and target folders are defined in `references/taxonomy.md`
- New external files are copied into `references/knowledge_base/<category>/auto_ingested/`
- Retained raw source files stay under `references/raw/sources/`; do not delete or overwrite them during processing
- `references/raw/source_manifest.json` stores source-specific processing rules
- `references/raw/source_index.json` is the generated coverage report for raw sources and their downstream outputs
- Files dropped into `inbox/` should be processed with `scripts/process_inbox.py`, which ingests them and archives the originals under `inbox/archive/`
- Processed outputs are written to `references/processed/<doc_id>/`
- `references/registry.jsonl` is the machine-readable source of truth for ingestion status
- `scripts/retrieve.py` is the default QA entrypoint over processed chunks

## Extraction Guidance

Use the least invasive method that yields reliable text, and note when content appears only in images.

Preferred tools and approaches:
- Markdown: `rg` plus direct reading
- PDF: use the `pdf` skill for layout-sensitive extraction, otherwise `pdfplumber`
- DOCX: use `python-docx`
- PPT/PPTX: use `python-pptx`
- XLSX: parse workbook XML into sheet previews and CSV table caches
- Legacy `.ppt`: prefer the paired PDF if present
- Legacy `.xls`: treat as manual-review unless converted to `.xlsx`

If a file appears to be image-heavy (scanned PDF or image-only slides), state that OCR is required and ask the user whether to proceed.

## Response Format

Follow `references/answer_schema.md` as the response contract. The displayed Markdown should keep answers traceable and easy to verify.

Minimum sections in `answer_md`:

- `结论`: direct answer in 2-6 lines
- `依据`: short bullets summarizing the supporting points
- `引用`: one line per source with file path and location

Citation style examples:
- `來源: references/knowledge_base/Quality Standards/品質標準 260227.pdf (p. 12)`
- `來源: references/knowledge_base/Finished Product Inspection Process/BP-PACIQADT-001 4.8成品查貨流程  260227.ppt (slide 5)`
- `來源: references/knowledge_base/Defect Analysis Table/针织圆领/8-不对称问题/8-不对称问题.md (section: 檢驗要點)`

Never cite a file you did not open and verify.

## References

Key reference file:
- `references/knowledge_index.md` for the current inventory of knowledge-base files
- `references/knowledge_base/**/data_structure.md` for topic-level navigation before opening binary files
- `references/taxonomy.md` for routing and classification rules
- `references/answer_schema.md` for frontend-friendly response formatting
- `references/development_memo.md` for implementation notes and current limits
