from __future__ import annotations

import argparse
import copy
import html
import json
from pathlib import Path
from typing import Any

import field_view


class BoardViewError(ValueError):
    pass


def _relation_graph(document: dict[str, Any], relation_kind: str):
    objects = {obj["object_id"]: obj for obj in document.get("objects", [])}
    if not objects:
        raise BoardViewError("Board requires at least one Object")

    children: dict[str, list[str]] = {oid: [] for oid in objects}
    parents: dict[str, str] = {}
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
    return objects, children, parents, roots, edges


def _hierarchy_layout(
    objects: dict[str, dict[str, Any]],
    children: dict[str, list[str]],
    roots: list[str],
) -> dict[str, dict[str, float]]:
    card_w = 320.0
    card_h = 190.0
    x_step = 430.0
    y_gap = 56.0
    cursor = 170.0
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
            y = center - card_h / 2
        else:
            y = cursor
            center = y + card_h / 2
            cursor += card_h + y_gap
        positions[oid] = {
            "x": 170.0 + depth * x_step,
            "y": y,
            "width": card_w,
            "height": card_h,
        }
        visiting.remove(oid)
        visited.add(oid)
        return center

    for root in roots:
        place(root, 0)
        cursor += 120.0

    # A valid hierarchical Board should place every object represented by the relation graph.
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
    objects, children, _parents, roots, _edges = _relation_graph(result, relation_kind)
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
            "x": min_x - 90.0,
            "y": min_y - 120.0,
            "width": max_x - min_x + 180.0,
            "height": max_y - min_y + 210.0,
        },
        "members": list(objects),
    }]
    return result


def _object_resolution(obj: dict[str, Any], repo: Path) -> dict[str, Any]:
    refs = [ref for ref in obj.get("ground_refs", []) if ref.get("provider") == "git-object"]
    if not refs:
        return {
            "renderer": "label",
            "path": str(obj.get("label") or obj["object_id"]),
            "digest": "",
            "version": "",
            "rendered": str(obj.get("content") or ""),
            "bytes": 0,
            "type": obj.get("kind", "object"),
        }
    resolved = field_view._resolve_git(refs[0], repo)
    renderer, rendered = field_view._render_kind(
        resolved["path"], resolved["type"], resolved["bytes"]
    )
    return {
        **resolved,
        "renderer": renderer,
        "rendered": rendered,
        "bytes": len(resolved["bytes"]),
    }


def _card_body(meta: dict[str, Any], child_count: int) -> str:
    renderer = meta["renderer"]
    if renderer == "tree":
        return (
            '<div class="tree-card-body">'
            f'<strong>{child_count}</strong><span>connected children</span>'
            '</div>'
        )
    if renderer == "text":
        preview = html.escape(str(meta["rendered"])[:5000])
        return f'<div class="card-body text-card"><pre><code>{preview}</code></pre></div>'
    if renderer == "html":
        srcdoc = html.escape(str(meta["rendered"]), quote=True)
        path = html.escape(str(meta["path"]), quote=True)
        return (
            '<div class="card-body html-card">'
            f'<iframe sandbox="" referrerpolicy="no-referrer" title="Rendered HTML preview for {path}" srcdoc="{srcdoc}"></iframe>'
            '</div>'
        )
    if renderer == "binary":
        return '<div class="card-body fallback-card">Binary object</div>'
    text = html.escape(str(meta.get("rendered") or ""))
    return f'<div class="card-body fallback-card">{text or "Addressed object"}</div>'


