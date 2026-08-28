from __future__ import annotations

import argparse
import copy
import html
import json
import re
from pathlib import Path
from typing import Any

import field_view


class BoardViewError(ValueError):
    pass


CARD_WIDTH = 360.0
CARD_HEIGHT = 220.0
CARD_RELATION_Y = 76.0


def _relation_graph(document: dict[str, Any], relation_kind: str):
    objects = {obj["object_id"]: obj for obj in document.get("objects", [])}
    if not objects:
        raise BoardViewError("Board requires at least one Object")

    children: dict[str, list[str]] = {oid: [] for oid in objects}
    parents: dict[str, str] = {}
    incoming: dict[str, int] = {oid: 0 for oid in objects}
    outgoing: dict[str, int] = {oid: 0 for oid in objects}
    edges: list[dict[str, str]] = []
    for connection in document.get("connections", []):
        if connection.get("kind") != relation_kind:
            continue
        src = connection.get("from", {}).get("object_id")
        dst = connection.get("to", {}).get("object_id")
        if src not in objects or dst not in objects:
            continue
        if dst in parents and parents[dst] != src:
            raise BoardViewError(
                f"hierarchical Board relation {relation_kind!r} gives {dst!r} multiple parents"
            )
        parents[dst] = src
        children[src].append(dst)
        incoming[dst] += 1
        outgoing[src] += 1
        edges.append({
            "id": str(connection.get("connection_id", "")),
            "from": src,
            "to": dst,
            "kind": relation_kind,
        })

    def sort_key(oid: str):
        return str(objects[oid].get("label") or oid).lower()

    for ids in children.values():
        ids.sort(key=sort_key)
    roots = sorted((oid for oid in objects if oid not in parents), key=sort_key)
    if not roots:
        raise BoardViewError(f"Board relation {relation_kind!r} has no root")
    return objects, children, parents, roots, edges, incoming, outgoing


def _hierarchy_layout(
    objects: dict[str, dict[str, Any]],
    children: dict[str, list[str]],
    roots: list[str],
) -> dict[str, dict[str, float]]:
    x_step = 500.0
    y_gap = 68.0
    cursor = 190.0
    positions: dict[str, dict[str, float]] = {}
    visiting: set[str] = set()
    visited: set[str] = set()

    def place(oid: str, depth: int) -> float:
        nonlocal cursor
        if oid in visiting:
            raise BoardViewError("hierarchical Board arrangement cannot lay out a relation cycle")
        if oid in visited:
            b = positions[oid]
            return b["y"] + b["height"] / 2
        visiting.add(oid)
        kids = children.get(oid, [])
        if kids:
            centers = [place(child, depth + 1) for child in kids]
            center = (centers[0] + centers[-1]) / 2
            y = center - CARD_HEIGHT / 2
        else:
            y = cursor
            center = y + CARD_HEIGHT / 2
            cursor += CARD_HEIGHT + y_gap
        positions[oid] = {
            "x": 180.0 + depth * x_step,
            "y": y,
            "width": CARD_WIDTH,
            "height": CARD_HEIGHT,
        }
        visiting.remove(oid)
        visited.add(oid)
        return center

    for root in roots:
        place(root, 0)
        cursor += 140.0

    for oid in objects:
        if oid not in positions:
            place(oid, 0)
    return positions


def materialize_board(
    document: dict[str, Any], *, board_id: str, label: str, premise: str,
    relation_kind: str = "contains",
) -> dict[str, Any]:
    """Author one premise-bearing Board from existing Objects and Connections.

    This operation changes Board composition/layout only. It creates no Objects and no Connections.
    """
    if not premise.strip():
        raise BoardViewError("Board premise must be explicit")
    result = copy.deepcopy(document)
    objects, children, _parents, roots, _edges, _incoming, _outgoing = _relation_graph(
        result, relation_kind
    )
    positions = _hierarchy_layout(objects, children, roots)

    result["boards"] = [{
        "board_id": board_id,
        "label": label,
        "premise": premise,
    }]
    for oid, obj in objects.items():
        obj["placement"] = {"board_id": board_id, "bounds": positions[oid]}

    min_x = min(b["x"] for b in positions.values())
    min_y = min(b["y"] for b in positions.values())
    max_x = max(b["x"] + b["width"] for b in positions.values())
    max_y = max(b["y"] + b["height"] for b in positions.values())
    result["frames"] = [{
        "frame_id": f"frame:{board_id}",
        "board_id": board_id,
        "label": label,
        "bounds": {
            "x": min_x - 100.0,
            "y": min_y - 130.0,
            "width": max_x - min_x + 200.0,
            "height": max_y - min_y + 230.0,
        },
        "members": list(objects),
    }]
    return result


