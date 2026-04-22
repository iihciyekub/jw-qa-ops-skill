# Raw Sources Workflow

本目录用于保留原始资料，不作为直接检索入口。

`knowledge-ops` 的主职责仍然是 QA 问答。`raw` 目录只是新增资料时的辅助入口，用于保留来源、检查覆盖状态、驱动必要的自动处理。

如果当前任务只是回答问题，默认不要先处理 `raw`，而应优先使用：

- `references/processed/`
- `references/registry.jsonl`
- `references/knowledge_index.md`
- `references/knowledge_base/`

## 目录约定

- `sources/`
  - 存放原始文件，按“一个来源目录 + 一个或多个原始文件”的方式组织
  - 建议目录名格式：`主题_日期_格式`
  - 例：`查貨AI疵點分析模塊思路_4月牛仔_20260417_docx`
- `source_manifest.json`
  - 存放特殊处理规则
  - 建议每条至少包含：`source_file`、`mode`、`note`
  - 对于普通 `pdf/doc/docx/ppt/pptx/xls/xlsx/md`，没有特殊规则时默认按 `direct_ingest` 处理
  - 对于疵点分析表这类需要拆章节的 `docx`，使用 `defect_catalog_docx_split`
- `source_index.json`
  - 自动生成的覆盖检查结果
  - 用来判断每个 raw 来源是否已经有对应的知识库文档、注册表条目和 processed 缓存

## 处理模式

- `direct_ingest`
  - 适用于普通文件
  - 保留 raw 原文件
  - 自动生成 `knowledge_base`、`registry.jsonl`、`processed/` 里的对应结果

- `defect_catalog_docx_split`
  - 适用于疵点分析表类 `docx`
  - 保留 raw 原文件
  - 自动拆成 `Defect Analysis Table/<品类>/章节目录/*.md` 和图片资源

- `linked_existing`
  - 适用于历史文件
  - 不重复生成新副本
  - 只建立 raw 与现有知识库目标之间的检查关系

## 日常命令

平时只在“新增了 raw 文件”或“怀疑某个 raw 还没入库”时使用下面命令。

检查当前 raw 覆盖状态：

```bash
python3 skills/knowledge-ops/scripts/process_raw.py
```

处理全部新加的 raw 文件并重建索引：

```bash
python3 skills/knowledge-ops/scripts/process_raw.py --apply --rebuild-index
```

只处理指定来源目录：

```bash
python3 skills/knowledge-ops/scripts/process_raw.py --apply --rebuild-index --source 查貨AI疵點分析模塊思路_4月牛仔_20260417_docx
```

强制重建：

```bash
python3 skills/knowledge-ops/scripts/process_raw.py --apply --force --rebuild-index
```

## 新增 raw 文件建议

1. 把新文件放进 `references/raw/sources/<你的来源目录>/`
2. 如果是普通文件，先直接运行检查和处理命令
3. 如果是特殊格式或需要拆章节的文档，在 `source_manifest.json` 中补规则
4. 处理后查看 `source_index.json` 是否为 `ok`

## 当前行为说明

- raw 原文件会保留，不会被脚本删除
- 自动检索仍然以 `references/knowledge_base`、`references/registry.jsonl`、`references/processed/` 为主
- `raw` 目录的职责是“保留来源 + 检查覆盖 + 驱动自动处理”
- 不要把 `raw` 流程当成日常 QA 主流程
