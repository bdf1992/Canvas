# Canvas

Canvas is a portable spatial composition capability for arranging addressable things, relating them visibly, and progressively wiring a subset into explicit executable circuits.

Canvas is designed to stand on its own. Integrations such as Soveraeign may provide stronger grounding, execution, custody, provenance, authority, and evidence, but they are providers of those semantics rather than prerequisites for Canvas itself.

## 0.1 — Grounded Field

The first target is deliberately small. A standalone implementation must be able to:

- create and reopen a Canvas;
- place addressable objects/cards;
- create durable user or agent notes;
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

## Architectural boundary

Canvas is not an authority system. Visual state does not create approval, completion, custody, standing, ratification, or authorization. Grouping is neutral. A visible connection is a relation, not hidden execution. Executable semantics are introduced explicitly by later Circuit/Netlist contracts.

The standalone core must never require Soveraeign. The intended dependency direction is:

```text
Canvas core
  ├─ local/file provider
  ├─ generic provider contract
  ├─ generic runner contract
  └─ optional Soveraeign adapter
```

See [SPEC.md](SPEC.md) for the 0.1 contract and [ROADMAP.md](ROADMAP.md) for the progression to 1.0.
