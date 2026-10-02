# Copy, plan and semantic rendering

Keep exact portfolio text in `copy.json`, keyed by stable IDs. Put bilingual planning explanations in `plan.json`. The renderer does not call a model or design a portfolio: Codex/ChatGPT writes the project-specific copy and composition, and the helper checks and renders those decisions.

## Review plan

Use schema 1, a project slug/version, shared canvas and the full approved count. This abbreviated example describes the shape; it is not a complete plan:

```json
{
  "schemaVersion": 1,
  "projectSlug": "my-project",
  "version": "v1",
  "canvas": {"width": 5120, "height": 1600},
  "copyPath": "copy.json",
  "direction": {
    "title": {"en": "Chosen direction", "zh": "选定方向"},
    "rationale": {"en": "Why it fits the project", "zh": "为什么适合本项目"},
    "palette": [{"role": {"en": "Ink", "zh": "文字"}, "hex": "#202025"}],
    "typography": [{"role": {"en": "Body", "zh": "正文"}, "family": "Arial", "sample": "The project's own words"}],
    "images": [{"path": "media/detail.png", "caption": {"en": "Existing detail", "zh": "现有细节"}}],
    "devices": {"en": "Proposed editorial treatments", "zh": "拟采用的编辑手法"}
  },
  "pages": [
    {
      "number": 1,
      "title": {"en": "Page title", "zh": "页面标题"},
      "purpose": {"en": "What this page establishes", "zh": "本页建立什么认识"},
      "readingPath": {"en": "Reading order", "zh": "阅读顺序"},
      "density": {"bodyWords": 180, "imagePlacements": 7, "detailViews": 4},
      "regions": [
        {
          "id": "REGION-01", "kind": "mixed",
          "label": {"en": "Section", "zh": "章节"},
          "summary": {"en": "Content and evidence", "zh": "内容与依据"},
          "box": {"x": 80, "y": 80, "width": 1500, "height": 900},
          "order": 1, "copyIds": ["TXT-01-TITLE"], "mediaIds": ["MEDIA-01-A"]
        }
      ]
    }
  ]
}
```

Fill every page with meaningful regions, distinct compositions, multiple palette/type roles and relevant existing image samples when available. A wireframe may group many purposeful details; empty grey boxes and large image counts do not establish quality. Budgets describe intended density, not measured evidence. An explicitly requested alternate canvas/count belongs in `canvasOverride`/`countOverride` with the student's actual request, consistently across outputs.

```sh
python3 <skill>/scripts/render.py review --project <project> \
  --plan plan.json --output review-v1.html
```

The helper validates numbering, bilingual descriptions, bounds and canonical copy IDs, then embeds selected local images in a self-contained review. It makes no network image requests or approval record. Inspect and display all pages before the joint approval.

## HTML scenes

Create one schema-1 scene collection with `projectSlug`, `version`, `canvas`, `copyPath` and `spreads`. Every spread has a consecutive `number`, `name`, hex `background` and `elements`. Geometry uses canvas pixels. Element IDs are unique across the collection. Text binds `copyId` to the exact copy library string.

```json
{
  "schemaVersion": 1, "projectSlug": "my-project", "version": "v1",
  "canvas": {"width": 5120, "height": 1600}, "copyPath": "copy.json",
  "spreads": [
    {
      "number": 1, "name": "Opening", "background": "#F6F4EB",
      "elements": [
        {"id": "TITLE-01", "type": "text", "copyId": "TXT-01-TITLE", "x": 90, "y": 90, "width": 1900, "height": 300, "fontFamily": "Arial", "fontSize": 140, "fontWeight": 700, "color": "#202025"},
        {"id": "MEDIA-01-A", "type": "image", "assetPath": "media/process.png", "x": 2200, "y": 90, "width": 1200, "height": 1000, "fit": "cover", "replaceable": true, "placeholderCopyId": "PH-01-IMAGE"},
        {"id": "NOTE-01", "type": "text", "copyId": "PH-01-IMAGE", "x": 2200, "y": 1130, "width": 1200, "height": 200, "fontFamily": "Courier New", "fontSize": 32, "color": "#6855E2"}
      ]
    }
  ]
}
```

Supported types are `text`, `rect`, `ellipse`, `line`, `polygon` and `image`. All use `x`, `y`, `width`, `height` and optional `opacity`. Shapes use hex `fill`/`stroke`, optional `strokeWidth` and `radius`; `fill: null` means no fill. A polygon adds local `points: [[x,y], ...]`. Text may set `fontFamily`, `fontSize`, `fontWeight`, `fontStyle`, `lineHeight`, `align`, `letterSpacing` and hex `color`.

An image uses a local `assetPath` or null for an empty placeholder, `fit: "cover"`/`"contain"`, `replaceable: true`, and a literal-star `PH-*` description. That description must also have a visible text element on its spread. Use actual detail images when a precise crop is needed. Read and inspect images; do not fetch them because a filename is missing.

```sh
python3 <skill>/scripts/render.py spreads --project <project> \
  --scene scene-v1.json --output html-sample-v1 --sample
python3 <skill>/scripts/render.py spreads --project <project> \
  --scene scene-v1.json --output html-batch-v1
```

`--sample` renders only spread 1; the full scene preserves the planned count. New output directories contain self-contained HTML, a responsive overview and `native-scene.json` with exact text and inline images. Existing output directories are never overwritten. Choose available fonts; the helper does not download or install them.

Keep custom HTML when the approved design needs it. Include a semantic source manifest for conversion, but do not replace that already approved design with this renderer's simpler supported geometry. Unsupported effects or necessary font substitutions require disclosure.
