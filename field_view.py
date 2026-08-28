from __future__ import annotations

import argparse
import html
import json
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any


class FieldViewError(ValueError):
    pass


def _git(repo: Path, *args: str, text: bool = True):
    proc = subprocess.run(
        ["git", *args], cwd=repo, check=False,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=text,
    )
    if proc.returncode != 0:
        err = proc.stderr.strip() if text else proc.stderr.decode("utf-8", "replace").strip()
        raise FieldViewError(f"git {' '.join(args)}: {err or 'command failed'}")
    return proc.stdout.strip() if text else proc.stdout


def _path_from_ref(ref: dict[str, Any]) -> str:
    raw = str(ref.get("id", ""))
    return raw.partition("#")[2] or raw


def _resolve_git(ref: dict[str, Any], repo: Path) -> dict[str, Any]:
    if ref.get("provider") != "git-object":
        raise FieldViewError("field_view currently renders git-object references")
    version = str(ref.get("version") or "")
    digest = str(ref.get("digest") or "")
    if not version or not digest:
        raise FieldViewError("git-object rendering requires exact version and digest")
    actual_commit = _git(repo, "rev-parse", f"{version}^{{commit}}")
    if actual_commit != version:
        raise FieldViewError("render version is not the exact pinned commit")
    path = _path_from_ref(ref)
    actual_digest = _git(repo, "rev-parse", f"{version}^{{tree}}" if path == "." else f"{version}:{path}")
    if actual_digest != digest:
        raise FieldViewError(f"render digest mismatch for {path}")
    object_type = _git(repo, "cat-file", "-t", digest)
    body = b"" if object_type == "tree" else _git(repo, "cat-file", "blob", digest, text=False)
    return {"path": path, "version": version, "digest": digest, "type": object_type, "bytes": body}


def _render_kind(path: str, object_type: str, payload: bytes) -> tuple[str, str]:
    if object_type == "tree":
        return "tree", ""
    suffix = PurePosixPath(path).suffix.lower()
    if suffix in {".html", ".htm"}:
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            return "binary", ""
        csp = (
            "default-src 'none'; img-src data:; style-src 'unsafe-inline'; font-src data:; "
            "media-src data:; connect-src 'none'; frame-src 'none'; object-src 'none'; "
            "base-uri 'none'; form-action 'none'"
        )
        srcdoc = f'<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="{html.escape(csp, quote=True)}">{text}'
        return "html", srcdoc
    if b"\x00" not in payload:
        try:
            return "text", payload.decode("utf-8")
        except UnicodeDecodeError:
            pass
    return "binary", ""


def _graph(document: dict[str, Any]):
    objects = {obj["object_id"]: obj for obj in document["objects"]}
    children = {oid: [] for oid in objects}
    parents: dict[str, str] = {}
    for edge in document["connections"]:
        if edge.get("kind") != "contains":
            continue
        src = edge["from"]["object_id"]
        dst = edge["to"]["object_id"]
        if src in objects and dst in objects:
            children[src].append(dst)
            parents[dst] = src
    for ids in children.values():
        ids.sort(key=lambda oid: str(objects[oid].get("label", oid)).lower())
    roots = [oid for oid in objects if oid not in parents]
    roots.sort()
    return objects, children, parents, roots


def _layout(objects, children, roots, meta):
    positions: dict[str, dict[str, float]] = {}
    cursor = 80.0
    x_step = 500.0
    gap = 72.0

    def size(oid: str) -> tuple[float, float]:
        return (280.0, 116.0) if meta[oid]["renderer"] == "tree" else (420.0, 300.0)

    def place(oid: str, depth: int) -> float:
        nonlocal cursor
        kids = children.get(oid, [])
        width, height = size(oid)
        if kids:
            centers = [place(kid, depth + 1) for kid in kids]
            center = (centers[0] + centers[-1]) / 2
            y = center - height / 2
        else:
            y = cursor
            center = y + height / 2
            cursor += height + gap
        positions[oid] = {"x": 80 + depth * x_step, "y": y, "width": width, "height": height}
        return center

    for root in roots:
        place(root, 0)
        cursor += 180
    return positions


