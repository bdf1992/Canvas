# Canvas Roadmap

The roadmap is capability progression, not a promise to accumulate UI features. Each stage should remain independently testable and should only widen the contract when the previous stage has executable evidence.

| Version | Theme | Contract growth | Exit condition |
|---|---|---|---|
| 0.1 | Grounded Field + First Board | Canvas field, Object, Frame, Connection, GroundRef, persistence, provider/projector/renderer extension pattern, optional Board premise, baseline Card rendering, Directory Board | standalone grounding passes; Canvas self-projects its repository; the first premise-bearing Directory Board reuses the same Objects/Connections and visibly renders every contains edge |
| 0.2 | Relational Canvas | richer Board/view semantics, typed relations, measures, grounding paths/hops | multiple premise-bearing Boards can compose the same grounded Objects differently without geometry becoming semantic authority |
| 0.3 | Circuit Grammar | Circuit, Module/Site, Port, Input/Output, constrained directional flow, deterministic Netlist IR | one circuit compiles deterministically from visible canonical connectivity |
| 0.4 | Traversal | Runner contract, pulses/tokens, local executable sites, traversal traces | one local circuit executes and returns an inspectable trace |
| 0.5 | Composition | nested premise-bearing Boards, reusable modules, circuits-of-circuits, explicit boundaries | a circuit/Board/module can be composed without copying hidden ownership |
| 0.6 | Agency | agents inspect/create/place/connect/propose using the same visible grammar | agent changes are fully inspectable and distinguishable from hidden inference |
| 0.7 | History & Collaboration | versions, diffs, sessions, attribution, reconciliation | Canvas/Board evolution can be replayed and compared without losing authorship |
| 0.8 | Evidence | provenance overlays, ground distance, measures, observations/receipts | evidence can be projected without visual state becoming authority |
| 0.9 | Interop & Conformance | provider SDK, runner SDK, renderer contract, migration/version rules, conformance suite | independent implementations pass portable conformance fixtures |
| 1.0 | Stable Contract | portable schema, reference renderers, circuit compiler, provider/runtime interfaces | stable compatibility contract with migration and conformance guarantees |

## 0.1 execution order

0.1 is self-hosted and premise-first:

1. **Grounded Field** — local-file reference + grounded annotation prove the minimal durable grammar.
2. **Repository field** — Canvas projects its own exact Git tree into that unchanged source grammar.
3. **Infinite Canvas interaction** — wheel/trackpad changes depth (zoom), drag changes location (pan), with no finite page edge.
4. **Card rendering capability** — exact provider bytes can render as text or sandboxed HTML when a Board premise needs object content.
5. **Directory Board** — the first real Board states `What exists here, and how is it contained?`, reuses the repository Objects and `contains` Connections, removes Cards from the topology view, and renders directory structure + Connection geometry directly.

The repository field and Directory Board are intentionally different artifacts:

```text
repository field = what source objects/relations exist
Directory Board  = one authored premise over that field
```

## Generalization rule

New source systems should normally add a Provider and/or Projector. New Board forms should normally add a premise + arrangement + renderer over existing grounded Objects/Connections rather than duplicate source semantics.

```text
Provider  -> addressed source resolution / bytes
Projector -> existing Canvas primitives
Board     -> premise + arrangement
Renderer  -> visual grammar appropriate to premise
```

Schema growth is justified only when a real source or Board behavior cannot be represented without loss or contradiction using the existing grammar.

## Board trajectory

Directory Board is the first witness because its premise is already exactly supported by real Git topology.

After that, Board types should be learned from real questions rather than invented as a taxonomy up front. Candidate premises include:

- roadmap — what is planned and in what progression?
- release readiness — what blocks this release?
- architecture — what components exist and how do they relate?
- discussion — what claims, evidence, and unresolved questions are in play?

Each Board should reuse the same grounded world wherever possible.

## Card-rendering trajectory

Cards remain available for Board premises that need content inspection or comparison. Do not create `TextCard`, `HtmlCard`, `MarkdownCard`, `FileCard`, etc. as semantic source types solely to control appearance.

The renderer progression remains:

```text
text/code -> HTML -> structured data -> images/media -> provider-specific rich renderers
```

But a Board may choose not to use Cards at all, as Directory Board demonstrates.

## Dependency rule

Every version MUST remain valid with provider-neutral contracts. Soveraeign may act as the strongest reference integration but MUST NOT become a prerequisite for Canvas core.

## Soveraeign integration trajectory

After Canvas self-hosting and the Directory Board are stable, Soveraeign can progressively demonstrate stronger optional implementations of the generic contracts: exact Asset/AssetVersion resolution, provenance/custody projections, registered operation resolution, governed traversal, Record/Receipt evidence projection, and admitted identity/authority checks.

These integrations prove Canvas can carry high-integrity semantics without embedding those semantics in Canvas itself.

## Scope governor

Do not add a Board type because the visual is attractive. Add it when there is a premise worth answering and grounded Objects/Connections that can answer it.