def _object_resolution(obj: dict[str, Any], repo: Path) -> dict[str, Any]:
    refs = [ref for ref in obj.get("ground_refs", []) if ref.get("provider") == "git-object"]
    if not refs:
        return {
            "renderer": "label",
            "provider": "canvas",
            "path": str(obj.get("label") or obj["object_id"]),
            "digest": "",
            "version": "",
            "rendered": str(obj.get("content") or ""),
            "bytes": 0,
            "type": obj.get("kind", "object"),
        }
    ref = refs[0]
    resolved = field_view._resolve_git(ref, repo)
    renderer, rendered = field_view._render_kind(
        resolved["path"], resolved["type"], resolved["bytes"]
    )
    return {
        **resolved,
        "provider": str(ref.get("provider") or "git-object"),
        "renderer": renderer,
        "rendered": rendered,
        "bytes": len(resolved["bytes"]),
    }


def _human_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _first_text_cue(text: str) -> str:
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw.strip())
        line = re.sub(r"^[#>*`\-\s]+", "", line).strip()
        if line:
            return line[:118] + ("…" if len(line) > 118 else "")
    return "No visible text content."


def _card_summary(
    meta: dict[str, Any], *, incoming_count: int, outgoing_count: int,
) -> str:
    renderer = str(meta["renderer"])
    size = _human_bytes(int(meta.get("bytes") or 0))
    relation_note = f"{incoming_count} in · {outgoing_count} out"
    if renderer == "tree":
        return f"Structural object with {outgoing_count} contained item{'s' if outgoing_count != 1 else ''}. {relation_note}."
    if renderer == "text":
        return f"UTF-8 text · {size}. {_first_text_cue(str(meta.get('rendered') or ''))}"
    if renderer == "html":
        return f"HTML document · {size}. Visual content is available in the sandboxed context section."
    if renderer == "binary":
        return f"Binary object · {size}. No inline content renderer is registered yet."
    cue = _first_text_cue(str(meta.get("rendered") or ""))
    return f"Addressed {meta.get('type', 'object')}. {cue}"


def _context_body(meta: dict[str, Any], outgoing_count: int) -> str:
    renderer = str(meta["renderer"])
    if renderer == "tree":
        return (
            '<div class="structural-context">'
            f'<strong>{outgoing_count}</strong><span>connected child object'
            f'{"s" if outgoing_count != 1 else ""}</span></div>'
        )
    if renderer == "text":
        preview = html.escape(str(meta["rendered"])[:20000])
        return f'<div class="context-body text-context"><pre><code>{preview}</code></pre></div>'
    if renderer == "html":
        srcdoc = html.escape(str(meta["rendered"]), quote=True)
        path = html.escape(str(meta["path"]), quote=True)
        return (
            '<div class="context-body html-context">'
            f'<iframe sandbox="" referrerpolicy="no-referrer" title="Rendered HTML context for {path}" srcdoc="{srcdoc}"></iframe>'
            '</div>'
        )
    if renderer == "binary":
        return '<div class="context-body fallback-context">Binary content is not rendered.</div>'
    text = html.escape(str(meta.get("rendered") or ""))
    return f'<div class="context-body fallback-context">{text or "No additional context."}</div>'


