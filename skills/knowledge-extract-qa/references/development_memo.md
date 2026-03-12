# Development Memo

## 2026-03-12

### Goal

Upgrade `knowledge-extract-qa` from a read-on-demand skill into a preprocess-first skill that can absorb new files, classify them, cache extracted text, and answer faster from processed artifacts.

### Implemented

- Normalized the skill so the knowledge base lives inside `references/knowledge_base`.
- Added `scripts/ingest.py` for incremental ingestion and preprocessing.
- Added `scripts/process_inbox.py` so files dropped into `inbox/` can be ingested and archived in one step.
- Added `scripts/retrieve.py` so QA can search processed chunks before reopening raw files.
- Added `scripts/build_index.py` to regenerate `references/knowledge_index.md`.
- Added `references/taxonomy.md` to define file-type and business-category routing.
- Added `references/processed/` as the cache root and `references/registry.jsonl` as the machine-readable catalog.
- Added `inbox/` as the default staging area for future uploads.

### Verification

- Full ingest completed successfully against the current knowledge base.
- `references/registry.jsonl` contains 29 processed entries after the initial run.
- Smoke tests passed for `docx`, `pptx`, and `xlsx` extraction on temporary sample files.
- Retrieval checks passed for representative queries such as `成品查货流程 抽样 标准`, `AQL 2.5`, and `打褶问题 解决方法`.
- Inbox workflow now supports `drop file -> process_inbox -> archive original -> query processed cache`.
- Inbox verification confirmed that a test `.docx` was routed into the correct business folder, processed, archived from `inbox/`, and then removed after validation.

### Design Decisions

- Prefer cached processed outputs over reopening raw files during QA.
- Treat legacy `.ppt` as a special case and prefer a paired PDF when present.
- Keep classification rule-based for now because it is deterministic and cheap.
- Use stable `doc_id` values derived from source path identity so updates overwrite cleanly.
- Store chunks as JSONL for simple retrieval and later upgrade to embeddings if needed.

### Known Limits

- Legacy `.xls` is not parsed yet; conversion to `.xlsx` is the current fallback.
- Scanned PDFs and image-heavy slides are marked `needs_ocr` rather than silently hallucinated.
- Auto-routing of externally added files is based on keyword rules and may still need review for ambiguous documents.

### Next Upgrade Candidates

- Add OCR for scanned PDFs and image-only slides.
- Add richer Excel summarization with column statistics.
- Add automation to watch `inbox/` and ingest on a schedule.
