from __future__ import annotations

import argparse
import html
import json
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

import canvas01
import card_render


class RepoCanvasError(canvas01.CanvasError):
    pass


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "git command failed"
        raise RepoCanvasError(f"git {' '.join(args)}: {detail}")
    return proc.stdout.strip()


def _git_bytes(repo: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", *args], cwd=repo, check=False,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip() or "git command failed"
        raise RepoCanvasError(f"git {' '.join(args)}: {detail}")
    return proc.stdout


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
        entries.append({
            "path": path,
            "type": object_type,
            "sha": sha,
            "mode": mode,
            "size": None if size_text == "-" else int(size_text),
        })
    entries.sort(key=lambda item: item["path"])
    return {"repo_path": str(repo_path), "commit": commit, "root_tree": root_tree, "entries": entries}


def _parent_path(path: str) -> str | None:
    if path == ".":
        return None
    parent = str(PurePosixPath(path).parent)
    return "." if parent in ("", ".") else parent


def _layout(entries: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    # The layout is deterministic presentation, not repository semantics.
    # Blob cards are intentionally large enough to render their resolved bytes.
    bounds: dict[str, dict[str, float]] = {}
    y = 64.0
    for entry in sorted(entries, key=lambda item: item["path"]):
        path = entry["path"]
        depth = 0 if path == "." else len(PurePosixPath(path).parts)
        is_tree = entry["type"] == "tree"
        width = 300.0 if is_tree else 420.0
        height = 116.0 if is_tree else 300.0
        bounds[path] = {
            "x": 80.0 + depth * 470.0,
            "y": y,
            "width": width,
            "height": height,
        }
        y += height + 42.0
    return bounds


def project_git_repository(
    repo: str | Path, *, source_id: str | None = None,
    revision: str = "HEAD", canvas_id: str | None = None,
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
        objects.append({
            "object_id": _id("git", path),
            "kind": "reference",
            "label": source if path == "." else path,
            "placement": {"board_id": "repo", "bounds": layout[path]},
            "ground_refs": [{
                "provider": "git-object",
                "id": f"{source}#{path}",
                "version": commit,
                "digest": entry["sha"],
            }],
        })

    paths = {entry["path"] for entry in entries}
    connections: list[dict[str, Any]] = []
    for entry in entries:
        path = entry["path"]
        parent = _parent_path(path)
        if parent is None:
            continue
        if parent not in paths:
            raise RepoCanvasError(f"Git tree is missing parent {parent!r} for {path!r}")
        connections.append({
            "connection_id": _id("contains", path),
            "from": {"object_id": _id("git", parent)},
            "to": {"object_id": _id("git", path)},
            "kind": "contains",
            "direction": "directed",
        })

    document = {
        "schema_version": "0.1",
        "canvas_id": canvas_id or f"git-repo:{source}@{commit}",
        # 0.1 still stores placement through the historical `boards` field.
        # The repository projection is a Canvas field, not an authored Board premise.
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
    ground_ref: dict[str, Any], repo: str | Path, source_id: str | None = None,
) -> dict[str, Any]:
    if ground_ref.get("provider") != "git-object":
        raise RepoCanvasError(f"Not a git-object GroundRef: {ground_ref.get('provider')}")
    repo_path = Path(repo).resolve()
    source = source_id or repo_path.name
    raw_id = str(ground_ref["id"])
    prefix = f"{source}#"
    if not raw_id.startswith(prefix):
        raise RepoCanvasError(f"GroundRef source {raw_id!r} does not match {source!r}")

    path = raw_id[len(prefix):]
    version = ground_ref.get("version")
    digest = ground_ref.get("digest")
    if not version or not digest:
        raise RepoCanvasError("git-object GroundRef requires exact version and digest")
    actual_commit = _git(repo_path, "rev-parse", f"{version}^{{commit}}")
    if actual_commit != version:
        raise RepoCanvasError("git-object version did not resolve to the exact commit")
    actual_sha = (
        _git(repo_path, "rev-parse", f"{version}^{{tree}}")
        if path == "." else _git(repo_path, "rev-parse", f"{version}:{path}")
    )
    if actual_sha != digest:
        raise RepoCanvasError(f"git-object digest mismatch for {path}: expected {digest}, got {actual_sha}")
    object_type = _git(repo_path, "cat-file", "-t", actual_sha)
    return {
        "provider": "git-object", "id": raw_id, "version": version,
        "digest": digest, "exists": True, "object_type": object_type, "path": path,
    }


def resolve_git_blob_bytes(
    ground_ref: dict[str, Any], repo: str | Path, source_id: str | None = None,
) -> bytes:
    resolved = resolve_git_ground_ref(ground_ref, repo, source_id=source_id)
    if resolved["object_type"] != "blob":
        raise RepoCanvasError(f"GroundRef is not a blob: {resolved['path']}")
    return _git_bytes(Path(repo).resolve(), "cat-file", "blob", resolved["digest"])


def _tree_render(child_count: int) -> dict[str, Any]:
    noun = "child" if child_count == 1 else "children"
    return {
        "renderer": "tree",
        "size": None,
        "truncated": False,
        "body": (
            '<div class="render-body tree-render">'
            '<div class="tree-glyph" aria-hidden="true"><span></span><span></span><span></span></div>'
            f'<strong>{child_count} immediate {noun}</strong>'
            '<span>Git tree · structural module</span>'
            '</div>'
        ),
    }


def render_html(
    document: dict[str, Any], output: str | Path, *,
    repo: str | Path | None = None, source_id: str | None = None,
) -> None:
    # View state and rendered provider bytes are presentation-only. Neither is
    # written back into the Canvas document.
    objects = {obj["object_id"]: obj for obj in document["objects"]}
    children: dict[str, list[str]] = {object_id: [] for object_id in objects}
    parents: dict[str, str] = {}
    for connection in document["connections"]:
        if connection["kind"] != "contains":
            continue
        source_object = connection["from"]["object_id"]
        target_object = connection["to"]["object_id"]
        children.setdefault(source_object, []).append(target_object)
        parents[target_object] = source_object
    for values in children.values():
        values.sort()
    tree_ids = {object_id for object_id, values in children.items() if values}

    max_x = max((o["placement"]["bounds"]["x"] + o["placement"]["bounds"]["width"] for o in objects.values()), default=800) + 100
    max_y = max((o["placement"]["bounds"]["y"] + o["placement"]["bounds"]["height"] for o in objects.values()), default=600) + 100

    edges: list[str] = []
    for connection in document["connections"]:
        if connection["kind"] != "contains":
            continue
        source_object = connection["from"]["object_id"]
        target_object = connection["to"]["object_id"]
        source = objects[source_object]["placement"]["bounds"]
        target = objects[target_object]["placement"]["bounds"]
        x1 = source["x"] + source["width"]
        y1 = source["y"] + source["height"] / 2
        x2 = target["x"]
        y2 = target["y"] + target["height"] / 2
        edges.append(
            f'<path class="edge" data-from="{html.escape(source_object, quote=True)}" '
            f'data-to="{html.escape(target_object, quote=True)}" '
            f'd="M {x1} {y1} C {x1 + 70} {y1}, {x2 - 70} {y2}, {x2} {y2}" />'
        )

    cards: list[str] = []
    client_objects: dict[str, dict[str, Any]] = {}
    for object_id, obj in objects.items():
        bounds = obj["placement"]["bounds"]
        ref = obj.get("ground_refs", [{}])[0]
        raw_ref_id = str(ref.get("id", ""))
        label_raw = obj.get("label", object_id)
        path = raw_ref_id.partition("#")[2] or label_raw
        digest = str(ref.get("digest", ""))
        version = str(ref.get("version", ""))
        is_tree = object_id in tree_ids

        if is_tree:
            rendering = _tree_render(len(children.get(object_id, [])))
        elif repo is not None and ref.get("provider") == "git-object":
            rendering = card_render.render_bytes(
                path,
                resolve_git_blob_bytes(ref, repo, source_id=source_id),
            )
        else:
            rendering = card_render.render_unresolved(path)

        renderer = str(rendering["renderer"])
        size = rendering.get("size")
        size_text = "" if size is None else f" · {int(size):,} bytes"
        kind_label = "TREE" if is_tree else renderer.upper()
        card_class = "tree" if is_tree else "blob"
        cards.append(
            f'<article class="card {card_class} render-{html.escape(renderer, quote=True)}" '
            f'style="left:{bounds["x"]}px;top:{bounds["y"]}px;width:{bounds["width"]}px;height:{bounds["height"]}px" '
            f'data-object-id="{html.escape(object_id, quote=True)}" data-path="{html.escape(path.lower(), quote=True)}" '
            f'data-renderer="{html.escape(renderer, quote=True)}" tabindex="0" role="button" '
            f'aria-label="Inspect {html.escape(path, quote=True)}">'
            '<div class="card-chrome">'
            f'<span class="card-kind">{kind_label}</span>'
            f'<strong title="{html.escape(path, quote=True)}">{html.escape(label_raw)}</strong>'
            f'<span class="card-meta">{html.escape(digest[:12])}{size_text}</span>'
            '</div>'
            f'{rendering["body"]}'
            '</article>'
        )
        client_objects[object_id] = {
            "label": label_raw,
            "path": path,
            "type": "tree" if is_tree else "blob",
            "renderer": renderer,
            "size": size,
            "digest": digest,
            "version": version,
        }

    surface_label_raw = document["boards"][0]["label"] if document["boards"] else document["canvas_id"]
    surface_label = html.escape(surface_label_raw)
    client_data = json.dumps(
        {"objects": client_objects, "children": children, "parents": parents},
        sort_keys=True, separators=(",", ":"),
    ).replace("<", "\\u003c")

    page = f'''<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{surface_label} — Canvas</title>
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
.card {{ position:absolute; display:flex; flex-direction:column; border:1px solid #3b4350; border-radius:14px; background:#1d212a; overflow:hidden; cursor:pointer; box-shadow:0 10px 30px rgba(0,0,0,.18); }}
.card.tree {{ border-left:4px solid #8a93a3; }}
.card.blob {{ border-left:4px solid #596271; }}
.card.hidden {{ display:none; }}
.card.selected {{ outline:3px solid #c3cad5; outline-offset:3px; }}
.card-chrome {{ flex:0 0 auto; display:grid; grid-template-columns:auto minmax(0,1fr); gap:4px 9px; align-items:center; padding:10px 12px; border-bottom:1px solid #343b47; background:#20252e; }}
.card-kind {{ grid-row:1 / span 2; min-width:44px; padding:5px 7px; border:1px solid #454e5c; border-radius:7px; color:#c8ced8; font-size:9px; letter-spacing:.08em; text-align:center; }}
.card-chrome strong {{ min-width:0; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.card-meta {{ color:#8f98a6; font-size:10px; }}
.render-body {{ flex:1 1 auto; min-height:0; position:relative; overflow:hidden; }}
.text-render {{ background:#12151b; }}
.text-render pre {{ margin:0; height:100%; padding:12px 14px; overflow:hidden; white-space:pre; color:#d7dce5; font:10px/1.45 ui-monospace, SFMono-Regular, Consolas, monospace; tab-size:2; }}
.render-truncated {{ position:absolute; right:8px; bottom:8px; padding:3px 6px; border-radius:6px; background:#242a34; color:#9ca5b3; font-size:9px; }}
.html-render {{ background:white; }}
.html-render iframe {{ width:100%; height:100%; border:0; display:block; pointer-events:none; background:white; }}
.tree-render, .binary-render, .unresolved-render {{ display:flex; flex-direction:column; align-items:center; justify-content:center; gap:7px; padding:12px; color:#aeb6c2; text-align:center; }}
.tree-render strong, .binary-render strong {{ color:#e8ebf0; font-size:13px; }}
.tree-render span, .binary-render span, .unresolved-render span {{ font-size:10px; }}
.tree-glyph {{ display:flex; gap:5px; align-items:end; height:28px; }}
.tree-glyph span {{ display:block; width:22px; border:1px solid #737d8d; border-radius:5px 5px 2px 2px; background:#252b35; }}
.tree-glyph span:nth-child(1) {{ height:17px; }} .tree-glyph span:nth-child(2) {{ height:28px; }} .tree-glyph span:nth-child(3) {{ height:21px; }}
.binary-glyph {{ display:grid; place-items:center; width:42px; height:42px; border:1px solid #596271; border-radius:10px; font:11px ui-monospace, monospace; }}
.unresolved-render code {{ max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:10px; }}
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
@media (max-width: 820px) {{ .workspace {{ grid-template-columns:1fr; grid-template-rows:minmax(0,1fr) auto; }} .inspector {{ max-height:36vh; border-left:0; border-top:1px solid #333945; }} }}
</style>
<header>
  <strong>{surface_label}</strong>
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
  <div class="viewport" id="viewport" tabindex="0" aria-label="Repository Canvas field">
    <div class="world" id="world">
      <svg viewBox="0 0 {max_x} {max_y}" preserveAspectRatio="none">{''.join(edges)}</svg>
      {''.join(cards)}
    </div>
  </div>
  <aside class="inspector" aria-live="polite">
    <h2 id="detail-title">Repository object</h2>
    <p id="detail-empty" class="muted">Select an object on the Canvas.</p>
    <div id="detail" hidden>
      <dl>
        <dt>Path</dt><dd id="detail-path"></dd>
        <dt>Git object</dt><dd id="detail-type"></dd>
        <dt>Card renderer</dt><dd id="detail-renderer"></dd>
        <dt>Bytes</dt><dd id="detail-size"></dd>
        <dt>Digest</dt><dd id="detail-digest"></dd>
        <dt>Pinned revision</dt><dd id="detail-version"></dd>
      </dl>
      <div class="context">
        <button type="button" class="control" id="center-selected">Center selected</button>
        <button type="button" class="control" id="toggle-subtree">Collapse subtree</button>
        <button type="button" class="control" id="show-all">Expand all</button>
      </div>
      <div class="context"><strong>Parent</strong><div id="parent-link" class="context-list"></div></div>
      <div class="context"><strong>Children</strong><div id="children-links" class="context-list"></div></div>
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
  const minScale = 0.05;
  const maxScale = 4;
  let selected = null, scale = 1, panX = 0, panY = 0;

  const detail = document.getElementById('detail');
  const detailEmpty = document.getElementById('detail-empty');
  const detailTitle = document.getElementById('detail-title');
  const detailPath = document.getElementById('detail-path');
  const detailType = document.getElementById('detail-type');
  const detailRenderer = document.getElementById('detail-renderer');
  const detailSize = document.getElementById('detail-size');
  const detailDigest = document.getElementById('detail-digest');
  const detailVersion = document.getElementById('detail-version');
  const parentLink = document.getElementById('parent-link');
  const childrenLinks = document.getElementById('children-links');
  const toggleSubtree = document.getElementById('toggle-subtree');

  function descendants(id) {{ const result=new Set(), queue=[...(graph.children[id]||[])]; while(queue.length){{const current=queue.shift(); if(result.has(current))continue; result.add(current); queue.push(...(graph.children[current]||[]));}} return result; }}
  function ancestorClosure(ids) {{ const result=new Set(ids); for(const id of [...ids]){{let current=graph.parents[id]; while(current){{result.add(current); current=graph.parents[current];}}}} return result; }}
  function visibleIds() {{
    const query=filter.value.trim().toLowerCase();
    if(query){{const matches=new Set(); for(const [id,meta] of Object.entries(graph.objects)) if(meta.path.toLowerCase().includes(query)||meta.label.toLowerCase().includes(query)) matches.add(id); return ancestorClosure(matches);}}
    const hidden=new Set(); for(const id of collapsed) for(const child of descendants(id)) hidden.add(child); return new Set([...allIds].filter(id=>!hidden.has(id)));
  }}
  function updateStatus() {{ status.textContent=`${{visibleIds().size}} shown · ${{Math.round(scale*100)}}%`; }}
  function applyView() {{ world.style.transform=`translate(${{panX}}px, ${{panY}}px) scale(${{scale}})`; const grid=24*scale; viewport.style.backgroundSize=`${{grid}}px ${{grid}}px`; viewport.style.backgroundPosition=`${{panX}}px ${{panY}}px`; updateStatus(); }}
  function updateVisibility() {{ const visible=visibleIds(); for(const card of cards){{const id=card.dataset.objectId; card.classList.toggle('hidden',!visible.has(id)); card.classList.toggle('selected',id===selected);}} for(const edge of edges) edge.classList.toggle('hidden',!visible.has(edge.dataset.from)||!visible.has(edge.dataset.to)); updateStatus(); }}
  function navButton(id) {{ const meta=graph.objects[id], button=document.createElement('button'); button.type='button'; button.className='control'; button.textContent=meta.path; button.addEventListener('click',()=>selectObject(id,true)); return button; }}
  function renderInspector() {{
    if(!selected||!graph.objects[selected]){{detail.hidden=true; detailEmpty.hidden=false; detailTitle.textContent='Repository object'; return;}}
    const meta=graph.objects[selected]; detail.hidden=false; detailEmpty.hidden=true; detailTitle.textContent=meta.label; detailPath.textContent=meta.path; detailType.textContent=meta.type; detailRenderer.textContent=meta.renderer; detailSize.textContent=meta.size==null?'—':`${{meta.size.toLocaleString()}} bytes`; detailDigest.textContent=meta.digest; detailVersion.textContent=meta.version;
    parentLink.replaceChildren(); const parent=graph.parents[selected]; if(parent)parentLink.appendChild(navButton(parent)); else parentLink.textContent='Repository root';
    childrenLinks.replaceChildren(); const childIds=graph.children[selected]||[]; if(childIds.length) for(const child of childIds) childrenLinks.appendChild(navButton(child)); else childrenLinks.textContent='No children';
    toggleSubtree.disabled=childIds.length===0; toggleSubtree.textContent=collapsed.has(selected)?'Expand subtree':'Collapse subtree';
  }}
  function clampScale(value) {{ return Math.max(minScale,Math.min(maxScale,value)); }}
  function zoomAt(nextScale,clientX,clientY) {{ const bounded=clampScale(nextScale), rect=viewport.getBoundingClientRect(), sx=clientX-rect.left, sy=clientY-rect.top, worldX=(sx-panX)/scale, worldY=(sy-panY)/scale; scale=bounded; panX=sx-worldX*scale; panY=sy-worldY*scale; applyView(); }}
  function zoomFromCenter(factor) {{ const rect=viewport.getBoundingClientRect(); zoomAt(scale*factor,rect.left+rect.width/2,rect.top+rect.height/2); }}
  function fitAll() {{ const margin=64, aw=Math.max(1,viewport.clientWidth-margin*2), ah=Math.max(1,viewport.clientHeight-margin*2); scale=clampScale(Math.min(1,aw/baseWidth,ah/baseHeight)); panX=(viewport.clientWidth-baseWidth*scale)/2; panY=(viewport.clientHeight-baseHeight*scale)/2; applyView(); }}
  function centerSelected() {{ if(!selected)return; const card=cardsById.get(selected); if(!card)return; panX=viewport.clientWidth/2-(card.offsetLeft+card.offsetWidth/2)*scale; panY=viewport.clientHeight/2-(card.offsetTop+card.offsetHeight/2)*scale; applyView(); }}
  function selectObject(id,center=false) {{ selected=id; updateVisibility(); renderInspector(); if(center)centerSelected(); }}

  for(const card of cards){{ card.addEventListener('click',()=>selectObject(card.dataset.objectId)); card.addEventListener('keydown',event=>{{if(event.key==='Enter'||event.key===' '){{event.preventDefault(); selectObject(card.dataset.objectId);}}}}); }}
  filter.addEventListener('input',updateVisibility);
  document.getElementById('zoom-out').addEventListener('click',()=>zoomFromCenter(1/1.2));
  document.getElementById('zoom-in').addEventListener('click',()=>zoomFromCenter(1.2));
  document.getElementById('fit').addEventListener('click',fitAll);
  document.getElementById('reset').addEventListener('click',()=>{{filter.value=''; collapsed.clear(); selected=null; updateVisibility(); renderInspector(); fitAll();}});
  document.getElementById('center-selected').addEventListener('click',centerSelected);
  toggleSubtree.addEventListener('click',()=>{{if(!selected)return; if(collapsed.has(selected))collapsed.delete(selected); else collapsed.add(selected); updateVisibility(); renderInspector();}});
  document.getElementById('show-all').addEventListener('click',()=>{{collapsed.clear(); filter.value=''; updateVisibility(); renderInspector();}});
  viewport.addEventListener('wheel',event=>{{event.preventDefault(); zoomAt(scale*Math.exp(-event.deltaY*0.0015),event.clientX,event.clientY);}},{{passive:false}});

  let drag=null;
  viewport.addEventListener('pointerdown',event=>{{if(event.target.closest('.card,button,input,iframe'))return; drag={{x:event.clientX,y:event.clientY,panX,panY}}; viewport.classList.add('dragging'); viewport.setPointerCapture(event.pointerId);}});
  viewport.addEventListener('pointermove',event=>{{if(!drag)return; panX=drag.panX+(event.clientX-drag.x); panY=drag.panY+(event.clientY-drag.y); applyView();}});
  function endDrag(event){{if(!drag)return; drag=null; viewport.classList.remove('dragging'); if(viewport.hasPointerCapture(event.pointerId))viewport.releasePointerCapture(event.pointerId);}}
  viewport.addEventListener('pointerup',endDrag); viewport.addEventListener('pointercancel',endDrag);
  window.addEventListener('resize',()=>{{if(!selected)fitAll();}});
  updateVisibility(); renderInspector(); requestAnimationFrame(fitAll);
}})();
</script>
'''
    Path(output).write_text(page, encoding="utf-8")


def verify_document(
    document: dict[str, Any], repo: str | Path, *, source_id: str | None,
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
    return {"valid": True, "objects": len(document["objects"]), "connections": len(document["connections"]), "resolved": resolutions}


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
        document, summary = project_git_repository(args.repo, source_id=args.source_id, revision=args.revision)
        canvas01.save_json(document, args.output)
        if args.html:
            render_html(document, args.html, repo=args.repo, source_id=args.source_id)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    document = canvas01.load_json(args.canvas)
    result = verify_document(document, args.repo, source_id=args.source_id, schema_path=args.schema)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except canvas01.CanvasError as exc:
        print(f"Canvas error: {exc}")
        raise SystemExit(2)
