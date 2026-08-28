# Canvas

Canvas is a portable spatial composition capability for arranging addressable things, relating them visibly, and progressively wiring a subset into explicit executable circuits.

Canvas is designed to stand on its own. Integrations such as Soveraeign may provide stronger grounding, execution, custody, provenance, authority, and evidence, but they are providers of those semantics rather than prerequisites for Canvas itself.

## Canvas, Board, Frame, Card, Connection

- **Canvas** is the open spatial field.
- **Board** is a bounded authored composition with an explicit premise.
- **Frame** is neutral visual grouping/boundary. It does not create the Board premise by itself.
- **Card** is a bounded visual rendering of an addressed Object/Resolution. Card is presentation, not a semantic Object kind.
- **Connection** is explicit stored relation data between Objects. A Board may arrange Cards so those Connections become its primary topology.

A placement surface without a premise is not treated as a semantic Board. The portable schema permits an optional `Board.premise` so this distinction is durable and inspectable.

## Reusable Board grammar

Canvas should not add a new primitive for each familiar visual metaphor. A Board is assembled from the same reusable grammar:

```text
Board premise
+ existing grounded Objects
+ Card renderings of those Objects
+ explicit Connections
+ Frames/layout
```

Provider/source metaphors emerge from that composition. They are not new Canvas object families.

```text
Provider  -> resolves addressed things and bytes
Projector -> maps source Objects/relations into Canvas
Board     -> states a premise and composes existing Objects/Connections
Renderer  -> shows those Objects as Cards and those relations as visible geometry
```

## First Board — repository containment

The first Board asks:

> **What exists here, and how is it contained?**

This can be called a **Directory Board** as a human description of the result, but `directory` is not a Canvas primitive, renderer, Object kind, or special Board class.

`repo_canvas.py` projects the exact Git repository into a source field. `board_view.py` then authors a generic Board over the same Objects and `contains` Connections.

```text
Git repository
  -> repository field
       grounded Objects
       contains Connections
  -> generic Board
       premise: What exists here, and how is it contained?
       Cards: render those same Objects
       relations: render those same contains Connections
       layout: hierarchy derived from the Connections
```

No repository Object or Connection is duplicated.

```bash
python repo_canvas.py project /path/to/repo \
  --source-id owner/repo \
  --output repo.field.canvas.json

python board_view.py build repo.field.canvas.json \
  --board-id repository-containment \
  --label "Directory Board" \
  --premise "What exists here, and how is it contained?" \
  --relation contains \
  --repo /path/to/repo \
  --output repo.board.canvas.json \
  --html repo.board.html

python repo_canvas.py verify repo.board.canvas.json /path/to/repo \
  --source-id owner/repo
```

The primary CI witness is **Canvas composing its own repository into this first generic Board**.

## Card rendering

Cards remain the common visual object surface across Board types. Existing baseline renderers include:

- Git tree/reference -> compact structural Card;
- UTF-8 text/code -> readable exact-byte preview;
- HTML/HTM -> sandboxed visual document preview;
- unknown binary -> explicit fallback.

Renderer choice does not create `DirectoryCard`, `FileCard`, `TextCard`, `HtmlCard`, or other semantic Object kinds.

## Interaction

The Board sits within the infinite Canvas field:

- wheel / trackpad -> zoom at pointer;
- drag empty Canvas -> pan;
- click Card -> select it and highlight incident Connections;
- double-click / Enter -> focus Card;
- `/` -> Find Card;
- Home / `0` -> deterministic Board home.

Visible relation geometry is generated from stored Connection records rather than inferred from proximity.

See [DESIGN.md](DESIGN.md) for the executable interaction philosophy.

## 0.1 — Grounded Field

The standalone implementation can:

- create and reopen a Canvas;
- place addressable Objects;
- connect Objects visibly;
- attach provider-neutral `GroundRef`s;
- persist and reload compositions;
- explain stored grounding paths without hidden inference;
- project an exact Git repository without source-specific Object kinds;
- render exact provider bytes as Cards;
- author a premise-bearing Board from existing Objects/Connections;
- arrange a Board from an explicit relation without turning that source metaphor into a primitive.

The durable 0.1 vocabulary remains `Canvas`, `Board`/placement surface, `Object`, `Frame`, `Connection`, and `GroundRef`.

## Architectural boundary

Canvas is not an authority system. Visual state does not create approval, completion, custody, standing, ratification, or authorization. Grouping is neutral. Visible geometry cannot invent a relation. Executable semantics are introduced explicitly by later Circuit/Netlist contracts.

The standalone core must never require Soveraeign. The intended dependency direction is:

```text
Canvas core
  <- provider/projector adapters
       ├─ local/file
       ├─ Git
       └─ optional Soveraeign
```

See [SPEC.md](SPEC.md) for the contract, [DESIGN.md](DESIGN.md) for the interaction philosophy, and [ROADMAP.md](ROADMAP.md) for the progression to 1.0.
