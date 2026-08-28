from __future__ import annotations

import copy
import subprocess
import tempfile
import unittest
from pathlib import Path

import canvas01
import directory_board
import repo_canvas


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema" / "canvas-0.1.schema.json"


class DirectoryBoardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "canvas@example.invalid")
        self.git("config", "user.name", "Canvas Test")
        (self.repo / "docs" / "nested").mkdir(parents=True)
        (self.repo / "src").mkdir()
        (self.repo / "README.md").write_text("# Example\n", encoding="utf-8")
        (self.repo / "docs" / "guide.md").write_text("guide\n", encoding="utf-8")
        (self.repo / "docs" / "nested" / "detail.txt").write_text("detail\n", encoding="utf-8")
        (self.repo / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.strip()

    def source_field(self):
        return repo_canvas.project_git_repository(self.repo, source_id="example/repo")[0]

    def board(self):
        source = self.source_field()
        before = copy.deepcopy(source)
        board = directory_board.materialize_directory_board(source)
        self.assertEqual(before, source)
        return source, board

    def test_directory_board_is_first_explicit_premise_bearing_board(self):
        source, board = self.board()
        self.assertNotIn("premise", source["boards"][0])
        self.assertEqual("Directory Board", board["boards"][0]["label"])
        self.assertEqual(directory_board.PREMISE, board["boards"][0]["premise"])
        self.assertEqual("directory", board["boards"][0]["board_id"])
        self.assertEqual({"directory"}, {obj["placement"]["board_id"] for obj in board["objects"]})

    def test_board_derivation_creates_no_objects_or_connections(self):
        source, board = self.board()
        self.assertEqual(
            [obj["object_id"] for obj in source["objects"]],
            [obj["object_id"] for obj in board["objects"]],
        )
        self.assertEqual(source["connections"], board["connections"])
        self.assertEqual(
            [obj.get("ground_refs") for obj in source["objects"]],
            [obj.get("ground_refs") for obj in board["objects"]],
        )

    def test_directory_arrangement_is_indented_and_row_ordered(self):
        _, board = self.board()
        by_id = {obj["object_id"]: obj for obj in board["objects"]}
        root = by_id["git:."]["placement"]["bounds"]
        docs = by_id["git:docs"]["placement"]["bounds"]
        nested = by_id["git:docs/nested"]["placement"]["bounds"]
        guide = by_id["git:docs/guide.md"]["placement"]["bounds"]
        self.assertLess(root["x"], docs["x"])
        self.assertLess(docs["x"], nested["x"])
        self.assertLess(nested["y"], guide["y"])
        self.assertEqual(30.0, guide["height"])

    def test_materialized_board_validates_against_portable_contract(self):
        _, board = self.board()
        schema = canvas01.load_json(SCHEMA)
        self.assertEqual([], canvas01.validate_against_schema(board, schema))
        self.assertEqual([], canvas01.validate_semantics(board))

    def test_renderer_is_a_board_frame_and_not_a_card_wall(self):
        _, board = self.board()
        output = Path(self.tmp.name) / "directory.html"
        result = directory_board.render_directory_board(board, output)
        rendered = output.read_text(encoding="utf-8")
        self.assertEqual("directory", result["board"])
        self.assertIn('class="board"', rendered)
        self.assertIn("Directory Board", rendered)
        self.assertIn(directory_board.PREMISE, rendered)
        self.assertIn('role="tree"', rendered)
        self.assertNotIn('class="card', rendered)
        self.assertNotIn("iframe", rendered)
        self.assertNotIn("render-body", rendered)

    def test_every_contains_connection_is_visible_geometry(self):
        _, board = self.board()
        output = Path(self.tmp.name) / "directory.html"
        directory_board.render_directory_board(board, output)
        rendered = output.read_text(encoding="utf-8")
        contains = [c for c in board["connections"] if c["kind"] == "contains"]
        self.assertIn("graph.connections", rendered)
        self.assertIn("data.connectionId", rendered)
        self.assertIn("class='connection'", rendered.replace('"', "'"))
        self.assertEqual(len(board["objects"]) - 1, len(contains))

    def test_directory_interaction_is_collapse_search_zoom_and_pan(self):
        _, board = self.board()
        output = Path(self.tmp.name) / "directory.html"
        directory_board.render_directory_board(board, output)
        rendered = output.read_text(encoding="utf-8")
        self.assertIn("function toggle(id)", rendered)
        self.assertIn("walkVisible", rendered)
        self.assertIn("viewport.addEventListener('wheel'", rendered)
        self.assertIn("viewport.addEventListener('pointerdown'", rendered)
        self.assertIn("Find path", rendered)
        self.assertNotIn("scrollLeft", rendered)
        self.assertNotIn("scrollTop", rendered)


if __name__ == "__main__":
    unittest.main()
