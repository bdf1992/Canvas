from __future__ import annotations

import argparse
import copy
import json
from collections import deque
from pathlib import Path
from typing import Any


class CanvasError(ValueError):
    pass


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise CanvasError("Canvas document must be a JSON object")
    return value


def save_json(document: dict[str, Any], path: str | Path) -> None:
    with Path(path).open("w", encoding="utf-8") as fh:
        json.dump(document, fh, indent=2, sort_keys=True)
        fh.write("\n")


def _resolve_ref(schema_root: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise CanvasError(f"Only local schema refs are supported: {ref}")
    node: Any = schema_root
    for part in ref[2:].split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    if not isinstance(node, dict):
        raise CanvasError(f"Schema ref did not resolve to an object: {ref}")
    return node


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    raise CanvasError(f"Unsupported schema type: {expected}")


def _validate_schema_node(value: Any, schema: dict[str, Any], root: dict[str, Any], path: str) -> list[str]:
    if "$ref" in schema:
        schema = _resolve_ref(root, schema["$ref"])

    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type is not None:
        types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_type_matches(value, t) for t in types):
            return [f"{path}: expected type {types}, got {type(value).__name__}"]

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: expected one of {schema['enum']!r}")
    if isinstance(value, str) and "minLength" in schema and len(value) < schema["minLength"]:
        errors.append(f"{path}: string shorter than minLength {schema['minLength']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "exclusiveMinimum" in schema and not value > schema["exclusiveMinimum"]:
            errors.append(f"{path}: must be > {schema['exclusiveMinimum']}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: additional property not allowed: {key!r}")
        for key, child_schema in properties.items():
            if key in value:
                errors.extend(_validate_schema_node(value[key], child_schema, root, f"{path}.{key}"))

    if isinstance(value, list):
        if schema.get("uniqueItems"):
            serialized = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in value]
            if len(serialized) != len(set(serialized)):
                errors.append(f"{path}: array items must be unique")
        if "items" in schema:
            for i, item in enumerate(value):
                errors.extend(_validate_schema_node(item, schema["items"], root, f"{path}[{i}]"))

    return errors


