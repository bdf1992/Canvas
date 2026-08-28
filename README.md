# Canvas

Canvas is a portable spatial composition capability for arranging addressable things, relating them visibly, and progressively wiring a subset into explicit executable circuits.

Canvas is designed to stand on its own. Integrations such as Soveraeign may provide stronger grounding, execution, custody, provenance, authority, and evidence, but they are providers of those semantics rather than prerequisites for Canvas itself.

## Canvas, Board, and Card

These are different layers.

- **Canvas** is the spatial field: the open space in which addressed things can appear, relate, and be inspected.
- **Board** is a premise-bearing authored view over that field. A roadmap board, release-readiness board, architecture board, or discussion board exists because someone chose a question/premise and arranged things to answer it.
- **Card** is the bounded visual rendering of one addressed thing on the Canvas. A Card is presentation, not a new semantic object family.

The raw repository projection is therefore a **repository Canvas field**, not a Board. Its Git trees/blobs may later be composed into many different Boards with different premises.

The 0.1 schema still uses the historical `boards` placement field. That storage name is retained for compatibility while the premise-bearing Board distinction is made explicit in the contract; it does not make every raw placement surface a semantic Board.

## General extension model

Canvas generalizes by projecting already-addressed things into a small shared grammar, not by inventing a new card type for every source system.

```text
Provider  -> resolves addressed things and bytes
Projector -> maps source objects/relations into Canvas
Renderer  -> turns resolved things into visible Cards
```

A Projector is not a new durable Canvas object. A text renderer, HTML renderer, image renderer, etc. are likewise presentation strategies, not `TextCard`, `HtmlCard`, or other semantic object classes.

## 0.1 — Grounded Field

The standalone implementation can:

- create and reopen a Canvas;
- place addressable objects;
- move and resize objects;
- group objects with semantically neutral frames;
- connect objects visibly;
- attach provider-neutral `GroundRef`s;
- persist and reload the composition;
- explain stored grounding paths without hidden inference;
- resolve exact provider bytes for rendering;
- render UTF-8 text/code as readable card content;
- render HTML visually inside a sandboxed, network-disabled card surface.

The durable 0.1 vocabulary remains `Canvas`, `Board` (historical placement surface), `Object`, `Frame`, `Connection`, and `GroundRef`. Card rendering does not widen it.

## Task 1 — Repository as Canvas field

`repo_canvas.py` projects an exact local Git revision into the Canvas field without widening the 0.1 semantic object grammar.

```bash
python repo_canvas.py project /path/to/repo \
  --source-id owner/repo \
  --output repo.canvas.json \
  --html repo.canvas.html

python repo_canvas.py verify repo.canvas.json /path/to/repo \
  --source-id owner/repo
```

Git trees/blobs remain Git trees/blobs. Canvas projects each as an ordinary grounded `reference` Object and only real tree membership as `contains` Connections. The renderer then resolves exact pinned blob bytes and chooses a visual strategy.

The primary CI witness is **Canvas rendering Canvas itself**. The artifact is `canvas-self-field` and contains the exact Canvas JSON plus `canvas.html`.

## Card rendering

A Card should not be an opaque address label. It should visibly represent the thing it renders while preserving exact grounding.

```text
GroundRef
   -> provider resolves exact bytes
   -> renderer chooses a visual body
   -> bounded Card appears on Canvas
```

Current baseline renderers:

- UTF-8 text/code -> escaped readable text preview;
- HTML/HTM -> sandboxed visual document preview with scripts, forms, frames, objects, and network access disabled;
- unknown binary -> explicit binary fallback.

Rendered bytes are presentation. They do not become new durable Canvas state and do not create authority.

## Architectural boundary

Canvas is not an authority system. Visual state does not create approval, completion, custody, standing, ratification, or authorization. Grouping is neutral. A visible connection is a relation, not hidden execution. Executable semantics are introduced explicitly by later Circuit/Netlist contracts.

The standalone core must never require Soveraeign. The intended dependency direction is:

```text
Canvas core
  <- provider/projector adapters
       ├─ local/file
       ├─ Git
       └─ optional Soveraeign
```

See [SPEC.md](SPEC.md) for the contract and [ROADMAP.md](ROADMAP.md) for the progression to 1.0.
