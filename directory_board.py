from __future__ import annotations

import argparse
import copy
import html
import json
from pathlib import Path
from typing import Any


class DirectoryBoardError(ValueError):
    pass


PREMISE = "What exists here, and how is it contained?"


def _path_from_object(obj: dict[str, Any]) -> str:
    refs = obj.get("ground_refs") or []
    if refs:
        raw = str(refs[0].get("id", ""))
        path = raw.partition("#")[2]
        if path:
            return path
    return str(obj.get("label") or obj.get("object_id") or "")


def _graph(document: dict[str, Any]):
    objects = {obj["object_id"]: obj for obj in document.get("objects", [])}
    if not objects:
        raise DirectoryBoardError("Directory Board requires at least one Object")

    children: dict[str, list[str]] = {oid: [] for oid in objects}
    parents: dict[str, str] = {}
    contains_edges: list[tuple[str, str, str]] = []
    for edge in document.get("connections", []):
        if edge.get("kind") != "contains":
            continue
        src = edge.get("from", {}).get("object_id")
        dst = edge.get("to", {}).get("object_id")
        if src not in objects or dst not in objects:
            continue
        if dst in parents and parents[dst] != src:
            raise DirectoryBoardError(f"Directory Object {dst} has multiple contains parents")
        parents[dst] = src
        children[src].append(dst)
        contains_edges.append((str(edge.get("connection_id", "")), src, dst))

    def order_key(oid: str):
        is_dir = bool(children.get(oid))
        path = _path_from_object(objects[oid])
        name = path.rsplit("/", 1)[-1] if path != "." else path
        return (0 if is_dir else 1, name.lower(), path.lower())

    for ids in children.values():
        ids.sort(key=order_key)
    roots = sorted((oid for oid in objects if oid not in parents), key=order_key)
    if not roots:
        raise DirectoryBoardError("Directory Board requires a root Object")
    return objects, children, parents, roots, contains_edges


def _directory_order(children: dict[str, list[str]], roots: list[str]) -> list[tuple[str, int]]:
    ordered: list[tuple[str, int]] = []

    def walk(oid: str, depth: int) -> None:
        ordered.append((oid, depth))
        for child in children.get(oid, []):
            walk(child, depth + 1)

    for root in roots:
        walk(root, 0)
    return ordered


def materialize_directory_board(document: dict[str, Any]) -> dict[str, Any]:
    """Create the first premise-bearing Board without duplicating source Objects."""
    result = copy.deepcopy(document)
    objects, children, _parents, roots, _edges = _graph(result)
    ordered = _directory_order(children, roots)

    result["boards"] = [{
        "board_id": "directory",
        "label": "Directory Board",
        "premise": PREMISE,
    }]

    row_height = 34.0
    for row, (oid, depth) in enumerate(ordered):
        objects[oid]["placement"] = {
            "board_id": "directory",
            "bounds": {
                "x": 64.0 + depth * 28.0,
                "y": 150.0 + row * row_height,
                "width": max(260.0, 820.0 - depth * 28.0),
                "height": 30.0,
            },
        }

    for frame in result.get("frames", []):
        frame["board_id"] = "directory"
    return result


