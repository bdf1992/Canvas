# Card rendering contract

Status: first executable rendering contract

A Card is a bounded visual rendering of one addressed Canvas Object. It is not a durable Object kind and it does not own the thing it renders.

## Anatomy

Every Card has three visible layers:

```text
Card
├─ Header
│  ├─ renderer / provider / source kind
│  ├─ identity / title
│  ├─ addressed path or locator
│  ├─ grounding revision / digest
│  └─ incoming / outgoing relation counts
├─ Summary
│  └─ concise explanation of what the addressed thing is
└─ Context / content
   └─ expandable resolved rendering such as text, HTML, structure, media, or fallback
```

### Header

The Header answers **what am I looking at and where did it come from?** without opening the Card.

It SHOULD expose enough grounding and topology context to distinguish two similarly named Cards without turning provenance metadata into the dominant visual.

### Summary

The Summary answers **why might I care about this Card?** at Board-reading distance.

The first implementation derives summaries from the resolved object: renderer/type, byte size, relation counts, and a short content cue. This derived Summary is renderer state, not persisted semantic Object state.

Do not add a durable `summary` field until an authored summary has a demonstrated meaning distinct from renderer-derived explanation.

### Context / content

Context answers **show me more of the addressed thing**.

It is collapsed by default. Expanding it MUST NOT mutate the Canvas document, provider state, GroundRef, Card identity, or stored Board layout.

Resolved content remains exact to the GroundRef revision/digest. Active content remains contained; HTML is sandboxed.

## Expansion behavior

Expansion is transient inspection state. An expanded Card may overlay nearby field space rather than forcing a Board re-layout. Relation anchor positions remain tied to the stored Card placement so inspecting content cannot silently rewrite topology.

## Relation surfaces

Cards expose incoming and outgoing relation counts in the Header. These counts summarize existing stored Connections; they are not relations themselves.

Selecting a Card SHOULD make its exact incident Connections easier to follow.

## Dense relation routing

Large fan-out must not turn the Board into an unreadable line wall.

The reference renderer may derive presentation-only routing bundles:

```text
Card ── shared trunk ─┬─ exact Connection → Card
                      ├─ exact Connection → Card
                      ├─ exact Connection → Card
                      └─ exact Connection → Card
```

Rules:

1. every stored Connection remains individually represented and inspectable;
2. a routing bundle is not persisted as a synthetic Connection;
3. low zoom may de-emphasize individual branches while preserving the bundle shape;
4. selection/focus restores emphasis to exact incident Connections;
5. routing geometry never creates semantic relation data.

## Invariants

- Card is representation, not Object ontology.
- Header, Summary, and Context are present for every Card.
- Summary is concise enough to remain useful while Context is collapsed.
- Context expansion is reversible view state.
- exact provider bytes/revisions remain the rendering ground.
- relation counts and routing are projections of stored Connections.
- Card rendering never creates authority, custody, approval, completion, or standing.
