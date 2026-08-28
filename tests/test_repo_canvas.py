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
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
        (self.repo / "a.txt").write_text("a\n", encoding="utf-8")
        (self.repo / "dir" / "b.txt").write_text("b\n", encoding="utf-8")
        (self.repo / "dir" / "sub" / "c.txt").write_text("c\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def project(self):
        return repo_canvas.project_git_repository(self.repo, source_id="example/repo")

    def render(self):
        document, _ = self.project()
        output = Path(self.tmp.name) / "board.html"
        repo_canvas.render_html(document, output)
        return document, output.read_text(encoding="utf-8")

    def test_complete_git_tree_uses_existing_canvas_grammar(self):
        document, summary = self.project()
        self.assertEqual(3, summary["trees"])
        self.assertEqual(3, summary["blobs"])
        self.assertEqual(6, summary["objects"])
        self.assertEqual(5, summary["connections"])
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

    def test_renderer_shows_repository_paths_without_new_domain_objects(self):
        document, _ = self.project()
        before = copy.deepcopy(document)
        output = Path(self.tmp.name) / "board.html"
        repo_canvas.render_html(document, output)
        rendered = output.read_text(encoding="utf-8")

        self.assertEqual(before, document)
        self.assertIn("example/repo", rendered)
        self.assertIn("dir/sub/c.txt", rendered)
        self.assertIn("6 objects", rendered)
        self.assertIn("5 connections", rendered)
        self.assertIn('data-object-id="git:dir"', rendered)
        self.assertIn('data-from="git:dir"', rendered)
        self.assertIn('data-to="git:dir/sub"', rendered)
        self.assertIn("Filter repository paths", rendered)
        self.assertIn("Collapse subtree", rendered)
        self.assertIn("Expand all", rendered)
        self.assertIn("Fit all", rendered)
        self.assertIn("Reset view", rendered)
        self.assertIn("Pinned revision", rendered)

    def test_canvas_wheel_zooms_instead_of_scrolling_the_board(self):
        _, rendered = self.render()
        self.assertIn("Repository infinite Canvas board", rendered)
        self.assertIn("touch-action:none", rendered)
        self.assertIn("overflow:hidden", rendered)
        self.assertIn("addEventListener('wheel'", rendered)
        self.assertIn("event.preventDefault()", rendered)
        self.assertIn("zoomAt(scale * factor, event.clientX, event.clientY)", rendered)
        self.assertNotIn("scrollLeft", rendered)
        self.assertNotIn("scrollTop", rendered)
        self.assertNotIn("scale-shell", rendered)

    def test_infinite_canvas_pan_is_world_translation_not_scroll_position(self):
        _, rendered = self.render()
        self.assertIn("let panX = 0", rendered)
        self.assertIn("let panY = 0", rendered)
        self.assertIn("translate(${panX}px, ${panY}px) scale(${scale})", rendered)
        self.assertIn("viewport.style.backgroundPosition = `${panX}px ${panY}px`", rendered)
        self.assertIn("panX = drag.panX + (event.clientX - drag.x)", rendered)
        self.assertIn("panY = drag.panY + (event.clientY - drag.y)", rendered)

    def test_renderer_contains_only_projection_ui_state_not_new_canvas_objects(self):
        document, rendered = self.render()
        self.assertNotIn("RepoNode", rendered)
        self.assertNotIn("FileCard", rendered)
        self.assertNotIn("DirectoryCard", rendered)
        self.assertEqual({"reference"}, {obj["kind"] for obj in document["objects"]})
        self.assertEqual({"contains"}, {connection["kind"] for connection in document["connections"]})


if __name__ == "__main__":
    unittest.main()
