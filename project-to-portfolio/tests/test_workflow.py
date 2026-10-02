"""Behavior checks for local intake and portable portfolio artifacts."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO if (REPO / ".codex-plugin").exists() else REPO / "plugins" / "project-to-portfolio"
SCRIPTS = PLUGIN / "skills" / "project-to-portfolio" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import project
import render

PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000b49444154789c636000020000050001a5f645400000000049454e44ae426082")


def fixture(root):
    """A deliberately fictional process study; no student or publisher data."""
    project.initialize(root, "process-study")
    current = project.read_json(root / "project.json")
    fields = {}
    for key, question in project.question_map().items():
        if question.get("conditionalOnAI") or question["requiredFor"] == "preflight":
            continue
        value = 4 if question["kind"] == "number" else "No" if key == "ai.used" else "Fictional test response: " + question["label"]
        fields[key] = {"state": "confirmed", "value": value, "notes": ""}
    patch = {"schemaVersion": 1, "projectSlug": "process-study", "fields": fields}
    project.write_json(root / "selected-intake.json", patch)
    project.import_intake(root, root / "selected-intake.json")
    (root / "media").mkdir()
    (root / "media" / "detail.png").write_bytes(PNG)
    library = {}
    pages, spreads = [], []
    for n in range(1, 5):
        title, body, placeholder = f"TXT-{n:02d}-TITLE", f"TXT-{n:02d}-BODY", f"PH-{n:02d}-IMAGE"
        library[title] = ["Process Study", "A material question", "Trying an alternative", "What remains open"][n - 1]
        library[body] = "This is fictional test content, not a student's completed project.\nIt checks exact copy and editable source records."
        library[placeholder] = "*Image placeholder — replace with your own process detail*"
        # Different source positions demonstrate that the renderer respects authored scenes.
        shift = (n % 2) * 280
        pages.append({"number": n, "title": {"en": library[title], "zh": "测试页 " + str(n)},
                      "purpose": {"en": "Explain this stage of a fictional process study.", "zh": "说明虚构过程研究的这一阶段。"},
                      "readingPath": {"en": "Title → body → image detail", "zh": "标题 → 正文 → 图片细节"},
                      "density": {"bodyWords": 25, "imagePlacements": 1, "detailViews": 1},
                      "regions": [
                          {"id": f"REGION-{n}-TEXT", "kind": "text", "label": {"en": "Context", "zh": "背景"},
                           "summary": {"en": "Exact project copy", "zh": "准确的项目文案"}, "box": {"x": 100 + shift, "y": 100, "width": 2000, "height": 1100},
                           "order": 1, "copyIds": [title, body], "mediaIds": []},
                          {"id": f"REGION-{n}-MEDIA", "kind": "image", "label": {"en": "Process detail", "zh": "过程细节"},
                           "summary": {"en": "Replaceable detail and its caption", "zh": "可替换细节及其说明"}, "box": {"x": 2600, "y": 200, "width": 1800, "height": 1100},
                           "order": 2, "copyIds": [placeholder], "mediaIds": [f"MEDIA-{n}"]}
                      ]})
        spreads.append({"number": n, "name": library[title], "background": "#F6F4EB", "elements": [
            {"id": f"TITLE-{n}", "type": "text", "copyId": title, "x": 100 + shift, "y": 120, "width": 2000, "height": 300, "fontSize": 130, "fontWeight": 700, "color": "#272333"},
            {"id": f"BODY-{n}", "type": "text", "copyId": body, "x": 100 + shift, "y": 600, "width": 2000, "height": 500, "fontSize": 55, "color": "#272333"},
            {"id": f"MEDIA-{n}", "type": "image", "assetPath": "media/detail.png", "x": 2600, "y": 200, "width": 1700, "height": 850, "fit": "contain", "replaceable": True, "placeholderCopyId": placeholder},
            {"id": f"NOTE-{n}", "type": "text", "copyId": placeholder, "x": 2600, "y": 1120, "width": 1900, "height": 240, "fontSize": 35, "fontFamily": "Courier New", "color": "#6855E2"},
            {"id": f"RULE-{n}", "type": "line", "x": 100, "y": 1450, "width": 4700, "height": 0, "stroke": "#272333", "strokeWidth": 4}
        ]})
    direction = {"title": {"en": "Quiet process notes", "zh": "安静的过程笔记"},
                 "rationale": {"en": "A fictional rendering fixture", "zh": "虚构的渲染测试样例"},
                 "devices": {"en": "Distinct text, detail and annotation layers", "zh": "分离文字、细节与注释图层"},
                 "palette": [{"role": {"en": "Ink", "zh": "文字"}, "hex": "#272333"}, {"role": {"en": "Annotation", "zh": "注释"}, "hex": "#6855E2"}],
                 "typography": [{"role": {"en": "Body", "zh": "正文"}, "family": "Arial", "sample": "Process Study"}, {"role": {"en": "Notes", "zh": "注释"}, "family": "Courier New", "sample": "A detail worth showing"}],
                 "images": [{"path": "media/detail.png", "caption": {"en": "Synthetic one-pixel fixture", "zh": "合成单像素测试图"}}]}
    common = {"schemaVersion": 1, "projectSlug": "process-study", "version": "v1", "canvas": {"width": 5120, "height": 1600}, "copyPath": "copy.json"}
    plan, scene = dict(common, direction=direction, pages=pages), dict(common, spreads=spreads)
    for name, value in (("copy.json", library), ("plan.json", plan), ("scene-v1.json", scene)):
        project.write_json(root / name, value)
    return library, plan, scene


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ptp-test-")
        self.root = Path(self.temporary.name)
        self.library, self.plan, self.scene = fixture(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def patch(self, fields, **other):
        value = {"schemaVersion": 1, "projectSlug": "process-study", "fields": fields, **other}
        project.write_json(self.root / "patch.json", value)
        return project.import_intake(self.root, self.root / "patch.json")

    def test_chat_import_preserves_answers_notes_and_snapshots(self):
        original = project.read_json(self.root / "project.json")
        result = self.patch({"project.name": {"state": "confirmed", "value": "A chosen title", "notes": "Student note"}}, language="zh")
        current = project.read_json(self.root / "project.json")
        self.assertEqual(result["changedFields"], ["project.name"])
        self.assertEqual(current["language"], "zh")
        self.assertEqual(current["fields"]["project.originMotivation"], original["fields"]["project.originMotivation"])
        self.assertEqual(current["fields"]["project.name"]["notes"], "Student note")
        self.assertEqual(len(current["fields"]), 30)
        self.assertTrue(list((self.root / ".history").glob("intake-r2-*.json")))

    def test_ai_route_and_optional_figma(self):
        current = project.read_json(self.root / "project.json")
        self.assertEqual(project.missing_fields(current), [])
        self.assertEqual([f["id"] for f in project.missing_fields(current, figma=True)], ["delivery.figmaUrl"])
        self.patch({"ai.used": {"state": "confirmed", "value": "Yes", "notes": "Pretrained computer vision"}})
        self.assertEqual(len(project.missing_fields(project.read_json(self.root / "project.json"))), 4)
        self.patch({"ai.modelsTools": {"state": "confirmed", "value": "A supplied model name", "notes": ""}, "ai.used": {"state": "confirmed", "value": "No", "notes": "Correction"}})
        current = project.read_json(self.root / "project.json")
        self.assertEqual(project.missing_fields(current), [])
        self.assertEqual(current["fields"]["ai.modelsTools"]["value"], "A supplied model name")

    def test_invalid_input_cannot_mutate_project(self):
        original = (self.root / "project.json").read_bytes()
        with self.assertRaises(ValueError):
            self.patch({"delivery.plannedPages": {"state": "confirmed", "value": 999, "notes": ""}})
        self.assertEqual((self.root / "project.json").read_bytes(), original)
        with self.assertRaises(ValueError):
            self.patch({}, projectSlug="another-project")
        with self.assertRaises(ValueError):
            self.patch({}, intakeRevision=1)
        with self.assertRaises(ValueError):
            self.patch({}, approvals={"plan": "approved"})
        self.assertEqual((self.root / "project.json").read_bytes(), original)

    def test_init_refuses_overwrite_and_installed_package(self):
        with self.assertRaises(ValueError):
            project.initialize(self.root, "process-study")
        with self.assertRaises(ValueError):
            project.project_root(str(PLUGIN / "portfolio-work"))

    def test_form_embeds_untrusted_text_safely(self):
        self.patch({"project.name": {"state": "confirmed", "value": '</script><script>alert("unsafe")</script>', "notes": ""}})
        data = (self.root / "intake.html").read_text()
        self.assertNotIn('</script><script>alert("unsafe")</script>', data)
        self.assertIn("\\u003c/script>", data)

    def test_review_and_scene_preserve_exact_copy(self):
        board = render.review_html(self.root, self.plan)
        files = render.render_spreads(self.root, self.scene)
        self.assertEqual(len(files), 6)
        self.assertEqual(board.count('class="wireframe"'), 4)
        native = json.loads(files["native-scene.json"])
        self.assertEqual(native["canonicalCopy"], self.library)
        self.assertEqual(native["canvas"], {"width": 5120, "height": 1600})
        self.assertTrue(native["spreads"][0]["elements"][2]["sourceImageData"].startswith("data:image/png;base64,"))
        self.assertIn("Trying an alternative", files["spread-03.html"])
        self.assertEqual(len(render.render_spreads(self.root, self.scene, sample=True)), 3)

    def test_source_validation_rejects_incomplete_copy_and_external_assets(self):
        bad = copy.deepcopy(self.scene)
        bad["spreads"][0]["elements"][0]["copyId"] = "UNKNOWN"
        with self.assertRaises(ValueError):
            render.render_spreads(self.root, bad)
        bad = copy.deepcopy(self.scene)
        bad["spreads"][0]["elements"][2]["assetPath"] = "../outside.png"
        with self.assertRaises(ValueError):
            render.render_spreads(self.root, bad)
        bad = copy.deepcopy(self.scene)
        bad["spreads"][0]["elements"][3]["copyId"] = "TXT-01-TITLE"
        with self.assertRaises(ValueError):
            render.render_spreads(self.root, bad)

    def test_artifact_approval_binds_actual_changed_source(self):
        output = self.root / "review.html"
        output.write_text(render.review_html(self.root, self.plan))
        first = project.approve(self.root, "plan", "review.html", "Test fixture authorization only")
        output.write_text(output.read_text() + "\n<!-- test revision -->")
        self.assertNotEqual(first["sha256"], project.artifact_digest(output))
        self.assertEqual(project.read_json(self.root / "approvals.json")["records"][0]["sha256"], first["sha256"])

    def test_cli_preserves_existing_outputs(self):
        command = [sys.executable, str(SCRIPTS / "render.py"), "spreads", "--project", str(self.root), "--scene", "scene-v1.json", "--output", "html-v1"]
        first = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        digest = project.artifact_digest(self.root / "html-v1")
        second = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(second.returncode, 1)
        self.assertIn("already exists", second.stderr)
        self.assertEqual(digest, project.artifact_digest(self.root / "html-v1"))


if __name__ == "__main__":
    unittest.main()
