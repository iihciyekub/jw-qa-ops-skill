# Answer Schema

Use this schema when the skill answers questions from the knowledge base. The goal is to keep answers readable in plain chat, renderable in frontend clients, and traceable to evidence.

## Design Rules

- Always produce a human-readable Markdown answer.
- Also structure the same answer into lightweight render blocks for frontend display.
- Keep citations separate from prose so the UI can style them consistently.
- If evidence is weak, say so in both Markdown and blocks.
- Apply strict anonymization before returning any user-facing text. Company, department, app, platform, bot, generated-by, watermark, and signature names must be replaced with generic labels.
- In user-facing citations, show only an anonymized file name and location. Do not show full or relative source paths in `answer_md`, `plain_text`, citation labels, captions, or visible blocks.
- When visual evidence is relevant, include image blocks or a compact image gallery, but keep captions and source labels anonymized.

## Privacy Labels

Use these labels consistently in `answer_md`, `plain_text`, `blocks`, citation display labels, previews, and table cells:

- Company, organization, supplier, customer, or partner: `匿名组织`
- Brand: `匿名品牌`
- Department, team, center, office, or business unit: `相关部门`
- App, system, platform, workflow, or bot: `匿名系统`
- Signature, watermark, generated-by footer, or source footer: `匿名署名`

Raw source paths may remain in machine-readable `citations.path` and image `path` fields for traceability or rendering, but visible citation labels should be anonymized file names only.

## Recommended Response Object

```json
{
  "title": "string",
  "plain_text": "string",
  "answer_md": "string",
  "blocks": [
    { "type": "summary", "text": "string" },
    { "type": "paragraph", "text": "string" },
    { "type": "bullets", "items": ["string"] },
    {
      "type": "navigation",
      "title": "string",
      "items": [
        {
          "label": "string",
          "query": "string",
          "reason": "string",
          "source_category": "string"
        }
      ]
    },
    {
      "type": "citations",
      "items": [
        {
          "path": "string",
          "location": "string",
          "label": "string",
          "display_filename": "string"
        }
      ]
    },
    {
      "type": "images",
      "title": "string",
      "items": [
        {
          "path": "string",
          "alt": "string",
          "caption": "string",
          "source_label": "string",
          "location": "string"
        }
      ]
    },
    { "type": "warning", "text": "string" },
    {
      "type": "table",
      "columns": ["string"],
      "rows": [["string"]]
    }
  ],
  "citations": [
    {
      "path": "string",
      "location": "string",
      "label": "string",
      "display_filename": "string"
    }
  ],
  "confidence": "high | medium | low"
}
```

## Minimum Required Fields

Even in a minimal answer, include these:

- `answer_md`
- `blocks`
- `citations`
- `confidence`

## Block Types

### `summary`

- Use for the short direct answer at the top.
- One block only in most responses.

### `paragraph`

- Use for explanatory prose.
- Keep each block to one idea.

### `bullets`

- Use for procedural steps, evidence lists, or extracted points.
- Avoid nested bullets.

### `navigation`

- Use when the user question is broad, underspecified, or likely to map to multiple knowledge areas.
- Present 3-6 concise directions the user can choose from.
- Each item should include:
  - `label`: short display text for the option
  - `query`: the follow-up retrieval query or refined user question
  - `reason`: why this direction is relevant
  - `source_category`: the likely business category, such as `quality_standard`, `defect_catalog`, or `finished_inspection_process`
- Do not treat navigation items as final evidence. Only cite sources that were retrieved or opened.

### `citations`

- Use for source display.
- Each item should include:
  - `path`
  - `location`
  - `label`
- `path` is machine-readable only. Do not print it in visible answer text.
- `label` and `display_filename` must be anonymized file names, not full paths.

### `images`

- Use when the user asks to see images, defect photos, screenshots, samples, appearance examples, or when images materially support the answer.
- Present only directly relevant images, usually 1-6 items.
- Each item should include:
  - `path`: absolute local path or renderable asset path for the UI
  - `alt`: short anonymized alt text
  - `caption`: what the image demonstrates
  - `source_label`: anonymized file name only
  - `location`: page, slide, section, or image number
- Do not display raw images that visibly contain company, brand, department, app, signature, watermark, email, or internal URL text. Redact/crop first when feasible; otherwise withhold the image and explain with a `warning` block.
- In Markdown rendering, image URLs may use absolute local paths when required by the client, but captions and citations must not repeat those paths.

### `warning`

- Use when OCR is missing, evidence is partial, or the source is image-heavy.

### `table`

- Use when the answer depends on tabular content such as AQL values or Excel extracts.

## Markdown Template

The `answer_md` field should usually follow this pattern:

```md
# 结论

...

## 依据

- ...
- ...

## 引用

- 来源：`匿名文件名.ext` (location)

## 备注

- 可选。只有在证据不足、OCR 缺失或信息存在限制时才写。
```

For ambiguous questions, use this navigation-first pattern instead:

```md
# 需要确认方向

你的问题可能对应以下几类资料：

1. ...
2. ...
3. ...

请确认你要查哪一类；如果其中一个方向明显最接近，我可以先按该方向给出临时结论。
```

When images are relevant, add this section before citations:

```md
## 相关图片

![匿名图片说明](/absolute/renderable/path/to/image.png)

图 1：图片说明。来源：匿名文件名.ext (location)
```

## Citation Rules

- Cite only files that were retrieved or opened.
- Visible citations must show only an anonymized file name, not the source path.
- Keep full source paths only in machine-readable fields such as `citations.path`.
- Prefer exact locations:
  - PDF: `p. 12`
  - PPT/PPTX: `slide 5`
  - Markdown/DOCX: `section: 标题`
  - Excel: `sheet: Summary`
- Keep the display label short and readable.

## Confidence Rules

- `high`
  - Direct match from processed chunks with consistent evidence
- `medium`
  - Partial evidence or answer assembled from multiple indirect chunks
- `low`
  - Weak evidence, OCR limitations, or inferred answer

## Notes For Frontend

- `answer_md` is the default rendering fallback.
- `blocks` should be treated as the richer display model.
- `citations` may be rendered separately as clickable source chips or a side panel.
