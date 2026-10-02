#!/usr/bin/env python3
"""Render reviewed portfolio plans/scenes locally. No model or network calls."""

from __future__ import annotations

import argparse
import base64
import html
import json
import math
import re
import sys
from pathlib import Path

from project import project_root, read_json, within, write_json


def need(condition, message):
    if not condition:
        raise ValueError(message)


def escape(value):
    return html.escape(str(value), quote=True)


def color(value, *, nullable=False):
    need((nullable and value is None) or (isinstance(value, str) and re.fullmatch(r"#[a-fA-F0-9]{6}", value)), "Colours must use #RRGGBB.")
    return value


def number(value, name, *, minimum=0):
    need(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= minimum, f"Invalid {name}.")
    return value


def font(value):
    need(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9 _.,'\-]+", value), "Use a plain local font-family name.")
    return value


def bilingual(value, name):
    need(isinstance(value, dict) and all(isinstance(value.get(key), str) and value[key].strip() for key in ("en", "zh")), f"{name} needs English and Chinese.")
    return value


def pair(value):
    return f'<div class="pair"><div lang="en">{escape(value["en"])}</div><div lang="zh">{escape(value["zh"])}</div></div>'


def box(value, canvas, *, line=False):
    for key in ("x", "y", "width", "height"):
        number(value.get(key), key, minimum=0)
    need(value["width"] > 0 or (line and value["height"] > 0), "Elements need positive dimensions.")
    need(value["height"] > 0 or (line and value["width"] > 0), "Elements need positive dimensions.")
    need(value["x"] + value["width"] <= canvas["width"] and value["y"] + value["height"] <= canvas["height"], "An element leaves the approved canvas.")


def image_data(root, name):
    path = within(root, name)
    need(path.is_file() and path.stat().st_size <= 32 * 1024 * 1024, "Use an existing local image no larger than 32 MiB.")
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif data.startswith((b"GIF87a", b"GIF89a")):
        mime = "image/gif"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ValueError("Existing images must be PNG, JPEG, GIF or WebP.")
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def check_base(root, data, key):
    need(isinstance(data, dict) and data.get("schemaVersion") == 1, "Use schemaVersion 1.")
    project = read_json(root / "project.json")
    need(data.get("projectSlug") == project["projectSlug"], "Plan/scene belongs to a different project.")
    need(isinstance(data.get("version"), str) and data["version"].strip(), "A plan/scene version is required.")
    canvas = data.get("canvas")
    need(isinstance(canvas, dict), "Canvas dimensions are required.")
    for name in ("width", "height"):
        need(isinstance(canvas.get(name), int) and not isinstance(canvas[name], bool) and canvas[name] > 0, "Canvas dimensions must be positive integers.")
    if canvas != {"width": 5120, "height": 1600}:
        need(isinstance(data.get("canvasOverride"), str) and data["canvasOverride"].strip(), "Alternate dimensions need the student's request in canvasOverride.")
    pages = data.get(key)
    need(isinstance(pages, list) and len(pages) > 0, f"{key} must contain the complete page list.")
    expected = project["fields"]["delivery.plannedPages"]["value"]
    if len(pages) != expected or not 4 <= len(pages) <= 15:
        need(isinstance(data.get("countOverride"), str) and data["countOverride"].strip(), "Count must match intake or have an explicit countOverride.")
    need([page.get("number") for page in pages] == list(range(1, len(pages) + 1)), "Pages must be consecutively numbered.")
    copy_path = within(root, data.get("copyPath", "copy.json"))
    library = read_json(copy_path)
    need(isinstance(library, dict) and library and all(isinstance(k, str) and k and isinstance(v, str) and v.strip() for k, v in library.items()), "Canonical copy must be a nonempty object of exact strings.")
    return canvas, library


def check_review(root, plan):
    canvas, library = check_base(root, plan, "pages")
    direction = plan.get("direction")
    need(isinstance(direction, dict), "A visual direction is required.")
    for key in ("title", "rationale", "devices"):
        bilingual(direction.get(key), "direction." + key)
    need(isinstance(direction.get("palette"), list) and len(direction["palette"]) >= 2, "Show multiple role-based palette colours.")
    for swatch in direction["palette"]:
        bilingual(swatch.get("role"), "Palette role")
        color(swatch.get("hex"))
    need(isinstance(direction.get("typography"), list) and len(direction["typography"]) >= 2, "Show display and supporting typography.")
    for item in direction["typography"]:
        bilingual(item.get("role"), "Typography role")
        font(item.get("family"))
        need(isinstance(item.get("sample"), str) and item["sample"].strip(), "Typography needs a sample.")
    images = direction.get("images", [])
    need(isinstance(images, list), "Style images must be a list.")
    if not images:
        bilingual(direction.get("imagesUnavailable"), "Explain unavailable style images")
    for image in images:
        bilingual(image.get("caption"), "Style image caption")
        image_data(root, image.get("path"))
    ids = set()
    used_copy = set()
    for page in plan["pages"]:
        for key in ("title", "purpose", "readingPath"):
            bilingual(page.get(key), "Page " + key)
        density = page.get("density", {})
        need(all(isinstance(density.get(k), int) and not isinstance(density[k], bool) and density[k] >= 0 for k in ("bodyWords", "imagePlacements", "detailViews")), "State honest page density budgets.")
        regions = page.get("regions")
        need(isinstance(regions, list) and regions, "Each page needs meaningful wireframe regions.")
        need(sorted(region.get("order", 0) for region in regions) == list(range(1, len(regions) + 1)), "Region reading orders must be consecutive.")
        for region in regions:
            identity = region.get("id")
            need(isinstance(identity, str) and identity and identity not in ids, "Region IDs must be unique.")
            ids.add(identity)
            need(region.get("kind") in ("text", "image", "mixed", "detail"), "Unknown region kind.")
            for key in ("label", "summary"):
                bilingual(region.get(key), "Region " + key)
            box(region.get("box", {}), canvas)
            need(isinstance(region.get("copyIds"), list) and isinstance(region.get("mediaIds"), list), "Regions need copyIds and mediaIds.")
            need(region["copyIds"] or region["mediaIds"], "Wireframe regions must bind content.")
            for identity in region["copyIds"]:
                need(identity in library, "Unknown canonical copy ID: " + str(identity))
                used_copy.add(identity)
    need(used_copy == set(library), "Every canonical copy ID must be placed in the page plan.")
    return canvas, library


def wireframe(page, canvas):
    output = [f'<svg class="wireframe" viewBox="0 0 {canvas["width"]} {canvas["height"]}" role="img" aria-label="Page {page["number"]} wireframe">']
    colors = {"text": "#eeebfc", "image": "#e1ecf3", "mixed": "#f3e5db", "detail": "#e6edde"}
    for region in page["regions"]:
        b = region["box"]
        output.append(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["width"]}" height="{b["height"]}" rx="12" fill="{colors[region["kind"]]}" stroke="#c4bed2" stroke-width="4"/>')
        output.append(f'<text x="{b["x"]+24}" y="{b["y"]+65}" fill="#393342" font-family="Arial,sans-serif" font-size="44">{region["order"]} · {escape(region["label"]["en"])}</text>')
        output.append(f'<text x="{b["x"]+24}" y="{b["y"]+120}" fill="#6d667a" font-family="Arial,sans-serif" font-size="32">{escape(region["label"]["zh"])}</text>')
    return "".join(output) + "</svg>"


def review_html(root, plan):
    canvas, library = check_review(root, plan)
    direction = plan["direction"]
    body = ['<header><div class="eyebrow">Project to Portfolio · Planning review</div><h1>Page structure & visual direction<br><span lang="zh">页面结构与视觉方向</span></h1><p>Review every page before the HTML sample. Opening this file records no approval.<br>请在 HTML 样稿前查看所有页面；打开文件不会记录批准。</p></header>']
    body.append('<section><h2>Intended style / 预期风格</h2>' + pair(direction["title"]) + pair(direction["rationale"]))
    body.append('<div class="swatches">')
    for swatch in direction["palette"]:
        body.append(f'<div><i style="background:{swatch["hex"]}"></i>{pair(swatch["role"])}<code>{swatch["hex"]}</code></div>')
    body.append('</div><div class="type-samples">')
    for item in direction["typography"]:
        body.append(f'<div>{pair(item["role"])}<p style="font-family:{escape(item["family"])}">{escape(item["sample"])}</p><small>{escape(item["family"])}</small></div>')
    body.append('</div><div class="image-samples">')
    for image in direction.get("images", []):
        body.append(f'<figure><img src="{image_data(root,image["path"])}" alt="{escape(image["caption"]["en"])}"><figcaption>{pair(image["caption"])}</figcaption></figure>')
    body.append('</div>' + pair(direction.get("imagesUnavailable", {"en": "", "zh": ""})) + pair(direction["devices"]) + '</section>')
    for page in plan["pages"]:
        d = page["density"]
        body.append(f'<section><div class="eyebrow">Page {page["number"]:02d}</div><h2>{escape(page["title"]["en"])} / {escape(page["title"]["zh"])}</h2>{pair(page["purpose"])}{wireframe(page,canvas)}')
        body.append('<div class="regions">')
        for region in sorted(page["regions"], key=lambda item: item["order"]):
            body.append(f'<div><strong>{region["order"]} · {escape(region["label"]["en"])} / {escape(region["label"]["zh"])}</strong>{pair(region["summary"])}<small>{escape(", ".join(region["copyIds"]+region["mediaIds"]))}</small></div>')
        body.append('</div><h3>Reading path / 阅读顺序</h3>' + pair(page["readingPath"]))
        body.append(f'<p class="budget">Planned budgets / 计划密度 · {d["bodyWords"]} body words / 正文字数 · {d["imagePlacements"]} image placements / 图片放置 · {d["detailViews"]} explanatory details / 说明细节</p></section>')
    body.append('<details class="copy"><summary>Exact canonical copy / 准确的最终文案</summary>')
    for identity, text in library.items():
        body.append(f'<div><code>{escape(identity)}</code><p>{escape(text)}</p></div>')
    body.append('</details>')
    css = '*{box-sizing:border-box}body{margin:0;background:#f7f6fc;color:#272333;font:16px/1.6 system-ui,-apple-system,sans-serif}main{max-width:1380px;margin:auto;padding:48px 32px 80px}header{max-width:850px;margin-bottom:42px}h1{font-size:38px;line-height:1.15;letter-spacing:-1.2px}h1 span{font-size:28px;color:#6d667a}h2{font-size:25px;letter-spacing:-.6px}h3{font-size:14px}.eyebrow{font-size:11px;font-weight:750;letter-spacing:1.4px;text-transform:uppercase;color:#6855e2}section{background:white;border:1px solid #e3deed;border-radius:18px;padding:28px;margin:25px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin:12px 0}.pair [lang=zh]{color:#6d667a}.swatches,.type-samples,.image-samples{display:flex;flex-wrap:wrap;gap:24px;margin:24px 0}.swatches>div{min-width:130px;max-width:210px}.swatches i{display:block;height:65px;border:1px solid #e3deed;border-radius:8px}.swatches .pair{display:block;font-size:12px}.type-samples>div{flex:1;min-width:250px;background:#f7f6fc;padding:16px;border-radius:10px}.type-samples p{font-size:25px;line-height:1.3}.type-samples .pair{font-size:12px}.image-samples figure{margin:0;flex:1;min-width:200px;max-width:350px}.image-samples img{width:100%;height:180px;object-fit:contain;background:#f7f6fc;border-radius:8px}.image-samples figcaption{font-size:12px}.wireframe{width:100%;border:1px solid #e3deed;background:#fcfbff;margin:20px 0}.regions{display:grid;grid-template-columns:repeat(2,1fr);gap:20px}.regions>div{padding:15px;border-left:3px solid #e3deed}.regions strong{font-size:14px}.regions .pair{font-size:13px;display:block}.regions small,small{overflow-wrap:anywhere;color:#6d667a}.budget{font-size:12px;color:#6d667a}.copy{padding:24px;background:white;border:1px solid #e3deed;border-radius:12px}.copy summary{cursor:pointer;min-height:44px}.copy p{white-space:pre-wrap}code{font:12px ui-monospace,monospace}@media(max-width:650px){main{padding:25px 16px}section{padding:20px}.pair,.regions{grid-template-columns:1fr;gap:8px}h1{font-size:30px}h1 span{font-size:23px}.wireframe{min-height:130px}.type-samples>div{min-width:200px}}'
    return f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(plan["projectSlug"])} · Page review</title><style>{css}</style><main>{"".join(body)}</main></html>'


