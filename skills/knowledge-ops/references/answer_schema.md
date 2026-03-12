# Answer Schema

Use this schema when the skill answers questions from the knowledge base. The goal is to keep answers readable in plain chat, renderable in frontend clients, and traceable to evidence.

## Design Rules

- Always produce a human-readable Markdown answer.
- Also structure the same answer into lightweight render blocks for frontend display.
- Keep citations separate from prose so the UI can style them consistently.
- If evidence is weak, say so in both Markdown and blocks.

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
      "type": "citations",
      "items": [
        {
          "path": "string",
          "location": "string",
          "label": "string"
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
      "label": "string"
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

### `citations`

- Use for source display.
- Each item should include:
  - `path`
  - `location`
  - `label`

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

- 来源：`path` (location)

## 备注

- 可选。只有在证据不足、OCR 缺失或信息存在限制时才写。
```

## Citation Rules

- Cite only files that were retrieved or opened.
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
