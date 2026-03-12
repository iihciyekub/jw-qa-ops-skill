---
name: knowledge-extract-qa
description: Structured extraction and Q&A from the local knowledge base under /Users/yjli/PolyUWorkspace/ref_260214_jeanswest_skills/KNOWLEDGE. Use when a user asks to answer questions by locating, extracting, and citing content from PPT/PPTX, DOCX, PDF, or Markdown files, with evidence-based responses and no hallucination.
---

# Knowledge Extract Qa

## Overview

Answer user questions by extracting verifiable content from the local knowledge base and returning structured, source-cited responses. Allow light paraphrasing, but never invent details that are not present in the files.

## Workflow

1. Clarify the question scope  
If the user request is vague (product type, process stage, defect name), ask a brief clarifying question before searching.

2. Locate likely sources  
Start with `references/knowledge_index.md` and any `data_structure.md` files under `KNOWLEDGE/**/`. Use `rg` to search Markdown. For PPT/PDF/DOCX, open and extract text to confirm the relevant section.

3. Extract evidence  
Capture the exact statements needed to answer the question. Track file path and location (page/slide/section heading).

4. Compose the response  
Summarize clearly, then list evidence with citations. If the answer is not present, say so and point to what was checked.

## Extraction Guidance

Use the least invasive method that yields reliable text, and note when content appears only in images.

Preferred tools and approaches:
- Markdown: `rg` plus direct reading
- PDF: use the `pdf` skill for layout-sensitive extraction, otherwise `pdfplumber`
- DOCX: use `python-docx`
- PPT/PPTX: use `python-pptx`

If a file appears to be image-heavy (scanned PDF or image-only slides), state that OCR is required and ask the user whether to proceed.

## Response Format

Follow this structure to keep answers traceable and easy to verify:

- `结论`: direct answer in 2-6 lines
- `依据`: short bullets summarizing the supporting points
- `引用`: one line per source with file path and location

Citation style examples:
- `來源: /Users/.../品質標準.pdf (p. 12)`
- `來源: /Users/.../成品查貨流程V1.9.ppt (slide 5)`
- `來源: /Users/.../8-不對稱問題.md (section: 檢驗要點)`

Never cite a file you did not open and verify.

## References

Key reference file:
- `references/knowledge_index.md` for the current inventory of knowledge-base files