def check_scene(root, scene):
    canvas, library = check_base(root, scene, "spreads")
    seen = set()
    used_copy = set()
    for spread in scene["spreads"]:
        need(isinstance(spread.get("name"), str) and spread["name"].strip(), "Each spread needs a name.")
        color(spread.get("background"))
        elements = spread.get("elements")
        need(isinstance(elements, list) and elements, "Each spread needs semantic elements.")
        page_copy = {element.get("copyId") for element in elements if element.get("type") == "text"}
        for element in elements:
            identity, kind = element.get("id"), element.get("type")
            need(isinstance(identity, str) and identity and identity not in seen, "Scene element IDs must be unique.")
            seen.add(identity)
            need(kind in ("text", "rect", "ellipse", "line", "polygon", "image"), "Unsupported scene element type.")
            box(element, canvas, line=kind == "line")
            if "opacity" in element:
                number(element["opacity"], "opacity")
                need(element["opacity"] <= 1, "Opacity must be from zero to one.")
            if kind == "text":
                need(element.get("copyId") in library, "Every text element needs an exact canonical copy ID.")
                used_copy.add(element["copyId"])
                font(element.get("fontFamily", "Arial"))
                number(element.get("fontSize", 40), "fontSize", minimum=1)
                color(element.get("color", "#202025"))
                need(element.get("fontWeight", 400) in range(100, 1000, 100), "Use a numeric font weight from 100 to 900.")
                need(element.get("fontStyle", "normal") in ("normal", "italic"), "Unknown font style.")
                need(element.get("align", "left") in ("left", "center", "right", "justify"), "Unknown text alignment.")
                number(element.get("lineHeight", 1.2), "lineHeight", minimum=0.5)
                number(element.get("letterSpacing", 0), "letterSpacing", minimum=-20)
            elif kind == "image":
                placeholder = element.get("placeholderCopyId")
                need(element.get("replaceable") is True and placeholder in library, "Images need a replaceable record and canonical description.")
                text = library[placeholder]
                need(text.startswith("*") and text.endswith("*") and len(text) > 2 and placeholder in page_copy, "Every image description needs literal stars and visible text on its spread.")
                need(element.get("fit", "cover") in ("cover", "contain"), "Image fit must be cover or contain.")
                if element.get("assetPath") is not None:
                    image_data(root, element["assetPath"])
            else:
                color(element.get("fill"), nullable=True)
                if "stroke" in element:
                    color(element["stroke"])
                number(element.get("strokeWidth", 1), "strokeWidth")
                number(element.get("radius", 0), "radius")
                if kind == "line":
                    need("stroke" in element, "A line needs its stroke colour.")
                if kind == "polygon":
                    points = element.get("points")
                    need(isinstance(points, list) and len(points) >= 3, "A polygon needs at least three local points.")
                    for point in points:
                        need(isinstance(point, list) and len(point) == 2, "Polygon points use [x,y].")
                        number(point[0], "point x")
                        number(point[1], "point y")
                        need(point[0] <= element["width"] and point[1] <= element["height"], "Polygon points leave their bounding box.")
    need(used_copy == set(library), "Every canonical copy ID must appear in the completed scene.")
    return canvas, library


