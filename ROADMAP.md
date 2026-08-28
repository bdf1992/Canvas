# Canvas Roadmap

The roadmap is capability progression, not a promise to accumulate UI features. Each stage should remain independently testable and should only widen the contract when the previous stage has executable evidence.

| Version | Theme | Contract growth | Exit condition |
|---|---|---|---|
| 0.1 | Grounded Field + First Board | Canvas field, Object, Frame, Connection, GroundRef, persistence, provider/projector/renderer pattern, optional Board premise, baseline Card rendering, generic Board composition | standalone grounding passes; Canvas self-projects its repository; the first premise-bearing Board reuses the same Objects/Connections and shows them as Cards + visible contains relations without a directory-specific primitive |
| 0.2 | Relational Canvas | richer Board/view semantics, typed relations, measures, grounding paths/hops | multiple premise-bearing Boards compose the same grounded Objects differently without geometry becoming semantic authority |
| 0.3 | Circuit Grammar | Circuit, Module/Site, Port, Input/Output, constrained directional flow, deterministic Netlist IR | one circuit compiles deterministically from visible canonical connectivity |
| 0.4 | Traversal | Runner contract, pulses/tokens, local executable sites, traversal traces | one local circuit executes and returns an inspectable trace |
| 0.5 | Composition | nested premise-bearing Boards, reusable modules, circuits-of-circuits, explicit boundaries | a circuit/Board/module can be composed without copying hidden ownership |
| 0.6 | Agency | agents inspect/create/place/connect/propose using the same visible grammar | agent changes are fully inspectable and distinguishable from hidden inference |
| 0.7 | History & Collaboration | versions, diffs, sessions, attribution, reconciliation | Canvas/Board evolution can be replayed and compared without losing authorship |
| 0.8 | Evidence | provenance overlays, ground distance, measures, observations/receipts | evidence can be projected without visual state becoming authority |
| 0.9 | Interop & Conformance | provider SDK, runner SDK, renderer contract, migration/version rules, conformance suite | independent implementations pass portable conformance fixtures |
| 1.0 | Stable Contract | portable schema, reference renderers, circuit compiler, provider/runtime interfaces | stable compatibility contract with migration and conformance guarantees |

## 0.1 execution order

1. **Grounded Field** — local-file reference + grounded annotation prove the minimal durable grammar.
2. **Repository field** — Canvas projects its own exact Git tree into that source grammar.
3. **Infinite Canvas interaction** — wheel/trackpad changes depth; empty-space drag changes position.
4. **Card rendering capability** — exact provider bytes render through structural/text/sandboxed-HTML Cards without semantic Card subtypes.
5. **First Board** — state `What exists here, and how is it contained?`; reuse repository Objects and `contains` Connections; show the Objects as Cards inside a generic Board Frame; derive hierarchical layout from the Connections.

The directory-like reading is an outcome of the composition, not a new primitive:

```text
repository field
  -> generic Board
       premise
       Cards
       contains Connections
       Frame/layout
```

## Generalization rule

New source systems should normally add a Provider and/or Projector. New Board forms should normally vary premise, selected Cards, Connections, and arrangement rather than add a metaphor-specific core primitive.

```text
Provider  -> addressed source resolution / bytes
Projector -> existing Canvas primitives
Board     -> premise + composition
Card      -> visual rendering of an Object
Connection-> visible stored relation
```

Schema growth is justified only when a real source or Board behavior cannot be represented without loss or contradiction using the existing grammar.

## Board trajectory

The first Board is conversationally directory-like because Git already supplies exact containment topology. It is still built from the generic Board grammar.

After that, Board forms should be learned from real premises rather than invented as a taxonomy up front. Candidate premises include:

- roadmap — what is planned and in what progression?
- release readiness — what blocks this release?
- architecture — what components exist and how do they relate?
- discussion — what claims, evidence, and unresolved questions are in play?

Each should first attempt to reuse `Board + Card + Connection + Frame` before widening the contract.

## Card-rendering trajectory

Do not create `TextCard`, `HtmlCard`, `MarkdownCard`, `FileCard`, `DirectoryCard`, etc. as semantic source types solely to control appearance.

The renderer progression remains:

```text
structural -> text/code -> HTML -> structured data -> images/media -> provider-specific rich renderers
```

## Dependency rule

Every version MUST remain valid with provider-neutral contracts. Soveraeign may act as the strongest reference integration but MUST NOT become a prerequisite for Canvas core.

## Soveraeign integration trajectory

After Canvas self-hosting and the first generic Board are stable, Soveraeign can progressively demonstrate stronger optional implementations of the generic contracts: exact Asset/AssetVersion resolution, provenance/custody projections, registered operation resolution, governed traversal, Record/Receipt evidence projection, and admitted identity/authority checks.

## Scope governor

Do not add a Board primitive because a visual metaphor is attractive. Add a new primitive only when a real Board premise cannot be expressed faithfully by composing existing Cards, Connections, Frames, and grounded Objects.
