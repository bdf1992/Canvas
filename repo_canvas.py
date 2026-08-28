from __future__ import annotations

import argparse
import html
import json
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

import canvas01


class RepoCanvasError(canvas01.CanvasError):
    pass


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "git command failed"
        raise RepoCanvasError(f"git {' '.join(args)}: {detail}")
    return proc.stdout.strip()


def _id(prefix: str, value: str) -> str:
    return f"{prefix}:{value}"


def git_snapshot(repo: str | Path, revision: str = "HEAD") -> dict[str, Any]:
    repo_path = Path(repo).resolve()
    if _git(repo_path, "rev-parse", "--is-inside-work-tree") != "true":
        raise RepoCanvasError(f"Not a Git working tree: {repo_path}")

    commit = _git(repo_path, "rev-parse", f"{revision}^{{commit}}")
    root_tree = _git(repo_path, "rev-parse", f"{commit}^{{tree}}")
    raw = _git(repo_path, "ls-tree", "-r", "-t", "-l", "--full-tree", commit)

    entries: list[dict[str, Any]] = [
        {"path": ".", "type": "tree", "sha": root_tree, "mode": "040000", "size": None}
    ]
    for line in raw.splitlines():
        if not line:
            continue
        try:
            meta, path = line.split("\t", 1)
            mode, object_type, sha, size_text = meta.split()
        except ValueError as exc:
            raise RepoCanvasError(f"Unexpected git ls-tree line: {line!r}") from exc
        entries.append(
            {
                "path": path,
                "type": object_type,
                "sha": sha,
                "mode": mode,
                "size": None if size_text == "-" else int(size_text),
            }
        )

    entries.sort(key=lambda item: item["path"])
    return {
        "repo_path": str(repo_path),
        "commit": commit,
        "root_tree": root_tree,
        "entries": entries,
    }


def _parent_path(path: str) -> str | None:
    if path == ".":
        return None
    parent = str(PurePosixPath(path).parent)
    return "." if parent in ("", ".") else parent


