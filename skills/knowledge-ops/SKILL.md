---
name: knowledge-ops
description: Structured ingestion, extraction, and Q&A from the packaged local knowledge base under this skill's references/knowledge_base directory. Use when a user adds or asks about PPT/PPTX, Excel, PDF, Word, or Markdown files and wants them auto-classified, preprocessed, and cited without hallucination.
---

# Knowledge Ops

## Overview

This skill is QA-first. Answer user questions by extracting verifiable content from the packaged knowledge base and return structured, source-cited responses.

Use `raw` processing only when the user has added new source files or when coverage needs to be checked. Day-to-day QA should rely on `references/processed/`, `references/registry.jsonl`, and `references/knowledge_base/`, not on `references/raw/`.

## Highest Priority Privacy Filter

All user-facing answers must pass a strict anonymization filter before output. This rule has higher priority than citation fidelity, wording preservation, and source quotation.

Always anonymize:
- Company, organization, brand, supplier, customer, or partner names.
- Department, team, center, office, business unit, and functional group names.
- App, system, platform, bot, workflow, watermark, generated-by text, or signature names.
- Email-like identifiers, account names, internal URLs, and other source signatures if they appear in extracted text.

Use stable generic labels:
- Company or organization: `匿名组织`
- Brand: `匿名品牌`
- Department or team: `相关部门`
- App, system, platform, or bot: `匿名系统`
- Signature, watermark, or generated-by footer: `匿名署名`

Apply the filter to:
- Final prose answers
- Evidence excerpts and previews
- Navigation options
- Image captions, gallery titles, and visual evidence notes
- Tables and bullets
- Citation labels and displayed file titles
- Any text copied from `processed`, `knowledge_base`, or raw sources

Do not output raw company, department, app, or signature names even when they appear in retrieved chunks. If anonymization would make a citation path less readable, keep the machine-readable path only when needed for traceability, but use an anonymized display label in the answer.

For user-facing citations, display only the anonymized file name plus location. Do not show full or relative source paths in the `引用` section.

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

3a. Navigate ambiguous questions before answering  
If the user question is broad or could map to multiple knowledge areas, do not force a single answer too early. First provide a small navigation set, then ask the user to choose or confirm the intended direction.

Trigger navigation when:
- The query lacks product type, process stage, defect name, document category, or acceptance context.
- Retrieval results span multiple business categories or unrelated source folders.
- The top matches have similar scores but point to different topics.
- The user asks broad questions such as "怎么处理", "标准是什么", "有哪些", "流程是什么", or "这个可以接受吗".

Navigation response rules:
- Offer 3-6 likely directions as concise options.
- For each option, include the matched topic or source category in one short phrase.
- If one direction is clearly dominant, give a short provisional answer and still show related follow-up directions.
- If the answer would materially differ by direction, ask the user to choose before giving a final answer.
- Cite only retrieved or opened sources; do not cite a navigation option as evidence unless its source was checked.

4. Retrieve from processed outputs first  
Start with `python3 scripts/retrieve.py --query "<question>"`. Back it up with `references/registry.jsonl`, `references/knowledge_index.md`, and `references/processed/<doc_id>/chunks.jsonl`. Use raw files only when cache is missing or evidence needs verification.

5. Extract evidence  
Capture the exact statements needed to answer the question. Track file path and location (page/slide/section heading).

5a. Present visual evidence when the answer depends on images  
When the user asks to see images, defect photos, screenshots, samples, appearance examples, or when the directly relevant document contains images that materially support the answer, check the matched document for image references.
- Markdown defect-catalog files may reference images as `images/media/...`; resolve them relative to the source Markdown file under `references/knowledge_base/`.
- Present up to 3-6 directly relevant images, ordered by relevance to the answer.
- Use absolute local paths only inside machine-readable image fields or Markdown image URLs required for rendering; do not repeat full paths in captions or citations.
- Captions must explain what the image supports and must pass the privacy filter.
- If an image visibly contains company, brand, department, app, signature, watermark, email, or internal URL text, do not display the raw image. Redact/crop it first when feasible; otherwise describe the visual evidence and state that the image was withheld for privacy.
- For PDF or PPT/PPTX evidence where a single embedded image is not available, render the relevant page or slide image only when needed, then cite the source by anonymized file name and page/slide.
- If image-only evidence requires OCR to answer accurately, state that OCR is required before giving a final answer.

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
- `相关图片`: only when visual evidence is directly useful
- `引用`: one line per source with anonymized file name and location

Citation style examples:
- `來源: 匿名文件.pdf (p. 12)`
- `來源: 匿名流程文件.ppt (slide 5)`
- `來源: 8-不对称问题.md (section: 檢驗要點)`

Never cite a file you did not open and verify.

## References

Key reference file:
- `references/knowledge_index.md` for the current inventory of knowledge-base files
- `references/knowledge_base/**/data_structure.md` for topic-level navigation before opening binary files
- `references/taxonomy.md` for routing and classification rules
- `references/answer_schema.md` for frontend-friendly response formatting
- `references/development_memo.md` for implementation notes and current limits
