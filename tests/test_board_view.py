from __future__ import annotations

import copy
import subprocess
import tempfile
import unittest
from pathlib import Path

import board_view
import canvas01
import repo_canvas


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema" / "canvas-0.1.schema.json"
PREMISE = "What exists here, and how is it contained?"


class BoardViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "canvas@example.invalid")
        self.git("config", "user.name", "Canvas Test")
        (self.repo / "docs").mkdir()
        (self.repo / "README.md").write_text("# Example\nReadable board card\n", encoding="utf-8")
        (self.repo / "docs" / "demo.html").write_text(
            "<h1>Visual HTML Card</h1><script>window.pwned=1</script>", encoding="utf-8"
        )
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
        board = board_view.materialize_board(
            source,
            board_id="repository-containment",
            label="Directory Board",
            premise=PREMISE,
            relation_kind="contains",
        )
        self.assertEqual(before, source)
        return source, board

    def test_board_is_premise_plus_existing_objects_and_connections(self):
        source, board = self.board()
        self.assertEqual("repository-containment", board["boards"][0]["board_id"])
        self.assertEqual("Directory Board", board["boards"][0]["label"])
        self.assertEqual(PREMISE, board["boards"][0]["premise"])
        self.assertEqual(
            [obj["object_id"] for obj in source["objects"]],
            [obj["object_id"] for obj in board["objects"]],
        )
        self.assertEqual(source["connections"], board["connections"])
        self.assertEqual(
            [obj.get("ground_refs") for obj in source["objects"]],
            [obj.get("ground_refs") for obj in board["objects"]],
        )

    def test_board_uses_generic_frame_not_directory_primitive(self):
        _, board = self.board()
        self.assertEqual(1, len(board["frames"]))
        frame = board["frames"][0]
        self.assertEqual("frame:repository-containment", frame["frame_id"])
        self.assertEqual(
            {obj["object_id"] for obj in board["objects"]}, set(frame["members"])
        )
        self.assertEqual(
            {"repository-containment"},
            {obj["placement"]["board_id"] for obj in board["objects"]},
        )

    def test_board_layout_is_hierarchical_but_semantics_stay_in_relations(self):
        _, board = self.board()
        by_id = {obj["object_id"]: obj for obj in board["objects"]}
        root = by_id["git:."]["placement"]["bounds"]
        docs = by_id["git:docs"]["placement"]["bounds"]
        demo = by_id["git:docs/demo.html"]["placement"]["bounds"]
        self.assertLess(root["x"], docs["x"])
        self.assertLess(docs["x"], demo["x"])
        self.assertEqual(190.0, demo["height"])

    def test_board_validates_portable_contract(self):
        _, board = self.board()
        schema = canvas01.load_json(SCHEMA)
        self.assertEqual([], canvas01.validate_against_schema(board, schema))
        self.assertEqual([], canvas01.validate_semantics(board))

    def test_rendered_board_has_cards_and_connection_geometry(self):
        _, board = self.board()
        output = Path(self.tmp.name) / "board.html"
        result = board_view.render_board(board, self.repo, output, relation_kind="contains")
        rendered = output.read_text(encoding="utf-8")
        self.assertEqual(len(board["objects"]), result["cards"])
        self.assertEqual(len(board["objects"]), rendered.count('<article class="card '))
        self.assertEqual(
            len([c for c in board["connections"] if c["kind"] == "contains"]),
            rendered.count('class="connection"'),
        )
        self.assertIn('class="board-frame"', rendered)
        self.assertIn("relations: contains", rendered)
        self.assertNotIn('role="tree"', rendered)
        self.assertNotIn('class="row"', rendered)
        self.assertNotIn("folders collapse", rendered)

    def test_cards_render_exact_text_and_html_bytes(self):
        document, board = self.board()
        output = Path(self.tmp.name) / "board.html"
        result = board_view.render_board(board, self.repo, output)
        rendered = output.read_text(encoding="utf-8")
        self.assertIn("Readable board card", rendered)
        self.assertIn("Visual HTML Card", rendered)
        self.assertIn('iframe sandbox=""', rendered)
        self.assertEqual({"tree": 2, "text": 1, "html": 1}, result["renderers"])
        self.assertEqual({"reference"}, {obj["kind"] for obj in document["objects"]})

        (self.repo / "README.md").write_text("DIRTY CONTENT", encoding="utf-8")
        second = Path(self.tmp.name) / "second.html"
        board_view.render_board(board, self.repo, second)
        text = second.read_text(encoding="utf-8")
        self.assertIn("Readable board card", text)
        self.assertNotIn("DIRTY CONTENT", text)

    def test_relations_are_primary_topology_and_selection_highlights_them(self):
        _, board = self.board()
        output = Path(self.tmp.name) / "board.html"
        board_view.render_board(board, self.repo, output)
        rendered = output.read_text(encoding="utf-8")
        self.assertIn("data-connection-id=", rendered)
        self.assertIn("edge.dataset.from===id||edge.dataset.to===id", rendered)
        self.assertIn("viewport.addEventListener('wheel'", rendered)
        self.assertIn("viewport.addEventListener('pointerdown'", rendered)
        self.assertNotIn("scrollLeft", rendered)
        self.assertNotIn("scrollTop", rendered)


if __name__ == "__main__":
    unittest.main()
