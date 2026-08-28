# Canvas Roadmap

The roadmap is capability progression, not a promise to accumulate UI features. Each stage should remain independently testable and should only widen the contract when the previous stage has executable evidence.

| Version | Theme | Contract growth | Exit condition |
|---|---|---|---|
| 0.1 | Grounded Field | Canvas, Board, Object, Frame, Connection, GroundRef, persistence, provider/projector/renderer extension pattern | standalone grounding passes and one complete external topology (Git repository) projects without schema widening |
| 0.2 | Relational Canvas | typed relations, measures, grounding paths/hops, richer views | relations remain explicit and inspectable; no geometry-as-semantics |
| 0.3 | Circuit Grammar | Circuit, Module/Site, Port, Input/Output, constrained directional flow, deterministic Netlist IR | one circuit compiles deterministically from visible canonical connectivity |
| 0.4 | Traversal | Runner contract, pulses/tokens, local executable sites, traversal traces | one local circuit executes and returns an inspectable trace |
| 0.5 | Composition | nested boards, reusable modules, circuits-of-circuits, explicit boundaries | a circuit can be composed as a module without exposing/copying internal ownership |
| 0.6 | Agency | agents inspect/create/place/connect/propose using the same visible grammar | agent changes are fully inspectable and distinguishable from hidden inference |
| 0.7 | History & Collaboration | versions, diffs, sessions, attribution, reconciliation | board evolution can be replayed/compared without losing authorship |
| 0.8 | Evidence | provenance overlays, ground distance, measures, observations/receipts | evidence can be projected without visual state becoming authority |
| 0.9 | Interop & Conformance | provider SDK, runner SDK, renderer contract, migration/version rules, conformance suite | independent implementation can pass portable conformance fixtures |
| 1.0 | Stable Contract | portable schema, reference renderer, circuit compiler, provider/runtime interfaces | stable compatibility contract with migration and conformance guarantees |

## 0.1 execution order

0.1 now has two proof layers:

1. **Grounded Field** — local-file reference + grounded annotation proved the minimal grammar.
2. **Task 1: repository projection** — project the complete `bdf1992/Soveraeign` Git tree into that unchanged grammar and render it as one board in the shared GitHub environment.

Do not advance the optional Soveraeign semantic adapter ahead of Task 1. First prove Canvas is useful by representing the repository we already share without importing Soveraeign domain semantics.

## Generalization rule

New source systems should normally add a Provider and/or Projector, not a new Canvas object family.

```text
Provider  -> addressed source resolution
Projector -> existing Canvas primitives
Renderer  -> inspectable presentation
```

Schema growth is justified only when a real source or behavior cannot be represented without loss or contradiction using the existing grammar.

## Dependency rule

Every version MUST remain valid with provider-neutral contracts. Soveraeign may act as the strongest reference integration but MUST NOT become a prerequisite for Canvas core.

## Soveraeign integration trajectory

After the repository projection is accepted, Soveraeign can progressively demonstrate stronger optional implementations of the generic contracts:

- `GroundRef` -> exact Asset / AssetVersion resolution;
- provider facts -> provenance and custody projections;
- Circuit site -> registered operation resolution;
- traversal -> governed Runtime execution;
- observation -> Record / Receipt / evidence projection;
- actor interaction -> admitted identity, attribution, and authority checks.

These integrations prove Canvas can carry high-integrity semantics without embedding those semantics in Canvas itself.

## Scope governor

Do not advance a version because a feature is attractive. Advance when the current contract has a witness and the next missing capability cannot be expressed cleanly without widening the grammar.