def element_html(root, element, library):
    e, kind = element, element["type"]
    css = f'position:absolute;left:{e["x"]}px;top:{e["y"]}px;width:{e["width"]}px;height:{e["height"]}px;opacity:{e.get("opacity",1)};'
    attr = f'data-element-id="{escape(e["id"])}"'
    if kind == "text":
        css += f'font-family:{e.get("fontFamily","Arial")};font-size:{e.get("fontSize",40)}px;font-weight:{e.get("fontWeight",400)};font-style:{e.get("fontStyle","normal")};color:{e.get("color","#202025")};line-height:{e.get("lineHeight",1.2)};letter-spacing:{e.get("letterSpacing",0)}px;text-align:{e.get("align","left")};white-space:pre-wrap;overflow-wrap:break-word;'
        return f'<div {attr} data-copy-id="{escape(e["copyId"])}" style="{escape(css)}">{escape(library[e["copyId"]])}</div>'
    if kind == "image":
        if e.get("assetPath") is not None:
            return f'<img {attr} data-replaceable="true" alt="{escape(library[e["placeholderCopyId"]])}" src="{image_data(root,e["assetPath"])}" style="{escape(css+"object-fit:"+e.get("fit","cover")+";")}">'
        return f'<div {attr} data-replaceable="true" role="img" aria-label="{escape(library[e["placeholderCopyId"]])}" style="{escape(css)}background:#eeeaf6;border:2px dashed #b2a8ce;"></div>'
    fill, stroke, stroke_width = e.get("fill") or "none", e.get("stroke", "none"), e.get("strokeWidth", 1)
    if kind in ("rect", "ellipse"):
        radius = "50%" if kind == "ellipse" else str(e.get("radius", 0)) + "px"
        css += f'background:{fill if fill != "none" else "transparent"};border:{stroke_width}px solid {stroke if stroke != "none" else "transparent"};border-radius:{radius};'
        return f'<div {attr} style="{escape(css)}"></div>'
    if kind == "line":
        # Give a zero-height/width line a paintable SVG viewport without changing its endpoints.
        svg_css = css.replace(f'width:{e["width"]}px;', f'width:{max(1,e["width"])}px;').replace(f'height:{e["height"]}px;', f'height:{max(1,e["height"])}px;') + 'overflow:visible;'
        shape = f'<line x1="0" y1="0" x2="{e["width"]}" y2="{e["height"]}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
        return f'<svg {attr} style="{escape(svg_css)}">{shape}</svg>'
    points = " ".join(f"{point[0]},{point[1]}" for point in e["points"])
    return f'<svg {attr} style="{escape(css)}overflow:visible;"><polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/></svg>'