def _layout(entries: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    # Deterministic depth columns. Git path order is the only ordering input.
    # Placement is a projection and carries no repository semantics.
    ordered = sorted(entries, key=lambda item: item["path"])
    bounds: dict[str, dict[str, float]] = {}
    for row, entry in enumerate(ordered):
        path = entry["path"]
        depth = 0 if path == "." else len(PurePosixPath(path).parts)
        bounds[path] = {
            "x": 40 + depth * 300,
            "y": 40 + row * 88,
            "width": 260,
            "height": 64,
        }
    return bounds


def project_git_repository(
    repo: str | Path,
    *,
    source_id: str | None = None,
    revision: str = "HEAD",
    canvas_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot = git_snapshot(repo, revision)
    repo_path = Path(snapshot["repo_path"])
    source = source_id or repo_path.name
    commit = snapshot["commit"]
    entries = snapshot["entries"]
    layout = _layout(entries)

    objects: list[dict[str, Any]] = []
    for entry in entries:
        path = entry["path"]
        label = source if path == "." else path
        objects.append(
            {
                "object_id": _id("git", path),
                "kind": "reference",
                "label": label,
                "placement": {
                    "board_id": "repo",
                    "bounds": layout[path],
                },
                "ground_refs": [
                    {
                        "provider": "git-object",
                        "id": f"{source}#{path}",
                        "version": commit,
                        "digest": entry["sha"],
                    }
                ],
            }
        )

    paths = {entry["path"] for entry in entries}
    connections: list[dict[str, Any]] = []
    for entry in entries:
        path = entry["path"]
        parent = _parent_path(path)
        if parent is None:
            continue
        if parent not in paths:
            raise RepoCanvasError(f"Git tree is missing parent {parent!r} for {path!r}")
        connections.append(
            {
                "connection_id": _id("contains", path),
                "from": {"object_id": _id("git", parent)},
                "to": {"object_id": _id("git", path)},
                "kind": "contains",
                "direction": "directed",
            }
        )

    document = {
        "schema_version": "0.1",
        "canvas_id": canvas_id or f"git-repo:{source}@{commit}",
        "boards": [{"board_id": "repo", "label": f"{source}@{commit[:12]}"}],
        "objects": objects,
        "frames": [],
        "connections": connections,
    }
    summary = {
        "source_id": source,
        "commit": commit,
        "root_tree": snapshot["root_tree"],
        "trees": sum(1 for entry in entries if entry["type"] == "tree"),
        "blobs": sum(1 for entry in entries if entry["type"] == "blob"),
        "other_git_objects": sum(1 for entry in entries if entry["type"] not in {"tree", "blob"}),
        "objects": len(objects),
        "connections": len(connections),
    }
    return document, summary


def resolve_git_ground_ref(
    ground_ref: dict[str, Any],
    repo: str | Path,
    source_id: str | None = None,
) -> dict[str, Any]:
    if ground_ref.get("provider") != "git-object":
        raise RepoCanvasError(f"Not a git-object GroundRef: {ground_ref.get('provider')}")

    repo_path = Path(repo).resolve()
    source = source_id or repo_path.name
    raw_id = str(ground_ref["id"])
    prefix = f"{source}#"
    if not raw_id.startswith(prefix):
        raise RepoCanvasError(f"GroundRef source {raw_id!r} does not match {source!r}")

    path = raw_id[len(prefix) :]
    version = ground_ref.get("version")
    digest = ground_ref.get("digest")
    if not version or not digest:
        raise RepoCanvasError("git-object GroundRef requires exact version and digest")

    actual_commit = _git(repo_path, "rev-parse", f"{version}^{{commit}}")
    if actual_commit != version:
        raise RepoCanvasError("git-object version did not resolve to the exact commit")

    if path == ".":
        actual_sha = _git(repo_path, "rev-parse", f"{version}^{{tree}}")
    else:
        actual_sha = _git(repo_path, "rev-parse", f"{version}:{path}")
    if actual_sha != digest:
        raise RepoCanvasError(
            f"git-object digest mismatch for {path}: expected {digest}, got {actual_sha}"
        )

    object_type = _git(repo_path, "cat-file", "-t", actual_sha)
    return {
        "provider": "git-object",
        "id": raw_id,
        "version": version,
        "digest": digest,
        "exists": True,
        "object_type": object_type,
        "path": path,
    }


def render_html(document: dict[str, Any], output: str | Path) -> None:
    objects = {obj["object_id"]: obj for obj in document["objects"]}
    tree_ids = {
        connection["from"]["object_id"]
        for connection in document["connections"]
        if connection["kind"] == "contains"
    }
    max_x = max(
        (
            obj["placement"]["bounds"]["x"] + obj["placement"]["bounds"]["width"]
            for obj in objects.values()
        ),
        default=800,
    ) + 80
    max_y = max(
        (
            obj["placement"]["bounds"]["y"] + obj["placement"]["bounds"]["height"]
            for obj in objects.values()
        ),
        default=600,
    ) + 80

    lines: list[str] = []
    for connection in document["connections"]:
        if connection["kind"] != "contains":
            continue
        source = objects[connection["from"]["object_id"]]["placement"]["bounds"]
        target = objects[connection["to"]["object_id"]]["placement"]["bounds"]
        x1 = source["x"] + source["width"]
        y1 = source["y"] + source["height"] / 2
        x2 = target["x"]
        y2 = target["y"] + target["height"] / 2
        lines.append(
            f'<path d="M {x1} {y1} C {x1 + 60} {y1}, {x2 - 60} {y2}, {x2} {y2}" />'
        )

    cards: list[str] = []
    for object_id, obj in objects.items():
        bounds = obj["placement"]["bounds"]
        object_class = "tree" if object_id in tree_ids else "blob"
        label = html.escape(obj.get("label", object_id))
        search_label = html.escape(obj.get("label", object_id).lower(), quote=True)
        ref = obj.get("ground_refs", [{}])[0]
        digest = html.escape(str(ref.get("digest", ""))[:12])
        cards.append(
            f'<div class="card {object_class}" '
            f'style="left:{bounds["x"]}px;top:{bounds["y"]}px;'
            f'width:{bounds["width"]}px;height:{bounds["height"]}px" '
            f'data-label="{search_label}">'
            f'<strong>{label}</strong><span>{object_class} · {digest}</span></div>'
        )

    board_label = html.escape(
        document["boards"][0]["label"] if document["boards"] else document["canvas_id"]
    )
    page = f'''<!doctype html>
<meta charset="utf-8">
<title>{board_label} — Canvas</title>
<style>
:root {{ color-scheme: dark; font-family: ui-sans-serif, system-ui, sans-serif; }}
body {{ margin:0; background:#111318; color:#e8ebf0; }}
header {{ position:sticky; top:0; z-index:5; display:flex; gap:16px; align-items:center; padding:12px 16px; background:#181b22; border-bottom:1px solid #333945; }}
header strong {{ white-space:nowrap; }}
header span {{ color:#a8b0bd; white-space:nowrap; }}
input {{ min-width:260px; flex:1; padding:8px 10px; border:1px solid #444b59; border-radius:8px; background:#101218; color:inherit; }}
.viewport {{ overflow:auto; height:calc(100vh - 58px); }}
.board {{ position:relative; width:{max_x}px; height:{max_y}px; background-image:radial-gradient(#2d3340 1px, transparent 1px); background-size:24px 24px; }}
svg {{ position:absolute; inset:0; width:100%; height:100%; pointer-events:none; }}
path {{ fill:none; stroke:#505968; stroke-width:1.5; }}
.card {{ position:absolute; box-sizing:border-box; padding:9px 11px; border:1px solid #3b4350; border-radius:9px; background:#1d212a; overflow:hidden; }}
.card.tree {{ border-left:4px solid #8a93a3; }}
.card.blob {{ border-left:4px solid #596271; }}
.card strong {{ display:block; font-size:12px; line-height:1.25; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.card span {{ display:block; margin-top:7px; color:#a8b0bd; font-size:10px; }}
.card.filtered {{ opacity:.07; }}
</style>
<header><strong>{board_label}</strong><span>{len(objects)} objects · {len(document["connections"])} connections</span><input id="filter" aria-label="Filter repository paths" placeholder="Filter paths"></header>
<div class="viewport"><div class="board"><svg viewBox="0 0 {max_x} {max_y}" preserveAspectRatio="none">{''.join(lines)}</svg>{''.join(cards)}</div></div>
<script>
const input=document.getElementById('filter');
const cards=[...document.querySelectorAll('.card')];
input.addEventListener('input',()=>{{
  const value=input.value.trim().toLowerCase();
  for(const card of cards) card.classList.toggle('filtered',Boolean(value)&&!card.dataset.label.includes(value));
}});
</script>
'''
    Path(output).write_text(page, encoding="utf-8")


def verify_document(
    document: dict[str, Any],
    repo: str | Path,
    *,
    source_id: str | None,
    schema_path: str | Path,
) -> dict[str, Any]:
    schema = canvas01.load_json(schema_path)
    errors = canvas01.validate_against_schema(document, schema) + canvas01.validate_semantics(document)
    if errors:
        raise RepoCanvasError("\n".join(errors))

    resolutions = 0
    for obj in document["objects"]:
        for ref in obj.get("ground_refs", []):
            if ref.get("provider") == "git-object":
                resolve_git_ground_ref(ref, repo, source_id=source_id)
                resolutions += 1
    return {
        "valid": True,
        "objects": len(document["objects"]),
        "connections": len(document["connections"]),
        "resolved": resolutions,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project a Git repository into Canvas 0.1")
    sub = parser.add_subparsers(dest="command", required=True)

    project = sub.add_parser("project")
    project.add_argument("repo")
    project.add_argument("--source-id")
    project.add_argument("--revision", default="HEAD")
    project.add_argument("--output", required=True)
    project.add_argument("--html")

    verify = sub.add_parser("verify")
    verify.add_argument("canvas")
    verify.add_argument("repo")
    verify.add_argument("--source-id")
    verify.add_argument("--schema", default="schema/canvas-0.1.schema.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "project":
        document, summary = project_git_repository(
            args.repo,
            source_id=args.source_id,
            revision=args.revision,
        )
        canvas01.save_json(document, args.output)
        if args.html:
            render_html(document, args.html)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    document = canvas01.load_json(args.canvas)
    result = verify_document(
        document,
        args.repo,
        source_id=args.source_id,
        schema_path=args.schema,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except canvas01.CanvasError as exc:
        print(f"Canvas error: {exc}")
        raise SystemExit(2)