def render_field(document: dict[str, Any], repo: str | Path, output: str | Path) -> dict[str, Any]:
    repo_path = Path(repo).resolve()
    objects, children, parents, roots = _graph(document)
    if not roots:
        raise FieldViewError("Canvas field has no root object")

    meta: dict[str, dict[str, Any]] = {}
    for oid, obj in objects.items():
        refs = [r for r in obj.get("ground_refs", []) if r.get("provider") == "git-object"]
        if not refs:
            raise FieldViewError(f"{oid} has no renderable git-object GroundRef")
        resolved = _resolve_git(refs[0], repo_path)
        renderer, rendered = _render_kind(resolved["path"], resolved["type"], resolved["bytes"])
        meta[oid] = {
            "label": obj.get("label") or resolved["path"],
            "path": resolved["path"],
            "type": resolved["type"],
            "renderer": renderer,
            "digest": resolved["digest"],
            "version": resolved["version"],
            "bytes": len(resolved["bytes"]),
            "rendered": rendered,
        }

    positions = _layout(objects, children, roots, meta)
    max_x = max(v["x"] + v["width"] for v in positions.values()) + 100
    max_y = max(v["y"] + v["height"] for v in positions.values()) + 100

    edges = []
    for parent, kids in children.items():
        p = positions[parent]
        for child in kids:
            c = positions[child]
            x1, y1 = p["x"] + p["width"], p["y"] + p["height"] / 2
            x2, y2 = c["x"], c["y"] + c["height"] / 2
            edges.append(f'<path class="edge" d="M{x1} {y1} C{x1+80} {y1},{x2-80} {y2},{x2} {y2}" />')

    cards = []
    for oid, m in meta.items():
        b = positions[oid]
        path = html.escape(m["path"])
        label = html.escape(str(m["label"]))
        if m["renderer"] == "tree":
            body = f'<div class="tree-body"><span>{len(children.get(oid, []))}</span><small>contained objects</small></div>'
        elif m["renderer"] == "text":
            preview = html.escape(m["rendered"][:20000])
            body = f'<div class="render-body text-render"><pre><code>{preview}</code></pre></div>'
        elif m["renderer"] == "html":
            srcdoc = html.escape(m["rendered"], quote=True)
            body = f'<div class="render-body html-render"><iframe sandbox="" referrerpolicy="no-referrer" title="Rendered HTML preview for {path}" srcdoc="{srcdoc}"></iframe></div>'
        else:
            body = '<div class="binary-body">Binary object<br><small>No visual renderer yet</small></div>'
        cards.append(
            f'<article class="card render-{m["renderer"]}" style="left:{b["x"]}px;top:{b["y"]}px;width:{b["width"]}px;height:{b["height"]}px" '
            f'data-object-id="{html.escape(oid, quote=True)}" data-path="{html.escape(m["path"], quote=True)}" tabindex="0" role="button">'
            f'<div class="card-chrome"><span class="kind">{m["renderer"].upper()}</span><strong title="{path}">{label}</strong><span class="meta">{html.escape(m["digest"][:10])}</span></div>{body}</article>'
        )

    client = {
        "objects": {oid: {k: v for k, v in m.items() if k != "rendered"} | {"bounds": positions[oid]} for oid, m in meta.items()},
        "children": children,
        "parents": parents,
        "roots": roots,
    }
    client_json = json.dumps(client, sort_keys=True, separators=(",", ":")).replace("<", "\\u003c")
    label = html.escape(document.get("canvas_id", "Canvas"))

    page = f'''<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{label} — Canvas field</title>
<style>
:root{{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif}}
*{{box-sizing:border-box}} html,body{{width:100%;height:100%;overflow:hidden}} body{{margin:0;background:#0f1115;color:#e8ecf2}}
.viewport{{position:fixed;inset:0;overflow:hidden;cursor:grab;touch-action:none;background-color:#0f1115;background-image:radial-gradient(#2a303a 1px,transparent 1px);background-size:24px 24px}}
.viewport.dragging{{cursor:grabbing;user-select:none}} .world{{position:absolute;left:0;top:0;width:{max_x}px;height:{max_y}px;transform-origin:0 0;will-change:transform}}
svg{{position:absolute;inset:0;width:100%;height:100%;overflow:visible;pointer-events:none}} .edge{{fill:none;stroke:#424a57;stroke-width:1.5}}
.card{{position:absolute;display:flex;flex-direction:column;border:1px solid #343b46;border-radius:12px;background:#171b22;overflow:hidden;box-shadow:0 8px 28px #0005;cursor:pointer;outline:none}}
.card:hover{{border-color:#586272}} .card.selected{{outline:2px solid #b8c2d0;outline-offset:3px}}
.card-chrome{{height:54px;flex:0 0 54px;padding:9px 11px;border-bottom:1px solid #303640;background:#1a1f27;display:grid;grid-template-columns:auto 1fr auto;gap:8px;align-items:center}}
.card-chrome .kind{{font-size:9px;letter-spacing:.08em;color:#8e98a8}} .card-chrome strong{{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}} .card-chrome .meta{{font:9px ui-monospace,SFMono-Regular,monospace;color:#7d8796}}
.render-body{{flex:1;min-height:0;background:#11151b}} .text-render{{overflow:hidden}} pre{{margin:0;padding:12px;height:100%;overflow:hidden;white-space:pre-wrap;word-break:break-word;font:10.5px/1.42 ui-monospace,SFMono-Regular,Consolas,monospace;color:#cfd6df}}
.html-render iframe{{width:100%;height:100%;border:0;display:block;pointer-events:none;background:#fff}}
.tree-body{{flex:1;display:flex;align-items:center;justify-content:center;gap:8px;color:#aab3c0}} .tree-body span{{font-size:28px;font-weight:650;color:#e2e7ed}} .tree-body small{{max-width:70px;line-height:1.2}}
.binary-body{{flex:1;display:grid;place-content:center;text-align:center;color:#9aa4b2}}
.hud{{position:fixed;z-index:20;top:14px;left:14px;display:flex;align-items:center;gap:8px;padding:6px;border:1px solid #343b46;border-radius:12px;background:#141820e8;backdrop-filter:blur(10px);box-shadow:0 8px 24px #0005}}
.brand{{padding:0 8px;font-size:12px;font-weight:650;max-width:280px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}} .hud input{{width:240px;height:34px;border:1px solid #3b4350;border-radius:8px;background:#0e1117;color:inherit;padding:0 10px;outline:none}}
.hud input:focus{{border-color:#778397}} .hud button,.peek button{{height:34px;border:1px solid #3b4350;border-radius:8px;background:#202630;color:inherit;padding:0 10px;cursor:pointer}}
.status{{position:fixed;z-index:18;right:14px;bottom:12px;font-size:11px;color:#7f8997;background:#11151bcf;padding:6px 8px;border-radius:8px;pointer-events:none}}
.peek{{position:fixed;z-index:25;top:70px;right:14px;width:min(320px,calc(100vw - 28px));padding:14px;border:1px solid #3a424e;border-radius:12px;background:#151a22f2;backdrop-filter:blur(12px);box-shadow:0 14px 36px #0008}}
.peek[hidden]{{display:none}} .peek-head{{display:flex;align-items:start;gap:10px}} .peek h2{{font-size:14px;margin:0;flex:1;word-break:break-word}} .peek .close{{width:30px;padding:0;font-size:18px}}
.peek dl{{margin:12px 0 0}} .peek dt{{margin-top:9px;color:#7e8999;font-size:9px;text-transform:uppercase;letter-spacing:.08em}} .peek dd{{margin:3px 0 0;font-size:11px;word-break:break-all}} .peek .actions{{display:flex;gap:8px;margin-top:12px}}
.hint{{position:fixed;z-index:18;left:16px;bottom:12px;color:#697483;font-size:10px;pointer-events:none}}
@media(max-width:700px){{.brand{{display:none}}.hud{{right:14px}}.hud input{{width:auto;flex:1}}}}
</style>
<div class="viewport" id="viewport" aria-label="Infinite Canvas field"><div class="world" id="world"><svg viewBox="0 0 {max_x} {max_y}">{''.join(edges)}</svg>{''.join(cards)}</div></div>
<div class="hud"><span class="brand">{label}</span><input id="search" aria-label="Find an object" placeholder="Find…  /"><button id="home" type="button">Home</button></div>
<div class="status" id="status"></div><div class="hint">wheel zooms · drag pans · double-click focuses</div>
<aside class="peek" id="peek" hidden><div class="peek-head"><h2 id="peek-title"></h2><button class="close" id="peek-close" aria-label="Close">×</button></div><dl><dt>Path</dt><dd id="peek-path"></dd><dt>Kind</dt><dd id="peek-kind"></dd><dt>Ground</dt><dd id="peek-ground"></dd></dl><div class="actions"><button id="peek-focus">Focus</button></div></aside>
<script type="application/json" id="field-data">{client_json}</script>
<script>
(()=>{{
const graph=JSON.parse(document.getElementById('field-data').textContent),viewport=document.getElementById('viewport'),world=document.getElementById('world'),search=document.getElementById('search'),status=document.getElementById('status'),peek=document.getElementById('peek');
const cards=[...document.querySelectorAll('.card')],byId=new Map(cards.map(c=>[c.dataset.objectId,c]));
let scale=.78,panX=0,panY=0,selected=null; const minScale=.08,maxScale=4,minReadableScale=.55;
function apply(){{world.style.transform=`translate(${{panX}}px,${{panY}}px) scale(${{scale}})`;const g=24*scale;viewport.style.backgroundSize=`${{g}}px ${{g}}px`;viewport.style.backgroundPosition=`${{panX}}px ${{panY}}px`;status.textContent=`${{cards.length}} objects · ${{Math.round(scale*100)}}%`;}}
function clamp(v){{return Math.max(minScale,Math.min(maxScale,v));}}
function zoomAt(next,cx,cy){{const rect=viewport.getBoundingClientRect(),sx=cx-rect.left,sy=cy-rect.top,wx=(sx-panX)/scale,wy=(sy-panY)/scale;scale=clamp(next);panX=sx-wx*scale;panY=sy-wy*scale;apply();}}
function center(id,targetScale){{const c=byId.get(id);if(!c)return;if(targetScale)scale=clamp(targetScale);const b=graph.objects[id].bounds;panX=viewport.clientWidth/2-(b.x+b.width/2)*scale;panY=viewport.clientHeight/2-(b.y+b.height/2)*scale;apply();}}
function home(){{selected=null;peek.hidden=true;const root=graph.roots[0];scale=Math.max(minReadableScale,.72);center(root,scale);}}
function select(id){{selected=id;cards.forEach(c=>c.classList.toggle('selected',c.dataset.objectId===id));const m=graph.objects[id];document.getElementById('peek-title').textContent=m.label;document.getElementById('peek-path').textContent=m.path;document.getElementById('peek-kind').textContent=`${{m.type}} · ${{m.renderer}} · ${{m.bytes.toLocaleString()}} bytes`;document.getElementById('peek-ground').textContent=`${{m.digest}} @ ${{m.version.slice(0,12)}}`;peek.hidden=false;}}
function focusSelected(){{if(selected)center(selected,Math.max(scale,.8));}}
cards.forEach(c=>{{c.addEventListener('click',e=>{{e.stopPropagation();select(c.dataset.objectId)}});c.addEventListener('dblclick',e=>{{e.stopPropagation();select(c.dataset.objectId);focusSelected()}});c.addEventListener('keydown',e=>{{if(e.key==='Enter'){{select(c.dataset.objectId);focusSelected()}}}})}});
viewport.addEventListener('wheel',e=>{{e.preventDefault();zoomAt(scale*Math.exp(-e.deltaY*.0015),e.clientX,e.clientY)}},{{passive:false}});
let drag=null;viewport.addEventListener('pointerdown',e=>{{if(e.target.closest('.card,.hud,.peek,input,button,iframe'))return;drag={{x:e.clientX,y:e.clientY,panX,panY}};viewport.classList.add('dragging');viewport.setPointerCapture(e.pointerId)}});viewport.addEventListener('pointermove',e=>{{if(!drag)return;panX=drag.panX+e.clientX-drag.x;panY=drag.panY+e.clientY-drag.y;apply()}});function end(e){{if(!drag)return;drag=null;viewport.classList.remove('dragging');if(viewport.hasPointerCapture(e.pointerId))viewport.releasePointerCapture(e.pointerId)}}viewport.addEventListener('pointerup',end);viewport.addEventListener('pointercancel',end);
search.addEventListener('keydown',e=>{{if(e.key==='Enter'){{const q=search.value.trim().toLowerCase();if(!q)return;const hit=Object.entries(graph.objects).find(([,m])=>m.path.toLowerCase().includes(q)||m.label.toLowerCase().includes(q));if(hit){{select(hit[0]);center(hit[0],Math.max(scale,.8));}}}}}});
document.getElementById('home').addEventListener('click',home);document.getElementById('peek-close').addEventListener('click',()=>{{selected=null;peek.hidden=true;cards.forEach(c=>c.classList.remove('selected'))}});document.getElementById('peek-focus').addEventListener('click',focusSelected);
window.addEventListener('keydown',e=>{{if(e.key==='/'&&document.activeElement!==search){{e.preventDefault();search.focus();search.select()}}else if(e.key==='Escape'){{if(document.activeElement===search){{search.value='';search.blur()}}selected=null;peek.hidden=true;cards.forEach(c=>c.classList.remove('selected'))}}else if(e.key==='0'&&document.activeElement!==search)home();}});
requestAnimationFrame(home);
}})();
</script>'''
    Path(output).write_text(page, encoding="utf-8")
    return {
        "objects": len(objects),
        "roots": len(roots),
        "renderers": {kind: sum(1 for m in meta.values() if m["renderer"] == kind) for kind in {m["renderer"] for m in meta.values()}},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a Canvas field with the minimal spatial design system")
    parser.add_argument("canvas")
    parser.add_argument("repo")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    with Path(args.canvas).open("r", encoding="utf-8") as fh:
        document = json.load(fh)
    print(json.dumps(render_field(document, args.repo, args.output), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FieldViewError as exc:
        print(f"Canvas field error: {exc}")
        raise SystemExit(2)