def _relation_markup(
    edges: list[dict[str, str]], bounds: dict[str, dict[str, float]],
) -> tuple[list[str], int]:
    by_source: dict[str, list[dict[str, str]]] = {}
    for edge in edges:
        by_source.setdefault(edge["from"], []).append(edge)

    markup: list[str] = []
    bundles = 0
    for source, source_edges in by_source.items():
        a = bounds[source]
        x1 = a["x"] + a["width"]
        y1 = a["y"] + CARD_RELATION_Y
        ordered = sorted(
            source_edges,
            key=lambda edge: (bounds[edge["to"]]["y"], edge["id"]),
        )
        if len(ordered) == 1:
            edge = ordered[0]
            b = bounds[edge["to"]]
            x2, y2 = b["x"], b["y"] + CARD_RELATION_Y
            markup.append(
                f'<path class="relation-edge relation-direct" '
                f'data-connection-id="{html.escape(edge["id"], quote=True)}" '
                f'data-from="{html.escape(source, quote=True)}" data-to="{html.escape(edge["to"], quote=True)}" '
                f'd="M{x1} {y1} C{x1 + 70} {y1},{x2 - 70} {y2},{x2} {y2}" />'
            )
            continue

        bundles += 1
        hub_x = x1 + 62.0
        child_points = [
            (bounds[edge["to"]]["x"], bounds[edge["to"]]["y"] + CARD_RELATION_Y)
            for edge in ordered
        ]
        min_y = min([y1, *[point[1] for point in child_points]])
        max_y = max([y1, *[point[1] for point in child_points]])
        source_q = html.escape(source, quote=True)
        markup.append(
            f'<path class="relation-bundle" data-source="{source_q}" data-count="{len(ordered)}" '
            f'd="M{x1} {y1} H{hub_x} M{hub_x} {min_y} V{max_y}" />'
        )
        markup.append(
            f'<g class="relation-bundle-label" data-source="{source_q}" transform="translate({hub_x},{y1})">'
            f'<circle r="11"></circle><text text-anchor="middle" dy="3.5">{len(ordered)}</text></g>'
        )
        for edge, (x2, y2) in zip(ordered, child_points):
            markup.append(
                f'<path class="relation-edge relation-branch" '
                f'data-connection-id="{html.escape(edge["id"], quote=True)}" '
                f'data-from="{source_q}" data-to="{html.escape(edge["to"], quote=True)}" '
                f'd="M{hub_x} {y2} H{x2}" />'
            )
    return markup, bundles