def spread_html(root, spread, canvas, library):
    elements = "".join(element_html(root, element, library) for element in spread["elements"])
    css = '*{box-sizing:border-box}body{margin:0;background:#e9e6ee;font-family:system-ui,sans-serif}.toolbar{position:sticky;top:0;z-index:10;background:white;border-bottom:1px solid #dad4e5;padding:9px 16px;display:flex;align-items:center;gap:18px;font-size:12px;min-height:44px}.toolbar a{color:#6855e2;text-decoration:none}.toolbar button{border:1px solid #dad4e5;background:white;border-radius:6px;padding:6px 10px;min-height:30px;cursor:pointer}.viewport{margin:16px;position:relative}.spread{position:absolute;left:0;top:0;transform-origin:top left;overflow:hidden}button:focus-visible,a:focus-visible{outline:3px solid #b2a5ff}@media print{.toolbar{display:none}.viewport{margin:0}.spread{transform:none!important;position:relative}}'
    script = f'let native=false;const frame=document.querySelector(".spread"),view=document.querySelector(".viewport"),button=document.getElementById("zoom");function resize(){{const scale=native?1:Math.min(1,(window.innerWidth-32)/{canvas["width"]});frame.style.transform=`scale(${{scale}})`;view.style.width=`${{{canvas["width"]}*scale}}px`;view.style.height=`${{{canvas["height"]}*scale}}px`;button.textContent=native?"Fit to window":"Read at 1:1"}}button.addEventListener("click",()=>{{native=!native;resize()}});window.addEventListener("resize",resize);resize();'
    return f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(spread["name"])}</title><style>{css}</style><div class="toolbar"><a href="index.html">All spreads</a><strong>{spread["number"]:02d} · {escape(spread["name"])}</strong><button id="zoom">Read at 1:1</button></div><div class="viewport"><main class="spread" data-spread="{spread["number"]}" style="width:{canvas["width"]}px;height:{canvas["height"]}px;background:{spread["background"]}">{elements}</main></div><script>{script}</script></html>'