def render_directory_board(document: dict[str, Any], output: str | Path) -> dict[str, Any]:
    objects, children, parents, roots, contains_edges = _graph(document)
    board = next((b for b in document.get("boards", []) if b.get("premise")), None)
    if board is None:
        raise DirectoryBoardError("Directory Board rendering requires an explicit Board premise")

    meta: dict[str, dict[str, Any]] = {}
    for oid, obj in objects.items():
        path = _path_from_object(obj)
        ref = (obj.get("ground_refs") or [{}])[0]
        is_dir = bool(children.get(oid))
        name = str(obj.get("label") or (path.rsplit("/", 1)[-1] if path != "." else path))
        if path != "." and "/" in name:
            name = path.rsplit("/", 1)[-1]
        meta[oid] = {
            "name": name,
            "path": path,
            "kind": "directory" if is_dir else "file",
            "digest": str(ref.get("digest") or ""),
            "version": str(ref.get("version") or ""),
            "provider": str(ref.get("provider") or ""),
            "children": len(children.get(oid, [])),
        }

    root_label = meta[roots[0]]["name"] if len(roots) == 1 else "Repository"
    version = next((m["version"] for m in meta.values() if m["version"]), "")
    client = {
        "objects": meta,
        "children": children,
        "parents": parents,
        "roots": roots,
        "connections": [{"id": edge_id, "from": src, "to": dst} for edge_id, src, dst in contains_edges],
    }
    client_json = json.dumps(client, sort_keys=True, separators=(",", ":")).replace("<", "\\u003c")
    title = html.escape(root_label)
    premise = html.escape(str(board["premise"]))
    short_version = html.escape(version[:12]) if version else "unversioned"

    page = f'''<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Directory Board</title>
<style>
:root{{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif}}
*{{box-sizing:border-box}} html,body{{width:100%;height:100%;overflow:hidden}} body{{margin:0;background:#0d0f13;color:#e6e9ee}}
.viewport{{position:fixed;inset:0;overflow:hidden;cursor:grab;touch-action:none;background-color:#0d0f13;background-image:radial-gradient(#252b34 1px,transparent 1px);background-size:24px 24px}}
.viewport.dragging{{cursor:grabbing;user-select:none}} .world{{position:absolute;left:0;top:0;transform-origin:0 0;will-change:transform}}
.board{{position:absolute;left:80px;top:72px;width:980px;min-height:420px;border:1px solid #353c46;border-radius:16px;background:#141820;box-shadow:0 22px 70px #0008;overflow:hidden}}
.board-head{{height:108px;padding:22px 26px 18px;border-bottom:1px solid #2d333c;background:#171c24}}
.board-kicker{{font-size:10px;letter-spacing:.11em;text-transform:uppercase;color:#858f9c}} .board-head h1{{margin:6px 0 4px;font-size:22px;font-weight:650}}
.board-premise{{margin:0;color:#a6afba;font-size:13px}} .board-meta{{position:absolute;right:26px;top:24px;text-align:right;color:#727d8b;font:10px ui-monospace,SFMono-Regular,Consolas,monospace}}
.columns{{display:grid;grid-template-columns:minmax(0,1fr) 110px 150px;align-items:center;height:34px;padding:0 26px;border-bottom:1px solid #292f38;color:#77818f;font-size:10px;letter-spacing:.06em;text-transform:uppercase}}
.tree{{position:relative;padding:8px 18px 18px;min-height:260px}} .connections{{position:absolute;left:18px;top:8px;overflow:visible;pointer-events:none}}
.connection{{fill:none;stroke:#4a5360;stroke-width:1.25;vector-effect:non-scaling-stroke}} .connection.active{{stroke:#c1c8d1;stroke-width:2}}
.row{{position:absolute;left:18px;right:18px;height:34px;display:grid;grid-template-columns:minmax(0,1fr) 110px 150px;align-items:center;border-radius:7px;outline:none;color:#cbd1d9}}
.row:hover{{background:#1c222b}} .row.selected{{background:#202731}}
.name-cell{{position:relative;display:flex;align-items:center;min-width:0;height:100%;padding-left:calc(var(--depth) * 28px + 8px)}}
.endpoint{{position:absolute;left:calc(var(--depth) * 28px - 2px);width:7px;height:7px;border-radius:50%;background:#77818f;box-shadow:0 0 0 2px #141820}} .row.selected .endpoint{{background:#d3d8df}}
.disclosure{{width:24px;height:26px;display:grid;place-items:center;border:0;background:transparent;color:#8993a0;padding:0;cursor:pointer;font-size:12px}} .disclosure.empty{{visibility:hidden}}
.glyph{{width:20px;color:#939daa;font-size:13px}} .name{{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px}}
.kind{{color:#858f9c;font-size:10px}} .ground{{color:#6f7987;font:9.5px ui-monospace,SFMono-Regular,Consolas,monospace;white-space:nowrap}} .row.hidden{{display:none}}
.hud{{position:fixed;z-index:20;top:14px;left:14px;display:flex;gap:7px;align-items:center;padding:6px;border:1px solid #343b46;border-radius:11px;background:#141820e8;backdrop-filter:blur(10px)}}
.hud input{{width:230px;height:34px;border:1px solid #3b4350;border-radius:8px;background:#0e1117;color:inherit;padding:0 10px;outline:none}} .hud button{{height:34px;border:1px solid #3b4350;border-radius:8px;background:#202630;color:inherit;padding:0 11px;cursor:pointer}}
.status{{position:fixed;z-index:18;right:14px;bottom:12px;color:#717b89;font-size:10px;background:#11151bcf;padding:6px 8px;border-radius:8px;pointer-events:none}} .hint{{position:fixed;z-index:18;left:16px;bottom:12px;color:#626d7a;font-size:10px;pointer-events:none}}
@media(max-width:700px){{.board{{width:760px}}.board-meta{{display:none}}.columns,.row{{grid-template-columns:minmax(0,1fr) 90px 110px}}.hud{{right:14px}}.hud input{{width:auto;flex:1}}}}
</style>
<div class="viewport" id="viewport" aria-label="Infinite Canvas containing a Directory Board"><div class="world" id="world">
<section class="board" id="board" aria-label="Directory Board: {premise}">
<header class="board-head"><div class="board-kicker">Directory Board</div><h1>{title}</h1><p class="board-premise">{premise}</p><div class="board-meta">{len(objects)} objects<br>{len(contains_edges)} contains connections<br>{short_version}</div></header>
<div class="columns"><span>Name</span><span>Kind</span><span>Ground</span></div><div class="tree" id="tree" role="tree" aria-label="Repository directory"><svg class="connections" id="connections" aria-label="Contains connections"></svg></div>
</section></div></div>
<div class="hud"><input id="search" aria-label="Find a path" placeholder="Find path…  /"><button id="home" type="button">Home</button></div><div class="hint">wheel zooms · drag pans · folders collapse</div><div class="status" id="status"></div>
<script type="application/json" id="directory-data">{client_json}</script>
<script>
(()=>{{
const graph=JSON.parse(document.getElementById('directory-data').textContent),viewport=document.getElementById('viewport'),world=document.getElementById('world'),board=document.getElementById('board'),tree=document.getElementById('tree'),svg=document.getElementById('connections'),search=document.getElementById('search'),status=document.getElementById('status'),collapsed=new Set(),rows=new Map();
let selected=null,scale=1,panX=0,panY=0,drag=null;const rowH=34,topPad=8,minScale=.28,maxScale=3;
function depthOf(id){{let d=0,p=graph.parents[id];while(p){{d++;p=graph.parents[p]}}return d}} function basename(path){{if(path==='.')return graph.objects[graph.roots[0]]?.name||'.';const p=path.split('/');return p[p.length-1]||path}}
function rowFor(id){{const m=graph.objects[id],depth=depthOf(id),hasKids=(graph.children[id]||[]).length>0,el=document.createElement('div');el.className='row';el.dataset.objectId=id;el.dataset.path=m.path;el.style.setProperty('--depth',depth);el.setAttribute('role','treeitem');el.setAttribute('aria-level',depth+1);el.tabIndex=0;const name=document.createElement('div');name.className='name-cell';const endpoint=document.createElement('span');endpoint.className='endpoint';endpoint.setAttribute('aria-hidden','true');name.appendChild(endpoint);const disclosure=document.createElement('button');disclosure.type='button';disclosure.className='disclosure'+(hasKids?'':' empty');disclosure.tabIndex=-1;disclosure.setAttribute('aria-label',hasKids?'Collapse directory':'No children');disclosure.textContent=hasKids?'▾':'·';name.appendChild(disclosure);const glyph=document.createElement('span');glyph.className='glyph';glyph.textContent=hasKids?'▱':'·';glyph.setAttribute('aria-hidden','true');name.appendChild(glyph);const label=document.createElement('span');label.className='name';label.textContent=basename(m.path);label.title=m.path;name.appendChild(label);const kind=document.createElement('span');kind.className='kind';kind.textContent=m.kind;const ground=document.createElement('span');ground.className='ground';ground.textContent=(m.digest||'').slice(0,12);el.append(name,kind,ground);disclosure.addEventListener('click',e=>{{e.stopPropagation();toggle(id)}});el.addEventListener('click',()=>select(id));el.addEventListener('dblclick',()=>{{if(hasKids)toggle(id);focusRow(id)}});el.addEventListener('keydown',e=>{{if(e.key==='Enter'){{e.preventDefault();if(hasKids)toggle(id);else focusRow(id)}}}});return el}}
for(const id of Object.keys(graph.objects)){{const el=rowFor(id);rows.set(id,el);tree.appendChild(el)}}
function walkVisible(){{const out=[];function walk(id){{out.push(id);if(collapsed.has(id))return;for(const c of graph.children[id]||[])walk(c)}}for(const r of graph.roots)walk(r);return out}} function endpointXY(id,indexById){{return{{x:depthOf(id)*28+18,y:topPad+indexById.get(id)*rowH+rowH/2}}}}
function renderConnections(visible,indexById){{svg.replaceChildren();const width=Math.max(1,board.clientWidth-36),height=Math.max(1,visible.length*rowH+topPad*2);svg.setAttribute('width',width);svg.setAttribute('height',height);svg.setAttribute('viewBox',`0 0 ${{width}} ${{height}}`);const set=new Set(visible);for(const edge of graph.connections){{if(!set.has(edge.from)||!set.has(edge.to))continue;const a=endpointXY(edge.from,indexById),b=endpointXY(edge.to,indexById),mid=a.x+14,p=document.createElementNS('http://www.w3.org/2000/svg','path');p.setAttribute('class','connection'+((selected===edge.from||selected===edge.to)?' active':''));p.dataset.from=edge.from;p.dataset.to=edge.to;p.dataset.connectionId=edge.id;p.setAttribute('d',`M ${{a.x}} ${{a.y}} H ${{mid}} V ${{b.y}} H ${{b.x}}`);svg.appendChild(p)}}}}
function layoutTree(){{const visible=walkVisible(),index=new Map(visible.map((id,i)=>[id,i]));for(const [id,row] of rows){{const i=index.get(id);row.classList.toggle('hidden',i===undefined);if(i!==undefined)row.style.top=`${{topPad+i*rowH}}px`;row.classList.toggle('selected',id===selected);const hasKids=(graph.children[id]||[]).length>0,btn=row.querySelector('.disclosure');if(hasKids){{btn.textContent=collapsed.has(id)?'▸':'▾';btn.setAttribute('aria-label',collapsed.has(id)?'Expand directory':'Collapse directory');row.setAttribute('aria-expanded',String(!collapsed.has(id)))}}}}tree.style.height=`${{visible.length*rowH+topPad*2+10}}px`;board.style.height=`${{108+34+visible.length*rowH+topPad*2+28}}px`;renderConnections(visible,index);updateStatus()}}
function select(id){{selected=id;layoutTree();rows.get(id)?.focus({{preventScroll:true}})}} function toggle(id){{if(!(graph.children[id]||[]).length)return;collapsed.has(id)?collapsed.delete(id):collapsed.add(id);layoutTree()}}
function clamp(v){{return Math.max(minScale,Math.min(maxScale,v))}} function applyView(){{world.style.transform=`translate(${{panX}}px,${{panY}}px) scale(${{scale}})`;const g=24*scale;viewport.style.backgroundSize=`${{g}}px ${{g}}px`;viewport.style.backgroundPosition=`${{panX}}px ${{panY}}px`;updateStatus()}} function zoomAt(next,cx,cy){{const r=viewport.getBoundingClientRect(),sx=cx-r.left,sy=cy-r.top,wx=(sx-panX)/scale,wy=(sy-panY)/scale;scale=clamp(next);panX=sx-wx*scale;panY=sy-wy*scale;applyView()}}
function home(){{const boardW=board.offsetWidth,boardH=board.offsetHeight;scale=clamp(Math.max(.72,Math.min(1,(viewport.clientWidth-120)/boardW)));panX=(viewport.clientWidth-boardW*scale)/2-80*scale;panY=Math.max(36,(viewport.clientHeight-Math.min(boardH*scale,viewport.clientHeight-72))/2)-72*scale;applyView()}}
function focusRow(id){{const row=rows.get(id);if(!row)return;let p=graph.parents[id];while(p){{collapsed.delete(p);p=graph.parents[p]}}layoutTree();selected=id;scale=Math.max(scale,.9);const bx=80+row.offsetLeft+depthOf(id)*28+180,by=72+108+34+row.offsetTop+rowH/2;panX=viewport.clientWidth/2-bx*scale;panY=viewport.clientHeight/2-by*scale;applyView();layoutTree()}} function updateStatus(){{status.textContent=`${{walkVisible().length}}/${{Object.keys(graph.objects).length}} shown · ${{Math.round(scale*100)}}%${{selected?' · '+graph.objects[selected].path:''}}`}}
search.addEventListener('input',()=>{{const q=search.value.trim().toLowerCase();for(const row of rows.values())row.style.opacity=!q||row.dataset.path.toLowerCase().includes(q)?'1':'.34'}});search.addEventListener('keydown',e=>{{if(e.key==='Enter'){{const q=search.value.trim().toLowerCase(),hit=Object.entries(graph.objects).find(([,m])=>m.path.toLowerCase().includes(q));if(hit)focusRow(hit[0])}}else if(e.key==='Escape'){{search.value='';search.dispatchEvent(new Event('input'));viewport.focus()}}}});document.getElementById('home').addEventListener('click',home);
viewport.addEventListener('wheel',e=>{{e.preventDefault();zoomAt(scale*Math.exp(-e.deltaY*.0015),e.clientX,e.clientY)}},{{passive:false}});viewport.addEventListener('pointerdown',e=>{{if(e.target.closest('.row,.hud,button,input'))return;drag={{x:e.clientX,y:e.clientY,panX,panY}};viewport.classList.add('dragging');viewport.setPointerCapture(e.pointerId)}});viewport.addEventListener('pointermove',e=>{{if(!drag)return;panX=drag.panX+e.clientX-drag.x;panY=drag.panY+e.clientY-drag.y;applyView()}});function endDrag(e){{if(!drag)return;drag=null;viewport.classList.remove('dragging');if(viewport.hasPointerCapture(e.pointerId))viewport.releasePointerCapture(e.pointerId)}}viewport.addEventListener('pointerup',endDrag);viewport.addEventListener('pointercancel',endDrag);
window.addEventListener('keydown',e=>{{if((e.target instanceof HTMLInputElement)||(e.target instanceof HTMLTextAreaElement))return;if(e.key==='/'){{e.preventDefault();search.focus()}}else if(e.key==='0'||e.key==='Home'){{e.preventDefault();home()}}else if(e.key==='Escape'){{selected=null;layoutTree()}}}});window.addEventListener('resize',home);layoutTree();requestAnimationFrame(home);
}})();
</script>
'''
    Path(output).write_text(page, encoding="utf-8")
    return {
        "board": "directory",
        "premise": str(board["premise"]),
        "objects": len(objects),
        "connections": len(contains_edges),
        "directories": sum(1 for m in meta.values() if m["kind"] == "directory"),
        "files": sum(1 for m in meta.values() if m["kind"] == "file"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and render the first premise-bearing Directory Board")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("canvas")
    build.add_argument("--output", required=True)
    build.add_argument("--html")
    render = sub.add_parser("render")
    render.add_argument("canvas")
    render.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    document = json.loads(Path(args.canvas).read_text(encoding="utf-8"))
    if args.command == "build":
        board = materialize_directory_board(document)
        Path(args.output).write_text(json.dumps(board, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = render_directory_board(board, args.html) if args.html else {
            "board": "directory",
            "premise": PREMISE,
            "objects": len(board.get("objects", [])),
            "connections": len([c for c in board.get("connections", []) if c.get("kind") == "contains"]),
        }
    else:
        result = render_directory_board(document, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
