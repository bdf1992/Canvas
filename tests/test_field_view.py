from __future__ import annotations

import copy
import subprocess
import tempfile
import unittest
from pathlib import Path

import field_view
import repo_canvas


class FieldViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "canvas@example.invalid")
        self.git("config", "user.name", "Canvas Test")
        (self.repo / "docs").mkdir()
        (self.repo / "README.txt").write_text("Hello Canvas\nReadable content\n", encoding="utf-8")
        (self.repo / "docs" / "demo.html").write_text(
            "<h1>Visual HTML</h1><p>Safe preview</p><script>window.pwned=1</script>",
            encoding="utf-8",
        )
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.strip()

    def render(self):
        document, _ = repo_canvas.project_git_repository(self.repo, source_id="example/repo")
        before = copy.deepcopy(document)
        output = Path(self.tmp.name) / "field.html"
        result = field_view.render_field(document, self.repo, output)
        self.assertEqual(before, document)
        return document, result, output.read_text(encoding="utf-8")

    def test_design_system_prefers_focus_over_fit_all_chrome(self):
        _, _, rendered = self.render()
        self.assertIn('id="home"', rendered)
        self.assertIn('id="search"', rendered)
        self.assertIn("minReadableScale=.55", rendered)
        self.assertIn("requestAnimationFrame(home)", rendered)
        self.assertNotIn('id="zoom-in"', rendered)
        self.assertNotIn('id="zoom-out"', rendered)
        self.assertNotIn('id="fit"', rendered)
        self.assertNotIn('id="reset"', rendered)

    def test_contextual_inspector_is_hidden_until_selection(self):
        _, _, rendered = self.render()
        self.assertIn('<aside class="peek" id="peek" hidden>', rendered)
        self.assertIn("peek.hidden=false", rendered)
        self.assertIn("peek.hidden=true", rendered)

    def test_search_navigates_without_filtering_topology(self):
        _, _, rendered = self.render()
        self.assertIn("const hit=Object.entries(graph.objects).find", rendered)
        self.assertNotIn("classList.toggle('hidden'", rendered)
        self.assertNotIn("visibleIds", rendered)

    def test_wheel_zoom_and_drag_pan_are_the_only_primary_spatial_controls(self):
        _, _, rendered = self.render()
        self.assertIn("viewport.addEventListener('wheel'", rendered)
        self.assertIn("e.preventDefault()", rendered)
        self.assertIn("viewport.addEventListener('pointerdown'", rendered)
        self.assertNotIn("scrollLeft", rendered)
        self.assertNotIn("scrollTop", rendered)

    def test_exact_pinned_bytes_drive_text_and_html_cards(self):
        document, result, rendered = self.render()
        self.assertEqual({"tree": 2, "text": 1, "html": 1}, result["renderers"])
        self.assertIn("Readable content", rendered)
        self.assertIn("Visual HTML", rendered)
        self.assertIn('iframe sandbox=""', rendered)
        self.assertIn("default-src &amp;#x27;none&amp;#x27;", rendered)
        self.assertEqual({"reference"}, {obj["kind"] for obj in document["objects"]})

        (self.repo / "README.txt").write_text("DIRTY WORKTREE CONTENT", encoding="utf-8")
        output = Path(self.tmp.name) / "second.html"
        field_view.render_field(document, self.repo, output)
        second = output.read_text(encoding="utf-8")
        self.assertIn("Readable content", second)
        self.assertNotIn("DIRTY WORKTREE CONTENT", second)


if __name__ == "__main__":
    unittest.main()