def render_spreads(root, scene, *, sample=False):
    canvas, library = check_scene(root, scene)
    spreads = scene["spreads"][:1] if sample else scene["spreads"]
    files = {f'spread-{page["number"]:02d}.html': spread_html(root, page, canvas, library) for page in spreads}
    cards = []
    for page in spreads:
        link = f'spread-{page["number"]:02d}.html'
        cards.append(f'<section><div><h2>{page["number"]:02d} · {escape(page["name"])}</h2><a href="{link}">Open spread / 查看跨页 ↗</a></div><iframe src="{link}" loading="lazy" title="{escape(page["name"])}"></iframe></section>')
    mode = "HTML sample" if sample else "Complete HTML batch"
    css = '*{box-sizing:border-box}body{margin:0;background:#f7f6fc;color:#272333;font-family:system-ui,sans-serif}main{max-width:1500px;margin:auto;padding:32px 22px 70px}h1{font-size:32px;letter-spacing:-1px}p{color:#6d667a}section{margin:28px 0;background:white;border:1px solid #e3deed;border-radius:12px;overflow:hidden}section>div{display:flex;gap:14px;align-items:center;justify-content:space-between;padding:16px 20px}h2{font-size:16px;margin:0}a{font-size:12px;color:#6855e2}iframe{display:block;border:0;width:100%;height:calc((100vw - 88px) * .3125 + 70px);max-height:520px;min-height:200px}@media(max-width:600px){main{padding:24px 14px}section>div{padding:12px;align-items:start;flex-direction:column}h1{font-size:26px}}'
    files["index.html"] = f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(scene["projectSlug"])} · {mode}</title><style>{css}</style><main><h1>{escape(scene["projectSlug"])} · {mode}</h1><p>Project to Portfolio · {len(spreads)} of {len(scene["spreads"])} spreads · {canvas["width"]} × {canvas["height"]} · {escape(scene["version"])}</p>{"".join(cards)}</main></html>'
    native = json.loads(json.dumps(scene))
    native["exportedSpreadCount"] = len(spreads)
    native["spreads"] = native["spreads"][:len(spreads)]
    for page in native["spreads"]:
        for element in page["elements"]:
            if element["type"] == "text":
                element["text"] = library[element["copyId"]]
            if element["type"] == "image":
                element["description"] = library[element["placeholderCopyId"]]
                element["sourceImageData"] = image_data(root, element["assetPath"]) if element.get("assetPath") is not None else None
    native["canonicalCopy"] = library
    files["native-scene.json"] = json.dumps(native, ensure_ascii=False, indent=2) + "\n"
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("review", "spreads"):
        command = sub.add_parser(name)
        command.add_argument("--project", required=True)
        command.add_argument("--output", required=True, help="New project-relative artifact path")
        if name == "review":
            command.add_argument("--plan", required=True)
        else:
            command.add_argument("--scene", required=True)
            command.add_argument("--sample", action="store_true")
    args = parser.parse_args()
    try:
        root = project_root(args.project)
        output = within(root, args.output)
        need(not output.exists(), "Output already exists; choose a new revision path.")
        if args.command == "review":
            plan = read_json(within(root, args.plan))
            result = review_html(root, plan)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(result, encoding="utf-8")
            report = {"review": str(output), "pageCount": len(plan["pages"])}
        else:
            scene = read_json(within(root, args.scene))
            files = render_spreads(root, scene, sample=args.sample)
            output.mkdir(parents=True)
            for name, text in files.items():
                (output / name).write_text(text, encoding="utf-8")
            report = {"preview": str(output / "index.html"), "renderedSpreadCount": len(files)-2,
                      "plannedSpreadCount": len(scene["spreads"]), "nativeScene": str(output / "native-scene.json")}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
