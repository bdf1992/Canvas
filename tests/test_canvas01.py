import copy
import tempfile
import unittest
from pathlib import Path

import canvas01


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures" / "grounded-field.canvas.json"
SCHEMA = ROOT / "schema" / "canvas-0.1.schema.json"


class Canvas01Tests(unittest.TestCase):
    def load(self):
        return canvas01.load_json(FIXTURE)

    def test_fixture_validates_against_schema_and_semantics(self):
        doc = self.load()
        schema = canvas01.load_json(SCHEMA)
        self.assertEqual([], canvas01.validate_against_schema(doc, schema))
        self.assertEqual([], canvas01.validate_semantics(doc))

    def test_note_is_one_hop_from_ground(self):
        path = canvas01.ground_path(self.load(), "object-note")
        self.assertIsNotNone(path)
        self.assertEqual(1, path["distance"])
        self.assertEqual(["object-note", "object-source"], path["objects"])
        self.assertEqual(["connection-note-source"], path["connections"])

    def test_local_file_provider_resolves_fixture(self):
        doc = self.load()
        path = canvas01.ground_path(doc, "object-note")
        result = canvas01.resolve_ground_ref(path["ground_refs"][0], ROOT)
        self.assertTrue(result["exists"])
        self.assertTrue(result["path"].endswith("fixtures/example.txt"))

    def test_move_changes_only_layout(self):
        doc = self.load()
        before_refs = copy.deepcopy(doc["objects"][0]["ground_refs"])
        before_connection = copy.deepcopy(doc["connections"])
        canvas01.move_object(doc, "object-source", 200, 220, 260, 160)
        self.assertEqual(before_refs, doc["objects"][0]["ground_refs"])
        self.assertEqual(before_connection, doc["connections"])

    def test_frame_membership_is_neutral(self):
        doc = self.load()
        before_refs = copy.deepcopy(doc["objects"][0]["ground_refs"])
        canvas01.set_frame_membership(doc, "frame-working-set", ["object-note"])
        self.assertEqual(["object-note"], doc["frames"][0]["members"])
        self.assertEqual(before_refs, doc["objects"][0]["ground_refs"])
        self.assertEqual(1, canvas01.ground_path(doc, "object-note")["distance"])

    def test_round_trip_has_no_semantic_loss(self):
        doc = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "roundtrip.canvas.json"
            canvas01.save_json(doc, path)
            reloaded = canvas01.load_json(path)
        self.assertEqual(doc, reloaded)

    def test_ungrounded_note_is_refused(self):
        doc = self.load()
        doc["connections"] = []
        errors = canvas01.validate_semantics(doc)
        self.assertTrue(any("object-note has no stored grounding path" in error for error in errors))

    def test_local_file_provider_cannot_escape_root(self):
        with self.assertRaises(canvas01.CanvasError):
            canvas01.resolve_ground_ref({"provider": "local-file", "id": "../outside.txt"}, ROOT)


if __name__ == "__main__":
    unittest.main()