def validate_against_schema(document: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    return _validate_schema_node(document, schema, schema, "$")


def _index(document: dict[str, Any], collection: str, id_key: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in document[collection]:
        item_id = item[id_key]
        if item_id in result:
            raise CanvasError(f"Duplicate {id_key}: {item_id}")
        result[item_id] = item
    return result


def ground_path(document: dict[str, Any], object_id: str) -> dict[str, Any] | None:
    objects = _index(document, "objects", "object_id")
    if object_id not in objects:
        raise CanvasError(f"Unknown object: {object_id}")

    if objects[object_id].get("ground_refs"):
        return {"object_id": object_id, "distance": 0, "objects": [object_id], "connections": [], "ground_refs": objects[object_id]["ground_refs"]}

    adjacency: dict[str, list[tuple[str, str]]] = {key: [] for key in objects}
    for connection in document["connections"]:
        source = connection["from"]["object_id"]
        target = connection["to"]["object_id"]
        adjacency.setdefault(source, []).append((target, connection["connection_id"]))
        if connection.get("direction", "undirected") == "undirected":
            adjacency.setdefault(target, []).append((source, connection["connection_id"]))

    queue = deque([(object_id, [object_id], [])])
    visited = {object_id}
    while queue:
        current, object_path, connection_path = queue.popleft()
        for neighbor, connection_id in adjacency.get(current, []):
            if neighbor in visited:
                continue
            next_objects = object_path + [neighbor]
            next_connections = connection_path + [connection_id]
            ground_refs = objects[neighbor].get("ground_refs") or []
            if ground_refs:
                return {
                    "object_id": object_id,
                    "distance": len(next_connections),
                    "objects": next_objects,
                    "connections": next_connections,
                    "ground_refs": ground_refs,
                }
            visited.add(neighbor)
            queue.append((neighbor, next_objects, next_connections))
    return None


def validate_semantics(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        boards = _index(document, "boards", "board_id")
        objects = _index(document, "objects", "object_id")
        frames = _index(document, "frames", "frame_id")
        _index(document, "connections", "connection_id")
    except CanvasError as exc:
        return [str(exc)]

    for obj in objects.values():
        board_id = obj["placement"]["board_id"]
        if board_id not in boards:
            errors.append(f"Object {obj['object_id']} references unknown board {board_id}")

    for frame in frames.values():
        if frame["board_id"] not in boards:
            errors.append(f"Frame {frame['frame_id']} references unknown board {frame['board_id']}")
        for member in frame["members"]:
            if member not in objects:
                errors.append(f"Frame {frame['frame_id']} references unknown object {member}")

    for connection in document["connections"]:
        for side in ("from", "to"):
            endpoint = connection[side]["object_id"]
            if endpoint not in objects:
                errors.append(f"Connection {connection['connection_id']} has unknown {side} object {endpoint}")

    if errors:
        return errors

    for obj in objects.values():
        if obj["kind"] == "reference" and not obj.get("ground_refs"):
            errors.append(f"Reference object {obj['object_id']} must contain at least one GroundRef")
        if obj["kind"] != "reference" and ground_path(document, obj["object_id"]) is None:
            errors.append(f"Object {obj['object_id']} has no stored grounding path")
    return errors


def resolve_ground_ref(ground_ref: dict[str, Any], root: str | Path) -> dict[str, Any]:
    provider = ground_ref["provider"]
    if provider != "local-file":
        raise CanvasError(f"Provider not available in standalone 0.1 reference runtime: {provider}")
    root_path = Path(root).resolve()
    candidate = (root_path / ground_ref["id"]).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise CanvasError("local-file GroundRef escapes provider root") from exc
    if not candidate.is_file():
        raise CanvasError(f"local-file GroundRef does not resolve to a file: {ground_ref['id']}")
    return {
        "provider": provider,
        "id": ground_ref["id"],
        "exists": True,
        "path": str(candidate),
        "size": candidate.stat().st_size,
    }


def move_object(document: dict[str, Any], object_id: str, x: float, y: float, width: float, height: float) -> None:
    if width <= 0 or height <= 0:
        raise CanvasError("width and height must be positive")
    objects = _index(document, "objects", "object_id")
    if object_id not in objects:
        raise CanvasError(f"Unknown object: {object_id}")
    objects[object_id]["placement"]["bounds"] = {"x": x, "y": y, "width": width, "height": height}


def set_frame_membership(document: dict[str, Any], frame_id: str, object_ids: list[str]) -> None:
    frames = _index(document, "frames", "frame_id")
    objects = _index(document, "objects", "object_id")
    if frame_id not in frames:
        raise CanvasError(f"Unknown frame: {frame_id}")
    unknown = [object_id for object_id in object_ids if object_id not in objects]
    if unknown:
        raise CanvasError(f"Unknown frame members: {unknown}")
    frames[frame_id]["members"] = list(dict.fromkeys(object_ids))


def inspect_canvas(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "canvas_id": document["canvas_id"],
        "schema_version": document["schema_version"],
        "boards": [{"board_id": b["board_id"], "label": b["label"]} for b in document["boards"]],
        "objects": [
            {
                "object_id": o["object_id"],
                "kind": o["kind"],
                "label": o.get("label", ""),
                "board_id": o["placement"]["board_id"],
                "bounds": o["placement"]["bounds"],
                "ground_distance": (ground_path(document, o["object_id"]) or {}).get("distance"),
            }
            for o in document["objects"]
        ],
        "frames": copy.deepcopy(document["frames"]),
        "connections": copy.deepcopy(document["connections"]),
    }


def _validated(canvas_path: Path, schema_path: Path) -> dict[str, Any]:
    document = load_json(canvas_path)
    schema = load_json(schema_path)
    errors = validate_against_schema(document, schema) + validate_semantics(document)
    if errors:
        raise CanvasError("\n".join(errors))
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Canvas 0.1 standalone reference runtime")
    parser.add_argument("--schema", default="schema/canvas-0.1.schema.json")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("canvas")

    inspect = sub.add_parser("inspect")
    inspect.add_argument("canvas")

    ground = sub.add_parser("ground-path")
    ground.add_argument("canvas")
    ground.add_argument("object_id")
    ground.add_argument("--root", default=".")

    move = sub.add_parser("move")
    move.add_argument("canvas")
    move.add_argument("object_id")
    move.add_argument("x", type=float)
    move.add_argument("y", type=float)
    move.add_argument("width", type=float)
    move.add_argument("height", type=float)
    move.add_argument("--output", required=True)

    members = sub.add_parser("frame-members")
    members.add_argument("canvas")
    members.add_argument("frame_id")
    members.add_argument("object_ids", nargs="*")
    members.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    schema_path = Path(args.schema)
    document = _validated(Path(args.canvas), schema_path)

    if args.command == "validate":
        print(json.dumps({"valid": True, "canvas_id": document["canvas_id"]}, indent=2))
    elif args.command == "inspect":
        print(json.dumps(inspect_canvas(document), indent=2))
    elif args.command == "ground-path":
        path = ground_path(document, args.object_id)
        if path is None:
            raise CanvasError(f"No grounding path for {args.object_id}")
        path["resolutions"] = [resolve_ground_ref(ref, args.root) for ref in path["ground_refs"]]
        print(json.dumps(path, indent=2))
    elif args.command == "move":
        move_object(document, args.object_id, args.x, args.y, args.width, args.height)
        save_json(document, args.output)
    elif args.command == "frame-members":
        set_frame_membership(document, args.frame_id, args.object_ids)
        save_json(document, args.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CanvasError as exc:
        print(f"Canvas error: {exc}")
        raise SystemExit(2)
