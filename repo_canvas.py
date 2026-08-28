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
    # View state is intentionally local to the renderer. Pan, zoom, selection,
    # collapse and filtering never write back to the Canvas document.
    objects = {obj["object_id"]: obj for obj in document["objects"]}
    children: dict[str, list[str]] = {object_id: [] for object_id in objects}
    parents: dict[str, str] = {}
    for connection in document["connections"]:
        if connection["kind"] != "contains":
            continue
        source_id = connection["from"]["object_id"]
        target_id = connection["to"]["object_id"]
        children.setdefault(source_id, []).append(target_id)
        parents[target_id] = source_id
    for values in children.values():
        values.sort()

    tree_ids = {object_id for object_id, values in children.items() if values}
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
        source_id = connection["from"]["object_id"]
        target_id = connection["to"]["object_id"]
        source = objects[source_id]["placement"]["bounds"]
        target = objects[target_id]["placement"]["bounds"]
        x1 = source["x"] + source["width"]
        y1 = source["y"] + source["height"] / 2
        x2 = target["x"]
        y2 = target["y"] + target["height"] / 2
        lines.append(
            f'<path class="edge" data-from="{html.escape(source_id, quote=True)}" '
            f'data-to="{html.escape(target_id, quote=True)}" '
            f'd="M {x1} {y1} C {x1 + 60} {y1}, {x2 - 60} {y2}, {x2} {y2}" />'
        )

    cards: list[str] = []
    client_objects: dict[str, dict[str, Any]] = {}
    for object_id, obj in objects.items():
        bounds = obj["placement"]["bounds"]
        object_class = "tree" if object_id in tree_ids else "blob"
        label_raw = obj.get("label", object_id)
        label = html.escape(label_raw)
        ref = obj.get("ground_refs", [{}])[0]
        raw_ref_id = str(ref.get("id", ""))
        path = raw_ref_id.partition("#")[2] or label_raw
        digest_raw = str(ref.get("digest", ""))
        version_raw = str(ref.get("version", ""))
        cards.append(
            f'<button type="button" class="card {object_class}" '
            f'style="left:{bounds["x"]}px;top:{bounds["y"]}px;'
            f'width:{bounds["width"]}px;height:{bounds["height"]}px" '
            f'data-object-id="{html.escape(object_id, quote=True)}" '
            f'data-path="{html.escape(path.lower(), quote=True)}" '
            f'aria-label="Inspect {html.escape(path, quote=True)}">'
            f'<strong>{label}</strong><span>{object_class} · {html.escape(digest_raw[:12])}</span></button>'
        )
        client_objects[object_id] = {
            "label": label_raw,
            "path": path,
            "type": object_class,
            "digest": digest_raw,
            "version": version_raw,
        }

    board_label_raw = (
        document["boards"][0]["label"] if document["boards"] else document["canvas_id"]
    )
    board_label = html.escape(board_label_raw)
    client_data = json.dumps(
        {"objects": client_objects, "children": children, "parents": parents},
        sort_keys=True,
        separators=(",", ":"),
    ).replace("<", "\\u003c")

    page = f'''<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{board_label} — Canvas</title>
<style>
:root {{ color-scheme: dark; font-family: ui-sans-serif, system-ui, sans-serif; }}
* {{ box-sizing:border-box; }}
html, body {{ width:100%; height:100%; overflow:hidden; }}
body {{ margin:0; background:#111318; color:#e8ebf0; }}
header {{ position:relative; z-index:10; display:flex; flex-wrap:wrap; gap:10px; align-items:center; padding:10px 12px; background:#181b22; border-bottom:1px solid #333945; }}
header strong {{ white-space:nowrap; }}
header .count {{ color:#a8b0bd; white-space:nowrap; font-size:12px; }}
.toolbar {{ display:flex; flex:1; min-width:280px; gap:6px; align-items:center; }}
input {{ min-width:180px; flex:1; padding:8px 10px; border:1px solid #444b59; border-radius:8px; background:#101218; color:inherit; font-size:16px; }}
button {{ color:inherit; font:inherit; }}
.control {{ min-height:38px; padding:7px 10px; border:1px solid #444b59; border-radius:8px; background:#20242d; cursor:pointer; }}
.control:disabled {{ opacity:.45; cursor:not-allowed; }}
.workspace {{ display:grid; grid-template-columns:minmax(0,1fr) 320px; height:calc(100vh - 59px); min-height:0; }}
.viewport {{ position:relative; overflow:hidden; min-width:0; min-height:0; cursor:grab; touch-action:none; background-color:#111318; background-image:radial-gradient(#2d3340 1px, transparent 1px); background-size:24px 24px; }}
.viewport.dragging {{ cursor:grabbing; user-select:none; }}
.world {{ position:absolute; left:0; top:0; width:{max_x}px; height:{max_y}px; transform-origin:0 0; will-change:transform; }}
svg {{ position:absolute; inset:0; width:100%; height:100%; pointer-events:none; overflow:visible; }}
.edge {{ fill:none; stroke:#505968; stroke-width:1.5; }}
.edge.hidden {{ display:none; }}
.card {{ position:absolute; display:block; box-sizing:border-box; padding:9px 11px; border:1px solid #3b4350; border-radius:9px; background:#1d212a; text-align:left; overflow:hidden; cursor:pointer; }}
.card.tree {{ border-left:4px solid #8a93a3; }}
.card.blob {{ border-left:4px solid #596271; }}
.card strong {{ display:block; font-size:12px; line-height:1.25; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.card span {{ display:block; margin-top:7px; color:#a8b0bd; font-size:10px; }}
.card.hidden {{ display:none; }}
.card.selected {{ outline:3px solid #c3cad5; outline-offset:2px; }}
.inspector {{ min-height:0; overflow:auto; border-left:1px solid #333945; background:#15181f; padding:16px; }}
.inspector h2 {{ margin:0 0 12px; font-size:16px; }}
.inspector dl {{ margin:0; }}
.inspector dt {{ margin-top:12px; color:#8f98a6; font-size:11px; text-transform:uppercase; letter-spacing:.05em; }}
.inspector dd {{ margin:4px 0 0; word-break:break-word; font-size:13px; }}
.context {{ margin-top:16px; border-top:1px solid #303641; padding-top:12px; }}
.context button {{ width:100%; margin-top:6px; text-align:left; }}
.context-list {{ max-height:240px; overflow:auto; }}
.muted {{ color:#8f98a6; }}
#status {{ min-width:120px; text-align:right; color:#a8b0bd; font-size:12px; }}
@media (max-width: 820px) {{
  .workspace {{ grid-template-columns:1fr; grid-template-rows:minmax(0,1fr) auto; }}
  .inspector {{ max-height:36vh; border-left:0; border-top:1px solid #333945; }}
}}
</style>
<header>
  <strong>{board_label}</strong>
  <span class="count">{len(objects)} objects · {len(document["connections"])} connections</span>
  <div class="toolbar">
    <input id="filter" aria-label="Filter repository paths" placeholder="Filter paths">
    <button type="button" class="control" id="zoom-out" aria-label="Zoom out">−</button>
    <button type="button" class="control" id="zoom-in" aria-label="Zoom in">+</button>
    <button type="button" class="control" id="fit">Fit all</button>
    <button type="button" class="control" id="reset">Reset view</button>
    <span id="status" aria-live="polite"></span>
  </div>
</header>
<div class="workspace">
  <div class="viewport" id="viewport" tabindex="0" aria-label="Repository infinite Canvas board">
    <div class="world" id="world">
      <svg viewBox="0 0 {max_x} {max_y}" preserveAspectRatio="none">{''.join(lines)}</svg>
      {''.join(cards)}
    </div>
  </div>
  <aside class="inspector" aria-live="polite">
    <h2 id="detail-title">Repository object</h2>
    <p id="detail-empty" class="muted">Select a tree or blob on the board.</p>
    <div id="detail" hidden>
      <dl>
        <dt>Path</dt><dd id="detail-path"></dd>
        <dt>Git object</dt><dd id="detail-type"></dd>
        <dt>Digest</dt><dd id="detail-digest"></dd>
        <dt>Pinned revision</dt><dd id="detail-version"></dd>
      </dl>
      <div class="context">
        <button type="button" class="control" id="center-selected">Center selected</button>
        <button type="button" class="control" id="toggle-subtree">Collapse subtree</button>
        <button type="button" class="control" id="show-all">Expand all</button>
      </div>
      <div class="context">
        <strong>Parent</strong>
        <div id="parent-link" class="context-list"></div>
      </div>
      <div class="context">
        <strong>Children</strong>
        <div id="children-links" class="context-list"></div>
      </div>
    </div>
  </aside>
</div>
<script type="application/json" id="graph-data">{client_data}</script>
<script>
(() => {{
  const graph = JSON.parse(document.getElementById('graph-data').textContent);
  const viewport = document.getElementById('viewport');
  const world = document.getElementById('world');
  const filter = document.getElementById('filter');
  const status = document.getElementById('status');
  const cards = [...document.querySelectorAll('.card')];
  const edges = [...document.querySelectorAll('.edge')];
  const cardsById = new Map(cards.map(card => [card.dataset.objectId, card]));
  const allIds = new Set(cardsById.keys());
  const collapsed = new Set();
  const baseWidth = {max_x};
  const baseHeight = {max_y};
  const minScale = 0.08;
  const maxScale = 4;
  let selected = null;
  let scale = 1;
  let panX = 0;
  let panY = 0;

  const detail = document.getElementById('detail');
  const detailEmpty = document.getElementById('detail-empty');
  const detailTitle = document.getElementById('detail-title');
  const detailPath = document.getElementById('detail-path');
  const detailType = document.getElementById('detail-type');
  const detailDigest = document.getElementById('detail-digest');
  const detailVersion = document.getElementById('detail-version');
  const parentLink = document.getElementById('parent-link');
  const childrenLinks = document.getElementById('children-links');
  const toggleSubtree = document.getElementById('toggle-subtree');

  function descendants(id) {{
    const result = new Set();
    const queue = [...(graph.children[id] || [])];
    while (queue.length) {{
      const current = queue.shift();
      if (result.has(current)) continue;
      result.add(current);
      queue.push(...(graph.children[current] || []));
    }}
    return result;
  }}

  function ancestorClosure(ids) {{
    const result = new Set(ids);
    for (const id of [...ids]) {{
      let current = graph.parents[id];
      while (current) {{
        result.add(current);
        current = graph.parents[current];
      }}
    }}
    return result;
  }}

  function visibleIds() {{
    const query = filter.value.trim().toLowerCase();
    if (query) {{
      const matches = new Set();
      for (const [id, meta] of Object.entries(graph.objects)) {{
        if (meta.path.toLowerCase().includes(query) || meta.label.toLowerCase().includes(query)) matches.add(id);
      }}
      return ancestorClosure(matches);
    }}
    const hidden = new Set();
    for (const id of collapsed) for (const child of descendants(id)) hidden.add(child);
    return new Set([...allIds].filter(id => !hidden.has(id)));
  }}

  function updateStatus() {{
    status.textContent = `${{visibleIds().size}} shown · ${{Math.round(scale * 100)}}%`;
  }}

  function applyView() {{
    world.style.transform = `translate(${{panX}}px, ${{panY}}px) scale(${{scale}})`;
    const grid = 24 * scale;
    viewport.style.backgroundSize = `${{grid}}px ${{grid}}px`;
    viewport.style.backgroundPosition = `${{panX}}px ${{panY}}px`;
    updateStatus();
  }}

  function updateVisibility() {{
    const visible = visibleIds();
    for (const card of cards) {{
      const id = card.dataset.objectId;
      card.classList.toggle('hidden', !visible.has(id));
      card.classList.toggle('selected', id === selected);
    }}
    for (const edge of edges) {{
      edge.classList.toggle('hidden', !visible.has(edge.dataset.from) || !visible.has(edge.dataset.to));
    }}
    updateStatus();
  }}

  function navButton(id) {{
    const meta = graph.objects[id];
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'control';
    button.textContent = meta.path;
    button.addEventListener('click', () => selectObject(id, true));
    return button;
  }}

  function renderInspector() {{
    if (!selected || !graph.objects[selected]) {{
      detail.hidden = true;
      detailEmpty.hidden = false;
      detailTitle.textContent = 'Repository object';
      return;
    }}
    const meta = graph.objects[selected];
    detail.hidden = false;
    detailEmpty.hidden = true;
    detailTitle.textContent = meta.label;
    detailPath.textContent = meta.path;
    detailType.textContent = meta.type;
    detailDigest.textContent = meta.digest;
    detailVersion.textContent = meta.version;

    parentLink.replaceChildren();
    const parent = graph.parents[selected];
    if (parent) parentLink.appendChild(navButton(parent));
    else parentLink.textContent = 'Repository root';

    childrenLinks.replaceChildren();
    const childIds = graph.children[selected] || [];
    if (childIds.length) {{
      for (const child of childIds) childrenLinks.appendChild(navButton(child));
    }} else {{
      childrenLinks.textContent = 'No children';
    }}

    toggleSubtree.disabled = childIds.length === 0;
    toggleSubtree.textContent = collapsed.has(selected) ? 'Expand subtree' : 'Collapse subtree';
  }}

  function clampScale(value) {{
    return Math.max(minScale, Math.min(maxScale, value));
  }}

  function zoomAt(nextScale, clientX, clientY) {{
    const bounded = clampScale(nextScale);
    const rect = viewport.getBoundingClientRect();
    const sx = clientX - rect.left;
    const sy = clientY - rect.top;
    const worldX = (sx - panX) / scale;
    const worldY = (sy - panY) / scale;
    scale = bounded;
    panX = sx - worldX * scale;
    panY = sy - worldY * scale;
    applyView();
  }}

  function zoomFromCenter(factor) {{
    const rect = viewport.getBoundingClientRect();
    zoomAt(scale * factor, rect.left + rect.width / 2, rect.top + rect.height / 2);
  }}

  function fitAll() {{
    const margin = 64;
    const availableWidth = Math.max(1, viewport.clientWidth - margin * 2);
    const availableHeight = Math.max(1, viewport.clientHeight - margin * 2);
    scale = clampScale(Math.min(1, availableWidth / baseWidth, availableHeight / baseHeight));
    panX = (viewport.clientWidth - baseWidth * scale) / 2;
    panY = (viewport.clientHeight - baseHeight * scale) / 2;
    applyView();
  }}

  function centerSelected() {{
    if (!selected) return;
    const card = cardsById.get(selected);
    if (!card) return;
    const centerX = card.offsetLeft + card.offsetWidth / 2;
    const centerY = card.offsetTop + card.offsetHeight / 2;
    panX = viewport.clientWidth / 2 - centerX * scale;
    panY = viewport.clientHeight / 2 - centerY * scale;
    applyView();
  }}

  function selectObject(id, center = false) {{
    selected = id;
    updateVisibility();
    renderInspector();
    if (center) centerSelected();
  }}

  for (const card of cards) card.addEventListener('click', () => selectObject(card.dataset.objectId));
  filter.addEventListener('input', updateVisibility);
  document.getElementById('zoom-out').addEventListener('click', () => zoomFromCenter(1 / 1.2));
  document.getElementById('zoom-in').addEventListener('click', () => zoomFromCenter(1.2));
  document.getElementById('fit').addEventListener('click', fitAll);
  document.getElementById('reset').addEventListener('click', () => {{
    filter.value = '';
    collapsed.clear();
    selected = null;
    updateVisibility();
    renderInspector();
    fitAll();
  }});
  document.getElementById('center-selected').addEventListener('click', centerSelected);
  toggleSubtree.addEventListener('click', () => {{
    if (!selected) return;
    if (collapsed.has(selected)) collapsed.delete(selected); else collapsed.add(selected);
    updateVisibility();
    renderInspector();
  }});
  document.getElementById('show-all').addEventListener('click', () => {{
    collapsed.clear();
    filter.value = '';
    updateVisibility();
    renderInspector();
  }});

  // The canvas wheel is depth, not document movement: every wheel/trackpad
  // gesture zooms around the pointer. Panning is an explicit drag gesture.
  viewport.addEventListener('wheel', event => {{
    event.preventDefault();
    const factor = Math.exp(-event.deltaY * 0.0015);
    zoomAt(scale * factor, event.clientX, event.clientY);
  }}, {{passive:false}});

  let drag = null;
  viewport.addEventListener('pointerdown', event => {{
    if (event.target.closest('.card,button,input')) return;
    drag = {{x:event.clientX, y:event.clientY, panX, panY}};
    viewport.classList.add('dragging');
    viewport.setPointerCapture(event.pointerId);
  }});
  viewport.addEventListener('pointermove', event => {{
    if (!drag) return;
    panX = drag.panX + (event.clientX - drag.x);
    panY = drag.panY + (event.clientY - drag.y);
    applyView();
  }});
  function endDrag(event) {{
    if (!drag) return;
    drag = null;
    viewport.classList.remove('dragging');
    if (viewport.hasPointerCapture(event.pointerId)) viewport.releasePointerCapture(event.pointerId);
  }}
  viewport.addEventListener('pointerup', endDrag);
  viewport.addEventListener('pointercancel', endDrag);

  window.addEventListener('resize', () => {{
    if (!selected) fitAll();
  }});

  updateVisibility();
  renderInspector();
  requestAnimationFrame(fitAll);
}})();
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
