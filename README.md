# Canvas

Canvas is a portable spatial composition capability for arranging addressable things, relating them visibly, and progressively wiring a subset into explicit executable circuits.

Canvas is designed to stand on its own. Integrations such as Soveraeign may provide stronger grounding, execution, custody, provenance, authority, and evidence, but they are providers of those semantics rather than prerequisites for Canvas itself.

## Canvas, Board, Frame, and Card

These are different layers.

- **Canvas** is the open spatial field.
- **Board** is a bounded authored view with an explicit premise. A placement surface without a premise is not treated as a Board.
- **Frame** is neutral visual grouping; it does not create a premise.
- **Card** is one optional bounded rendering of an addressed thing. Cards are useful when a Board premise is about object content; they are not the default representation for every Board.
- **Connection** is explicit relation data and can be the primary geometry of a Board.

The portable schema now permits an optional `premise` on stored board records. This keeps the historical placement surface readable while allowing the first real premise-bearing Board to be explicit.

## General extension model

Canvas generalizes by projecting already-addressed things into a small shared grammar, not by inventing new source-specific object families.

```text
Provider  -> resolves addressed things and bytes
Projector -> maps source objects/relations into Canvas
Board     -> states a premise and arranges existing Objects/Connections
Renderer  -> presents that Board through an appropriate visual grammar
```

A Board derivation should normally reuse existing Objects, GroundRefs, and Connections. A directory row, text Card, HTML Card, image Card, etc. is presentation rather than a new semantic source Object.

## First Board — Directory Board

The first real Board is deliberately simple:

> **What exists here, and how is it contained?**

`repo_canvas.py` first projects the exact Git repository into the Canvas field. `directory_board.py` then derives a premise-bearing Directory Board from the same Objects and the same `contains` Connections.

```text
Git repository
  -> repository field
  -> Directory Board
       premise: What exists here, and how is it contained?
       representation: directory/file rows
       relation geometry: contains Connections
```

The Directory Board creates no duplicate repository Objects and no duplicate Connections. It only adds Board premise and directory arrangement.

```bash
python repo_canvas.py project /path/to/repo \
  --source-id owner/repo \
  --output repo.field.canvas.json

python directory_board.py build repo.field.canvas.json \
  --output repo.directory.canvas.json \
  --html repo.directory.html

python repo_canvas.py verify repo.directory.canvas.json /path/to/repo \
  --source-id owner/repo
```

The primary CI witness is **Canvas showing its own repository as a Directory Board**.

## Directory Board interaction

The Board itself is one bounded frame on the infinite Canvas. Repository entries are rows/endpoints rather than Cards.

- wheel / trackpad -> zoom at pointer;
- drag empty Canvas -> pan;
- directory disclosure -> collapse / expand;
- click row -> select endpoint / relation context;
- `/` -> Find path;
- Enter in Find -> focus match;
- Home / `0` -> deterministic Board home.

Every drawn branch line corresponds to a stored `contains` Connection.

See [DESIGN.md](DESIGN.md) for the executable interaction philosophy.

## Card rendering remains a capability

Card rendering is not removed from Canvas. It is simply no longer used where the Board premise is directory topology.

Existing baseline Card renderers remain available:

- UTF-8 text/code -> readable text preview;
- HTML/HTM -> sandboxed visual document preview;
- unknown binary -> explicit binary fallback.

A future Board can choose these renderers when its premise requires reading or comparing object content.

## 0.1 — Grounded Field

The standalone implementation can:

- create and reopen a Canvas;
- place addressable objects;
- connect objects visibly;
- attach provider-neutral `GroundRef`s;
- persist and reload compositions;
- explain stored grounding paths without hidden inference;
- project an exact Git repository without source-specific Object kinds;
- derive a Directory Board without duplicating Objects or Connections;
- show stored `contains` relations as visible directory geometry;
- retain baseline exact-byte Card rendering for Board types that need it.

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