def render_board(
    document: dict[str, Any], repo: str | Path, output: str | Path,
    *, relation_kind: str = "contains",
) -> dict[str, Any]:
    repo_path = Path(repo).resolve()
    board = next((b for b in document.get("boards", []) if b.get("premise")), None)
    if board is None:
        raise BoardViewError("Board rendering requires an explicit premise")
    objects, children, _parents, _roots, edges, incoming, outgoing = _relation_graph(
        document, relation_kind
    )
    frame = next(
        (f for f in document.get("frames", []) if f.get("board_id") == board["board_id"]),
        None,
    )
    if frame is None:
        raise BoardViewError("premise-bearing Board requires a visible Frame")

    resolved: dict[str, dict[str, Any]] = {
        oid: _object_resolution(obj, repo_path) for oid, obj in objects.items()
    }
    bounds = {oid: obj["placement"]["bounds"] for oid, obj in objects.items()}
    relation_markup, bundle_count = _relation_markup(edges, bounds)

    cards: list[str] = []
    renderer_counts: dict[str, int] = {}
    for oid, obj in objects.items():
        meta, box = resolved[oid], bounds[oid]
        renderer = str(meta["renderer"])
        renderer_counts[renderer] = renderer_counts.get(renderer, 0) + 1
        path_raw = str(meta.get("path") or obj.get("label") or oid)
        path = html.escape(path_raw)
        label = html.escape(str(obj.get("label") or meta.get("path") or oid))
        provider = html.escape(str(meta.get("provider") or "provider"))
        kind = html.escape(str(meta.get("type") or renderer))
        digest_raw = str(meta.get("digest") or "")
        digest = html.escape(digest_raw[:12] or "unversioned")
        version_raw = str(meta.get("version") or "")
        version = html.escape(version_raw[:9]) if version_raw else ""
        summary = html.escape(
            _card_summary(meta, incoming_count=incoming[oid], outgoing_count=outgoing[oid])
        )
        context = _context_body(meta, outgoing[oid])
        relation_facts = (
            f'<span title="incoming {relation_kind} relations">← {incoming[oid]}</span>'
            f'<span title="outgoing {relation_kind} relations">→ {outgoing[oid]}</span>'
        )
        version_fact = f'<span class="version">@ {version}</span>' if version else ""
        cards.append(
            f'<article class="card render-{renderer}" data-object-id="{html.escape(oid, quote=True)}" '
            f'data-path="{html.escape(path_raw, quote=True)}" tabindex="0" '
            f'style="left:{box["x"]}px;top:{box["y"]}px;width:{box["width"]}px;height:{box["height"]}px">'
            '<header class="card-header">'
            '<div class="card-eyebrow">'
            f'<span class="renderer">{html.escape(renderer.upper())}</span><span>{provider}</span><span>{kind}</span>'
            '</div>'
            '<div class="card-title-row">'
            f'<strong title="{path}">{label}</strong>'
            '<button class="context-toggle" type="button" aria-expanded="false">Context <span>⌄</span></button>'
            '</div>'
            f'<div class="card-path" title="{path}">{path}</div>'
            '<div class="card-facts">'
            f'{relation_facts}<code title="digest {html.escape(digest_raw, quote=True)}">{digest}</code>{version_fact}'
            '</div>'
            '</header>'
            f'<section class="card-summary"><div class="summary-label">Summary</div><p>{summary}</p></section>'
            f'<section class="card-context" hidden><div class="context-label">Context / content</div>{context}</section>'
            '</article>'
        )

    fx, fy, fw, fh = (
        frame["bounds"]["x"], frame["bounds"]["y"],
        frame["bounds"]["width"], frame["bounds"]["height"],
    )
    world_w = max(fx + fw + 100, max(b["x"] + b["width"] for b in bounds.values()) + 100)
    world_h = max(fy + fh + 100, max(b["y"] + b["height"] for b in bounds.values()) + 100)
    premise = html.escape(str(board["premise"]))
    board_label = html.escape(str(board.get("label") or board["board_id"]))
    relation = html.escape(relation_kind)

    client = {
        "objects": {
            oid: {
                "label": objects[oid].get("label") or oid,
                "path": resolved[oid].get("path", ""),
                "bounds": bounds[oid],
                "incoming": incoming[oid],
                "outgoing": outgoing[oid],
            }
            for oid in objects
        },
        "edges": edges,
        "bundles": bundle_count,
        "frame": frame["bounds"],
    }
    client_json = json.dumps(client, sort_keys=True, separators=(",", ":")).replace("<", "\\u003c")

    page = f'''<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{board_label} — Canvas Board</title>
<style>
:root{{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif}}
*{{box-sizing:border-box}} html,body{{width:100%;height:100%;overflow:hidden}} body{{margin:0;background:#0e1116;color:#e8ecf1}}
.viewport{{position:fixed;inset:0;overflow:hidden;cursor:grab;touch-action:none;background-color:#0e1116;background-image:radial-gradient(#29303a 1px,transparent 1px);background-size:24px 24px}}
.viewport.dragging{{cursor:grabbing;user-select:none}} .world{{position:absolute;left:0;top:0;width:{world_w}px;height:{world_h}px;transform-origin:0 0;will-change:transform}}
.board-frame{{position:absolute;left:{fx}px;top:{fy}px;width:{fw}px;height:{fh}px;border:1px solid #3a424d;border-radius:22px;background:#12171ee8;box-shadow:0 26px 80px #0007}}
.board-head{{position:absolute;left:{fx + 26}px;top:{fy + 20}px;z-index:4;max-width:820px;pointer-events:none}} .board-head .kicker{{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:#7f8996}} .board-head h1{{margin:5px 0 4px;font-size:22px}} .board-head p{{margin:0;color:#a5aeba;font-size:13px}} .board-head .relation{{margin-top:7px;font:10px ui-monospace,SFMono-Regular,monospace;color:#727d8a}}
.connections{{position:absolute;inset:0;width:100%;height:100%;overflow:visible;pointer-events:none}} .relation-edge,.relation-bundle{{fill:none;vector-effect:non-scaling-stroke;transition:opacity .16s,stroke .16s,stroke-width .16s}} .relation-edge{{stroke:#566170;stroke-width:1.45;opacity:.64}} .relation-direct{{opacity:.72}} .relation-branch{{opacity:.48}} .relation-bundle{{stroke:#6d7887;stroke-width:2.2;opacity:.82}} .relation-bundle-label circle{{fill:#202832;stroke:#6d7887;stroke-width:1}} .relation-bundle-label text{{fill:#b4bdc8;font:9px ui-monospace,SFMono-Regular,monospace}} .connections.dense .relation-branch{{opacity:.16}} .connections.dense .relation-bundle{{opacity:.9;stroke-width:2.6}} .connections.focused .relation-edge:not(.active),.connections.focused .relation-bundle:not(.active),.connections.focused .relation-bundle-label:not(.active){{opacity:.055}} .relation-edge.active,.relation-bundle.active{{stroke:#d5dbe3;stroke-width:2.8;opacity:1!important}} .relation-bundle-label.active circle{{stroke:#d5dbe3;fill:#2b3440}} .relation-bundle-label.active text{{fill:#eef2f7}}
.card{{position:absolute;z-index:2;display:flex;flex-direction:column;border:1px solid #343d48;border-radius:15px;background:#181e26;overflow:hidden;outline:none;box-shadow:0 10px 30px #0005;cursor:pointer;transition:border-color .14s,box-shadow .14s,height .18s,transform .18s}} .card:hover{{border-color:#5c6877}} .card.selected{{outline:2px solid #c6ced8;outline-offset:3px}} .card.expanded{{height:500px!important;z-index:12;box-shadow:0 24px 70px #000b;border-color:#657181}}
.card-header{{flex:0 0 auto;padding:10px 12px 9px;background:linear-gradient(180deg,#202732,#1c222b);border-bottom:1px solid #313a45}} .card-eyebrow{{display:flex;align-items:center;gap:7px;color:#7f8997;font-size:8px;letter-spacing:.07em;text-transform:uppercase}} .card-eyebrow .renderer{{color:#bdc6d1;font-weight:700}} .card-title-row{{display:flex;align-items:center;gap:10px;margin-top:7px}} .card-title-row strong{{flex:1;min-width:0;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}} .context-toggle{{height:25px;border:1px solid #3d4754;border-radius:7px;background:#252e39;color:#b8c1cc;padding:0 7px;font-size:9px;cursor:pointer}} .context-toggle span{{display:inline-block;transition:transform .14s}} .card.expanded .context-toggle span{{transform:rotate(180deg)}} .card-path{{margin-top:4px;color:#8d98a6;font:9.5px ui-monospace,SFMono-Regular,Consolas,monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}} .card-facts{{display:flex;gap:6px;align-items:center;margin-top:8px;color:#8792a0;font-size:9px}} .card-facts span,.card-facts code{{padding:3px 5px;border-radius:5px;background:#141a21;border:1px solid #303944}} .card-facts code{{color:#aeb7c2;font:8.5px ui-monospace,SFMono-Regular,monospace}} .card-facts .version{{color:#788493}}
.card-summary{{flex:1;padding:11px 12px 12px;background:#151a21}} .summary-label,.context-label{{font-size:8px;letter-spacing:.1em;text-transform:uppercase;color:#6e7987}} .card-summary p{{margin:6px 0 0;color:#c1c9d3;font-size:11px;line-height:1.45;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}}
.card-context{{flex:1;min-height:0;border-top:1px solid #303944;background:#10151b;padding:10px 11px 11px}} .card-context[hidden]{{display:none}} .context-label{{margin-bottom:7px}} .context-body{{height:300px;min-height:0;border:1px solid #2d3641;border-radius:9px;overflow:auto;background:#0d1217}} .text-context pre{{margin:0;padding:10px;white-space:pre-wrap;word-break:break-word;font:9.5px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace;color:#cbd3dc}} .html-context{{overflow:hidden;background:#fff}} .html-context iframe{{width:100%;height:100%;border:0;background:#fff}} .structural-context{{height:110px;display:flex;align-items:center;justify-content:center;gap:9px;color:#9da8b5}} .structural-context strong{{font-size:28px;color:#e0e5eb}} .fallback-context{{display:grid;place-items:center;color:#929da9}}
.hud{{position:fixed;z-index:20;left:14px;top:14px;display:flex;gap:7px;padding:6px;border:1px solid #343c46;border-radius:11px;background:#141a22e8;backdrop-filter:blur(10px)}} .hud input{{width:230px;height:34px;border:1px solid #3b4551;border-radius:8px;background:#0e1218;color:inherit;padding:0 10px;outline:none}} .hud button{{height:34px;border:1px solid #3b4551;border-radius:8px;background:#202832;color:inherit;padding:0 11px;cursor:pointer}}
.status{{position:fixed;z-index:18;right:14px;bottom:12px;color:#727d8a;font-size:10px;background:#11161ccc;padding:6px 8px;border-radius:8px;pointer-events:none}} .hint{{position:fixed;z-index:18;left:16px;bottom:12px;color:#65717e;font-size:10px;pointer-events:none}}
</style>
<div class="viewport" id="viewport" aria-label="Infinite Canvas containing a premise-bearing Board"><div class="world" id="world">
<div class="board-frame" id="board-frame"></div><div class="board-head"><div class="kicker">Board</div><h1>{board_label}</h1><p>{premise}</p><div class="relation">{len(edges)} {relation} relations · {bundle_count} routed bundles</div></div>
<svg class="connections" id="connections" viewBox="0 0 {world_w} {world_h}" aria-label="Board relations">{''.join(relation_markup)}</svg>{''.join(cards)}
</div></div>
<div class="hud"><input id="search" aria-label="Find a Card" placeholder="Find Card…  /"><button id="home" type="button">Home</button></div><div class="hint">wheel zooms · drag pans · select traces relations · Context expands content</div><div class="status" id="status"></div>
<script type="application/json" id="board-data">{client_json}</script>
<script>
(()=>{{
const data=JSON.parse(document.getElementById('board-data').textContent),viewport=document.getElementById('viewport'),world=document.getElementById('world'),connections=document.getElementById('connections'),search=document.getElementById('search'),status=document.getElementById('status');let scale=.72,panX=70,panY=70,drag=null,selected=null;const minScale=.18,maxScale=3,cards=new Map([...document.querySelectorAll('.card')].map(el=>[el.dataset.objectId,el]));
function relationDensity(){{connections.classList.toggle('dense',scale<.68||data.edges.length>80)}}
function apply(){{world.style.transform=`translate(${{panX}}px,${{panY}}px) scale(${{scale}})`;relationDensity();status.textContent=`${{Math.round(scale*100)}}%${{selected?' · '+(data.objects[selected]?.path||data.objects[selected]?.label||selected):''}}`}}
function home(){{const r=data.frame,margin=54,widthFit=(viewport.clientWidth-margin*2)/r.width;scale=Math.max(.55,Math.min(.72,widthFit));panX=margin-r.x*scale;panY=margin-r.y*scale;apply()}}
function updateRelations(id){{connections.classList.toggle('focused',Boolean(id));for(const edge of document.querySelectorAll('.relation-edge'))edge.classList.toggle('active',Boolean(id)&&(edge.dataset.from===id||edge.dataset.to===id));for(const bundle of document.querySelectorAll('.relation-bundle,.relation-bundle-label'))bundle.classList.toggle('active',Boolean(id)&&bundle.dataset.source===id)}}
function select(id){{selected=id;for(const [oid,el] of cards)el.classList.toggle('selected',oid===id);updateRelations(id);apply()}}
function focusCard(id){{const o=data.objects[id];if(!o)return;selected=id;scale=Math.max(scale,.82);panX=viewport.clientWidth/2-(o.bounds.x+o.bounds.width/2)*scale;panY=viewport.clientHeight/2-(o.bounds.y+o.bounds.height/2)*scale;select(id)}}
function toggleContext(id,force){{const card=cards.get(id);if(!card)return;const section=card.querySelector('.card-context'),button=card.querySelector('.context-toggle'),next=force===undefined?!card.classList.contains('expanded'):force;card.classList.toggle('expanded',next);section.hidden=!next;button.setAttribute('aria-expanded',String(next));if(next)select(id)}}
for(const [id,el] of cards){{const toggle=el.querySelector('.context-toggle');toggle.addEventListener('click',e=>{{e.stopPropagation();toggleContext(id)}});el.addEventListener('click',e=>{{e.stopPropagation();select(id)}});el.addEventListener('dblclick',e=>{{if(e.target.closest('.context-toggle'))return;e.stopPropagation();focusCard(id)}});el.addEventListener('keydown',e=>{{if(e.key==='Enter'){{e.preventDefault();focusCard(id)}}else if(e.key===' '&&e.target===el){{e.preventDefault();toggleContext(id)}}}})}}
viewport.addEventListener('wheel',e=>{{e.preventDefault();const r=viewport.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,wx=(mx-panX)/scale,wy=(my-panY)/scale,next=Math.max(minScale,Math.min(maxScale,scale*Math.exp(-e.deltaY*.0015)));panX=mx-wx*next;panY=my-wy*next;scale=next;apply()}},{{passive:false}});
viewport.addEventListener('pointerdown',e=>{{if(e.button!==0||e.target.closest('.card,.hud'))return;drag={{x:e.clientX,y:e.clientY,px:panX,py:panY}};viewport.setPointerCapture(e.pointerId);viewport.classList.add('dragging')}});viewport.addEventListener('pointermove',e=>{{if(!drag)return;panX=drag.px+e.clientX-drag.x;panY=drag.py+e.clientY-drag.y;apply()}});function stop(e){{if(!drag)return;drag=null;viewport.classList.remove('dragging');try{{viewport.releasePointerCapture(e.pointerId)}}catch(_e){{}}}}viewport.addEventListener('pointerup',stop);viewport.addEventListener('pointercancel',stop);
search.addEventListener('keydown',e=>{{if(e.key==='Enter'){{const q=search.value.trim().toLowerCase();if(!q)return;const hit=Object.entries(data.objects).find(([_id,o])=>(o.path||o.label||'').toLowerCase().includes(q));if(hit)focusCard(hit[0])}}else if(e.key==='Escape'){{search.value='';viewport.focus()}}}});document.addEventListener('keydown',e=>{{if(e.target.matches('input,textarea'))return;if(e.key==='/'){{e.preventDefault();search.focus()}}else if(e.key==='0'||e.key==='Home'){{e.preventDefault();home()}}else if(e.key==='Escape'){{for(const el of cards.values()){{el.classList.remove('selected');if(el.classList.contains('expanded'))toggleContext(el.dataset.objectId,false)}}selected=null;updateRelations(null);apply()}}}});document.getElementById('home').addEventListener('click',home);requestAnimationFrame(home);
}})();
</script>'''
    Path(output).write_text(page, encoding="utf-8")
    return {
        "board_id": board["board_id"],
        "premise": board["premise"],
        "relation_kind": relation_kind,
        "cards": len(objects),
        "connections": len(edges),
        "bundles": bundle_count,
        "renderers": renderer_counts,
    }


def _cmd_build(args: argparse.Namespace) -> int:
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    board = materialize_board(
        source,
        board_id=args.board_id,
        label=args.label,
        premise=args.premise,
        relation_kind=args.relation,
    )
    Path(args.output).write_text(json.dumps(board, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary: dict[str, Any] = {
        "board_id": args.board_id,
        "label": args.label,
        "premise": args.premise,
        "relation_kind": args.relation,
        "objects": len(board["objects"]),
        "connections": len([c for c in board["connections"] if c.get("kind") == args.relation]),
    }
    if args.html:
        if not args.repo:
            raise BoardViewError("--repo is required when --html is requested")
        summary.update(render_board(board, args.repo, args.html, relation_kind=args.relation))
    print(json.dumps(summary, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Author and render premise-bearing Canvas Boards")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("input")
    build.add_argument("--output", required=True)
    build.add_argument("--html")
    build.add_argument("--repo")
    build.add_argument("--board-id", required=True)
    build.add_argument("--label", required=True)
    build.add_argument("--premise", required=True)
    build.add_argument("--relation", default="contains")
    build.set_defaults(func=_cmd_build)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (BoardViewError, field_view.FieldViewError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
