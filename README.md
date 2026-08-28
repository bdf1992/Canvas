# Canvas

Canvas is a portable spatial composition capability for arranging addressable things, relating them visibly, and progressively wiring a subset into explicit executable circuits.

Canvas is designed to stand on its own. Integrations such as Soveraeign may provide stronger grounding, execution, custody, provenance, authority, and evidence, but they are providers of those semantics rather than prerequisites for Canvas itself.

## General extension model

Canvas should generalize by projecting already-addressed things into a small shared grammar, not by inventing a new card type for every source system.

```text
Provider  -> resolves addressed things
Projector -> maps source objects/relations into Canvas
Renderer  -> shows the same Canvas document
```

A Projector is not a new durable Canvas object. It is a deterministic adapter that emits existing Canvas primitives: `Board`, `Object`, `Frame`, `Connection`, and `GroundRef`.

Task 1 proves this with Git. Git trees and blobs remain Git trees and blobs; Canvas projects each one as an ordinary grounded `reference` object and projects only real tree membership as explicit `contains` connections.

## 0.1 — Grounded Field

The first contract is deliberately small. A standalone implementation can:

- create and reopen a Canvas;
- place addressable objects/cards;
- move and resize objects;
- group objects with semantically neutral frames;
- connect objects visibly;
- attach provider-neutral `GroundRef`s;
- persist and reload the composition;
- explain stored grounding paths without hidden inference.

The core 0.1 vocabulary is:

`Canvas`, `Board`, `Object`, `Frame`, `Connection`, and `GroundRef`.

A `GroundRef` identifies something through a provider without making provider-specific concepts part of the portable Canvas contract.

```text
GroundRef {
  provider
  id
  version?
  digest?
}
```

## Task 1 — Repository as Canvas

`repo_canvas.py` projects an exact local Git revision into one Canvas Board without widening the 0.1 schema.

```bash
python repo_canvas.py project /path/to/repo \
  --source-id owner/repo \
  --output repo.canvas.json \
  --html repo-board.html

python repo_canvas.py verify repo.canvas.json /path/to/repo \
  --source-id owner/repo
```

The first CI witness clones the complete `bdf1992/Soveraeign` repository, pins its exact HEAD commit, emits the Canvas JSON and a directly inspectable HTML board, resolves every projected Git object, and proves a second projection of the same revision is byte-identical.

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

See [SPEC.md](SPEC.md) for the 0.1 contract and [ROADMAP.md](ROADMAP.md) for the progression to 1.0.
