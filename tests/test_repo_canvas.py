import copy
import subprocess
import tempfile
import unittest
from pathlib import Path

import canvas01
import repo_canvas


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema" / "canvas-0.1.schema.json"


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return proc.stdout.strip()


class RepoCanvasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "canvas@example.invalid")
        git(self.repo, "config", "user.name", "Canvas Test")
        (self.repo / "dir" / "sub").mkdir(parents=True)
        (self.repo / "a.txt").write_text("hello from text\nsecond line\n", encoding="utf-8")
        (self.repo / "dir" / "b.txt").write_text("b\n", encoding="utf-8")
        (self.repo / "dir" / "sub" / "c.txt").write_text("c\n", encoding="utf-8")
        (self.repo / "page.html").write_text(
            "<!doctype html><style>body{font-family:sans-serif}</style>"
            "<h1>Visual HTML</h1><script>window.__canvas_bad = true</script>",
            encoding="utf-8",
        )
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def project(self):
        return repo_canvas.project_git_repository(self.repo, source_id="example/repo")

    def render(self, document):
        output = Path(self.tmp.name) / "canvas.html"
        repo_canvas.render_html(
            document,
            output,
            repo=self.repo,
            source_id="example/repo",
        )
        return output.read_text(encoding="utf-8")

    def test_complete_git_tree_uses_existing_canvas_grammar(self):
        document, summary = self.project()
        self.assertEqual(3, summary["trees"])
        self.assertEqual(4, summary["blobs"])
        self.assertEqual(7, summary["objects"])
        self.assertEqual(6, summary["connections"])
        self.assertEqual({"reference"}, {obj["kind"] for obj in document["objects"]})
        self.assertEqual({"git-object"}, {obj["ground_refs"][0]["provider"] for obj in document["objects"]})
        self.assertEqual({"contains"}, {connection["kind"] for connection in document["connections"]})
        self.assertEqual([], document["frames"])

    def test_projection_validates_against_existing_0_1_contract(self):
        document, _ = self.project()
        schema = canvas01.load_json(SCHEMA)
        self.assertEqual([], canvas01.validate_against_schema(document, schema))
        self.assertEqual([], canvas01.validate_semantics(document))

    def test_every_projected_object_resolves_to_exact_git_object(self):
        document, summary = self.project()
        for obj in document["objects"]:
            ref = obj["ground_refs"][0]
            result = repo_canvas.resolve_git_ground_ref(ref, self.repo, source_id="example/repo")
            self.assertTrue(result["exists"])
            self.assertEqual(summary["commit"], result["version"])
            self.assertEqual(ref["digest"], result["digest"])

    def test_blob_renderer_reads_exact_pinned_git_bytes(self):
        document, _ = self.project()
        page = next(obj for obj in document["objects"] if obj["object_id"] == "git:page.html")
        data = repo_canvas.resolve_git_blob_bytes(
            page["ground_refs"][0], self.repo, source_id="example/repo"
        )
        self.assertIn(b"Visual HTML", data)
        (self.repo / "page.html").write_text("working tree replacement", encoding="utf-8")
        pinned = repo_canvas.resolve_git_blob_bytes(
            page["ground_refs"][0], self.repo, source_id="example/repo"
        )
        self.assertEqual(data, pinned)

    def test_same_commit_produces_same_semantic_projection(self):
        first, first_summary = self.project()
        second, second_summary = self.project()
        self.assertEqual(first_summary, second_summary)
        self.assertEqual(first, second)

    def test_uncommitted_work_does_not_change_pinned_projection(self):
        before, before_summary = self.project()
        (self.repo / "a.txt").write_text("working tree change\n", encoding="utf-8")
        (self.repo / "untracked.txt").write_text("not in HEAD\n", encoding="utf-8")
        after, after_summary = self.project()
        self.assertEqual(before_summary, after_summary)
        self.assertEqual(before, after)

    def test_renderer_visually_renders_text_and_html_without_new_object_types(self):
        document, _ = self.project()
        before = copy.deepcopy(document)
        rendered = self.render(document)

        self.assertEqual(before, document)
        self.assertIn('data-renderer="text"', rendered)
        self.assertIn('data-renderer="html"', rendered)
        self.assertIn("hello from text", rendered)
        self.assertIn("Visual HTML", rendered)
        self.assertIn('<iframe sandbox=""', rendered)
        self.assertIn("Content-Security-Policy", rendered)
        self.assertIn("default-src", rendered)
        self.assertNotIn("<script>window.__canvas_bad", rendered)
        self.assertIn("Card renderer", rendered)
        self.assertEqual({"reference"}, {obj["kind"] for obj in document["objects"]})
        self.assertEqual({"contains"}, {connection["kind"] for connection in document["connections"]})

    def test_renderer_is_infinite_canvas_navigation_not_scroll_navigation(self):
        document, _ = self.project()
        rendered = self.render(document)

        self.assertIn("Repository Canvas field", rendered)
        self.assertIn("event.preventDefault()", rendered)
        self.assertIn("function zoomAt", rendered)
        self.assertIn("let selected = null, scale = 1, panX = 0, panY = 0", rendered)
        self.assertIn("overflow:hidden", rendered)
        self.assertNotIn("scrollLeft", rendered)
        self.assertNotIn("scrollTop", rendered)
        self.assertNotIn("scale-shell", rendered)

    def test_renderer_contains_only_projection_ui_state_not_new_canvas_objects(self):
        document, _ = self.project()
        rendered = self.render(document)

        self.assertNotIn("RepoNode", rendered)
        self.assertNotIn("FileCard", rendered)
        self.assertNotIn("DirectoryCard", rendered)
        self.assertNotIn("TextCard", rendered)
        self.assertNotIn("HtmlCard", rendered)
        self.assertEqual({"reference"}, {obj["kind"] for obj in document["objects"]})
        self.assertEqual({"contains"}, {connection["kind"] for connection in document["connections"]})


if __name__ == "__main__":
    unittest.main()
