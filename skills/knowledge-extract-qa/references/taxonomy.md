# Taxonomy

This skill classifies ingested documents along two axes.

## Technical File Type

- `pdf`
- `ppt`
- `pptx`
- `word`
- `excel`
- `markdown`

## Business Category

- `finished_inspection_process`
  - Typical folder: `references/knowledge_base/Finished Product Inspection Process`
  - Keywords: `成品查貨流程`, `成品查货流程`, `3.3a`, `3.3b`
- `semi_finished_inspection_process`
  - Typical folder: `references/knowledge_base/Semi-finished Product Inspection Process`
  - Keywords: `半成品查貨流程`, `半成品查货流程`, `4.7`
- `quality_standard`
  - Typical folder: `references/knowledge_base/Quality Standards`
  - Keywords: `品質標準`, `品质标准`, `AQL`, `抽样`
- `defect_catalog`
  - Typical folder: `references/knowledge_base/Defect Analysis Table`
  - Keywords: `Defect Analysis Table`, `疵點`, `疵点`, `缺陷`
- `inspection_guideline`
  - Typical folder: `references/knowledge_base/Product Inspection and Inventory Check Guidelines`
  - Keywords: `產品檢查及查貨工作指引`, `产品检查及查货工作指引`, `工作指引`
- `work_guideline`
  - Typical folder: `references/knowledge_base/Work guidelines`
  - Keywords: `品質保證部工作指引`, `品质保证部工作指引`
- `inspection_plan`
  - Typical folder: `references/knowledge_base/Order inspection plan development`
  - Keywords: `制定订单查货计划`, `inspection plan`
- `uncategorized`
  - Fallback when no rules match strongly enough

## Storage Conventions

- Raw files belong under `references/knowledge_base`.
- New external files are copied into a matching `auto_ingested/` folder under the target business directory.
- Processed outputs live under `references/processed/<doc_id>/`.
- Registry rows live in `references/registry.jsonl`.
