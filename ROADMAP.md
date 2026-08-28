# Canvas Roadmap

The roadmap is capability progression, not a promise to accumulate UI features. Each stage should remain independently testable and should only widen the contract when the previous stage has executable evidence.

| Version | Theme | Contract growth | Exit condition |
|---|---|---|---|
| 0.1 | Grounded Field | Canvas field, Object, Frame, Connection, GroundRef, persistence, provider/projector/renderer extension pattern, baseline Card rendering | standalone grounding passes; Canvas self-projects its repository; exact text/HTML bytes visibly render without schema/object-kind widening |
| 0.2 | Relational Canvas | typed relations, measures, grounding paths/hops, premise-bearing Board/view semantics | authored Boards can state a premise and compose existing Objects without geometry becoming semantic authority |
| 0.3 | Circuit Grammar | Circuit, Module/Site, Port, Input/Output, constrained directional flow, deterministic Netlist IR | one circuit compiles deterministically from visible canonical connectivity |
| 0.4 | Traversal | Runner contract, pulses/tokens, local executable sites, traversal traces | one local circuit executes and returns an inspectable trace |
| 0.5 | Composition | nested premise-bearing Boards, reusable modules, circuits-of-circuits, explicit boundaries | a circuit/Board/module can be composed without copying hidden ownership |
| 0.6 | Agency | agents inspect/create/place/connect/propose using the same visible grammar | agent changes are fully inspectable and distinguishable from hidden inference |
| 0.7 | History & Collaboration | versions, diffs, sessions, attribution, reconciliation | Canvas/Board evolution can be replayed and compared without losing authorship |
| 0.8 | Evidence | provenance overlays, ground distance, measures, observations/receipts | evidence can be projected without visual state becoming authority |
| 0.9 | Interop & Conformance | provider SDK, runner SDK, renderer contract, migration/version rules, conformance suite | independent implementations pass portable conformance fixtures |
| 1.0 | Stable Contract | portable schema, reference renderer, circuit compiler, provider/runtime interfaces | stable compatibility contract with migration and conformance guarantees |

## 0.1 execution order

0.1 is now intentionally self-hosted and field-first:

1. **Grounded Field** — local-file reference + grounded annotation prove the minimal durable grammar.
2. **Repository Canvas field** — Canvas projects its own exact Git tree into that unchanged grammar.
3. **Infinite navigation** — wheel/trackpad changes depth (zoom), drag changes location (pan), with no finite page edge.
4. **Card rendering** — exact provider bytes render visibly inside bounded Cards; UTF-8 text and sandboxed HTML are the first witnesses.

The raw repository projection is not a Board. It is source material and module topology on the Canvas. A Board begins when an actor gives a view a premise, such as “roadmap”, “release readiness”, “architecture”, or “discussion”.

## Generalization rule

New source systems should normally add a Provider, Projector, and/or Renderer rather than a new Canvas Object family.

```text
Provider  -> addressed source resolution / bytes
Projector -> existing Canvas primitives
Renderer  -> bounded visual Card
```

Schema growth is justified only when a real source or behavior cannot be represented without loss or contradiction using the existing grammar.

## Card-rendering trajectory

Do not create `TextCard`, `HtmlCard`, `MarkdownCard`, `FileCard`, etc. solely to control appearance. Keep one grounded Object and let rendering strategies evolve independently.

The near progression is:

```text
text/code -> HTML -> structured data -> images/media -> provider-specific rich renderers
```

Each renderer must preserve exact grounding and contain active/untrusted content.

## Board trajectory

Board semantics should be widened only when we build the first real premise-bearing Board. The likely first witness is a **Canvas roadmap Board** assembled from already-existing repository objects rather than new duplicate objects.

That Board should answer an explicit premise/question and be distinguishable from the complete repository field beneath it.

## Dependency rule

Every version MUST remain valid with provider-neutral contracts. Soveraeign may act as the strongest reference integration but MUST NOT become a prerequisite for Canvas core.

## Soveraeign integration trajectory

After Canvas self-hosting and basic Card rendering are stable, Soveraeign can progressively demonstrate stronger optional implementations of the generic contracts: exact Asset/AssetVersion resolution, provenance/custody projections, registered operation resolution, governed traversal, Record/Receipt evidence projection, and admitted identity/authority checks.

These integrations prove Canvas can carry high-integrity semantics without embedding those semantics in Canvas itself.

## Scope governor

Do not advance a version because a feature is attractive. Advance when the current contract has a witness and the next missing capability cannot be expressed cleanly without widening the grammar.