def render_board(
    document: dict[str, Any], repo: str | Path, output: str | Path,
    *, relation_kind: str = "contains",
) -> dict[str, Any]:
    repo_path = Path(repo).resolve()
    board = next((b for b in document.get("boards", []) if b.get("premise")), None)
    if board is None:
        raise BoardViewError("Board rendering requires an explicit premise")
    objects, children, _parents, _roots, edges = _relation_graph(document, relation_kind)
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

    connection_markup: list[str] = []
    for edge in edges:
        a, b = bounds[edge["from"]], bounds[edge["to"]]
        x1, y1 = a["x"] + a["width"], a["y"] + a["height"] / 2
        x2, y2 = b["x"], b["y"] + b["height"] / 2
        connection_markup.append(
            f'<path class="connection" data-connection-id="{html.escape(edge["id"], quote=True)}" '
            f'data-from="{html.escape(edge["from"], quote=True)}" data-to="{html.escape(edge["to"], quote=True)}" '
            f'd="M{x1} {y1} C{x1 + 72} {y1},{x2 - 72} {y2},{x2} {y2}" />'
        )

    cards: list[str] = []
    renderer_counts: dict[str, int] = {}
    for oid, obj in objects.items():
        meta, box = resolved[oid], bounds[oid]
        renderer = str(meta["renderer"])
        renderer_counts[renderer] = renderer_counts.get(renderer, 0) + 1
        path = html.escape(str(meta.get("path") or obj.get("label") or oid))
        label = html.escape(str(obj.get("label") or meta.get("path") or oid))
        digest = html.escape(str(meta.get("digest") or "")[:10])
        body = _card_body(meta, len(children.get(oid, [])))
        cards.append(
            f'<article class="card render-{renderer}" data-object-id="{html.escape(oid, quote=True)}" '
            f'data-path="{html.escape(str(meta.get("path") or ""), quote=True)}" tabindex="0" '
            f'style="left:{box["x"]}px;top:{box["y"]}px;width:{box["width"]}px;height:{box["height"]}px">'
            '<header class="card-head">'
            f'<span class="renderer">{html.escape(renderer.upper())}</span>'
            f'<strong title="{path}">{label}</strong>'
            f'<span class="digest">{digest}</span>'
            '</header>'
            f'{body}</article>'
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
            }
            for oid in objects
        },
        "edges": edges,
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
.board-frame{{position:absolute;left:{fx}px;top:{fy}px;width:{fw}px;height:{fh}px;border:1px solid #3a424d;border-radius:20px;background:#12171ee8;box-shadow:0 26px 80px #0007}}
.board-head{{position:absolute;left:{fx + 24}px;top:{fy + 18}px;z-index:4;max-width:760px;pointer-events:none}} .board-head .kicker{{font-size:10px;text-transform:uppercase;letter-spacing:.11em;color:#7f8996}} .board-head h1{{margin:5px 0 4px;font-size:21px}} .board-head p{{margin:0;color:#a5aeba;font-size:13px}} .board-head .relation{{margin-top:7px;font:10px ui-monospace,SFMono-Regular,monospace;color:#727d8a}}
.connections{{position:absolute;inset:0;width:100%;height:100%;overflow:visible;pointer-events:none}} .connection{{fill:none;stroke:#4a5461;stroke-width:1.5;vector-effect:non-scaling-stroke}} .connection.active{{stroke:#c7ced7;stroke-width:2.4}}
.card{{position:absolute;z-index:2;display:flex;flex-direction:column;border:1px solid #343d48;border-radius:13px;background:#181e26;overflow:hidden;outline:none;box-shadow:0 9px 26px #0005;cursor:pointer}} .card:hover{{border-color:#5b6674}} .card.selected{{outline:2px solid #c1c9d3;outline-offset:3px}}
.card-head{{height:48px;flex:0 0 48px;padding:8px 10px;display:grid;grid-template-columns:auto 1fr auto;gap:8px;align-items:center;background:#1d232c;border-bottom:1px solid #313945}} .card-head .renderer{{font-size:8.5px;letter-spacing:.08em;color:#84909e}} .card-head strong{{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11.5px}} .card-head .digest{{font:8.5px ui-monospace,SFMono-Regular,monospace;color:#727e8c}}
.card-body{{flex:1;min-height:0;background:#12171e}} .text-card{{overflow:hidden}} pre{{height:100%;margin:0;padding:10px;overflow:hidden;white-space:pre-wrap;word-break:break-word;font:9.7px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace;color:#cbd3dc}} .html-card iframe{{width:100%;height:100%;border:0;background:#fff;pointer-events:none}} .tree-card-body{{flex:1;display:flex;align-items:center;justify-content:center;gap:8px;color:#9ba6b3}} .tree-card-body strong{{font-size:26px;color:#e0e5eb}} .fallback-card{{display:grid;place-items:center;color:#8e99a7}}
.hud{{position:fixed;z-index:20;left:14px;top:14px;display:flex;gap:7px;padding:6px;border:1px solid #343c46;border-radius:11px;background:#141a22e8;backdrop-filter:blur(10px)}} .hud input{{width:230px;height:34px;border:1px solid #3b4551;border-radius:8px;background:#0e1218;color:inherit;padding:0 10px;outline:none}} .hud button{{height:34px;border:1px solid #3b4551;border-radius:8px;background:#202832;color:inherit;padding:0 11px;cursor:pointer}}
.status{{position:fixed;z-index:18;right:14px;bottom:12px;color:#727d8a;font-size:10px;background:#11161ccc;padding:6px 8px;border-radius:8px;pointer-events:none}} .hint{{position:fixed;z-index:18;left:16px;bottom:12px;color:#65717e;font-size:10px;pointer-events:none}}
</style>
<div class="viewport" id="viewport" aria-label="Infinite Canvas containing a premise-bearing Board"><div class="world" id="world">
<div class="board-frame" id="board-frame"></div><div class="board-head"><div class="kicker">Board</div><h1>{board_label}</h1><p>{premise}</p><div class="relation">relations: {relation}</div></div>
<svg class="connections" viewBox="0 0 {world_w} {world_h}" aria-label="Board relations">{''.join(connection_markup)}</svg>{''.join(cards)}
</div></div>
<div class="hud"><input id="search" aria-label="Find a Card" placeholder="Find Card…  /"><button id="home" type="button">Home</button></div><div class="hint">wheel zooms · drag pans · Cards reveal addressed things</div><div class="status" id="status"></div>
<script type="application/json" id="board-data">{client_json}</script>
<script>
(()=>{{
const data=JSON.parse(document.getElementById('board-data').textContent),viewport=document.getElementById('viewport'),world=document.getElementById('world'),search=document.getElementById('search'),status=document.getElementById('status');let scale=.72,panX=70,panY=70,drag=null,selected=null;const minScale=.18,maxScale=3,cards=new Map([...document.querySelectorAll('.card')].map(el=>[el.dataset.objectId,el]));
function apply(){{world.style.transform=`translate(${{panX}}px,${{panY}}px) scale(${{scale}})`;status.textContent=`${{Math.round(scale*100)}}%${{selected?' · '+(data.objects[selected]?.path||data.objects[selected]?.label||selected):''}}`}}
function home(){{const r=data.frame,margin=54,usableW=viewport.clientWidth-margin*2,usableH=viewport.clientHeight-margin*2,fit=Math.min(usableW/r.width,usableH/r.height,.82);scale=Math.max(.34,fit);panX=(viewport.clientWidth-r.width*scale)/2-r.x*scale;panY=(viewport.clientHeight-r.height*scale)/2-r.y*scale;apply()}}
function select(id){{selected=id;for(const [oid,el] of cards)el.classList.toggle('selected',oid===id);for(const edge of document.querySelectorAll('.connection'))edge.classList.toggle('active',edge.dataset.from===id||edge.dataset.to===id);apply()}}
function focusCard(id){{const o=data.objects[id];if(!o)return;selected=id;scale=Math.max(scale,.82);panX=viewport.clientWidth/2-(o.bounds.x+o.bounds.width/2)*scale;panY=viewport.clientHeight/2-(o.bounds.y+o.bounds.height/2)*scale;select(id)}}
for(const [id,el] of cards){{el.addEventListener('click',e=>{{e.stopPropagation();select(id)}});el.addEventListener('dblclick',e=>{{e.stopPropagation();focusCard(id)}});el.addEventListener('keydown',e=>{{if(e.key==='Enter'){{e.preventDefault();focusCard(id)}}}})}}
viewport.addEventListener('wheel',e=>{{e.preventDefault();const r=viewport.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,wx=(mx-panX)/scale,wy=(my-panY)/scale,next=Math.max(minScale,Math.min(maxScale,scale*Math.exp(-e.deltaY*.0015)));panX=mx-wx*next;panY=my-wy*next;scale=next;apply()}},{{passive:false}});
viewport.addEventListener('pointerdown',e=>{{if(e.button!==0||e.target.closest('.card,.hud'))return;drag={{x:e.clientX,y:e.clientY,px:panX,py:panY}};viewport.setPointerCapture(e.pointerId);viewport.classList.add('dragging')}});viewport.addEventListener('pointermove',e=>{{if(!drag)return;panX=drag.px+e.clientX-drag.x;panY=drag.py+e.clientY-drag.y;apply()}});function stop(e){{if(!drag)return;drag=null;viewport.classList.remove('dragging');try{{viewport.releasePointerCapture(e.pointerId)}}catch(_e){{}}}}viewport.addEventListener('pointerup',stop);viewport.addEventListener('pointercancel',stop);
search.addEventListener('keydown',e=>{{if(e.key==='Enter'){{const q=search.value.trim().toLowerCase();if(!q)return;const hit=Object.entries(data.objects).find(([_id,o])=>(o.path||o.label||'').toLowerCase().includes(q));if(hit)focusCard(hit[0])}}else if(e.key==='Escape'){{search.value='';viewport.focus()}}}});document.addEventListener('keydown',e=>{{if(e.target.matches('input,textarea'))return;if(e.key==='/'){{e.preventDefault();search.focus()}}else if(e.key==='0'||e.key==='Home'){{e.preventDefault();home()}}else if(e.key==='Escape'){{selected=null;for(const el of cards.values())el.classList.remove('selected');for(const edge of document.querySelectorAll('.connection'))edge.classList.remove('active');apply()}}}});document.getElementById('home').addEventListener('click',home);requestAnimationFrame(home);
}})();
</script>'''
    Path(output).write_text(page, encoding="utf-8")
    return {
        "board_id": board["board_id"],
        "premise": board["premise"],
        "relation_kind": relation_kind,
        "cards": len(objects),
        "connections": len(edges),
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
