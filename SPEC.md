# Canvas 0.1 Contract — Grounded Field

Status: executable baseline

## Definition

Canvas is a shared spatial binding for addressable things. It gives humans and agents one visible grammar for placing, relating, annotating, grouping, rendering, and inspecting durable objects without turning presentation into authority.

Canvas 0.1 does not define workflow execution, domain state transitions, or provider authority. It defines the smallest durable field on which those later capabilities can be composed explicitly.

## Spatial distinctions

### Canvas

Canvas is the spatial field itself: open placement space plus durable objects, frames, connections, and grounding references.

### Board

A Board is a bounded, authored view over a Canvas with an explicit premise/question. A roadmap Board, architecture Board, release-readiness Board, discussion Board, or Directory Board exists because an actor selected a premise and arranged grounded things to answer it.

The JSON schema retains the historical `boards` placement-surface array. A stored entry MAY now contain a non-empty `premise`. In this contract, a placement surface without a premise is not treated as a semantic Board merely because it appears in the `boards` array.

A Board derivation SHOULD reuse existing Objects, GroundRefs, and Connections. It MUST NOT duplicate source objects simply to achieve a different visual arrangement.

### First Board — Directory Board

The first premise-bearing Board is Directory Board:

> **What exists here, and how is it contained?**

It is derived from the exact repository field and uses the same grounded Git Objects and the same stored `contains` Connections. It changes Board premise and arrangement only.

Directory Board represents repository entries as directory/file rows and treats `contains` Connections as primary visible geometry. It deliberately does not render file-content Cards because file contents are not required to answer its premise.

### Object

A durable addressable thing placed on the Canvas field or a Board. An Object may reference provider-backed ground or be a Canvas-native note/annotation/mock/derived object whose meaning remains grounded through explicit Connections.

### Card

A Card is **not a durable object kind**. It is one optional bounded visual rendering of an Object/Resolution.

```text
Object + GroundRef
      -> provider resolves exact thing/bytes
      -> renderer chooses a visual body
      -> Card appears when the Board premise needs that rendering
```

A renderer MAY choose text, HTML, image, structured-data, binary, or other visual strategies. Those strategies MUST NOT create `TextCard`, `HtmlCard`, `FileCard`, or equivalent semantic object families merely for presentation.

For provider-backed content, Card rendering SHOULD use the exact resolved revision/digest represented by the GroundRef rather than mutable working-tree state.

### Frame

A neutral visual grouping primitive. Membership in a Frame MUST NOT imply provider/domain state and a Frame does not create a Board premise.

### Connection

A visible, durable relation between addressable endpoints. 0.1 keeps the relation model intentionally small: `connection_id`, `from`, `to`, `kind`, and optional `direction`.

When a Board premise is relational, stored Connections SHOULD become primary visible geometry rather than decorative lines inferred from proximity.

### GroundRef

A provider-neutral reference to addressed external ground.

```json
{
  "provider": "local-file",
  "id": "example.txt",
  "version": null,
  "digest": null
}
```

Providers own resolution, version, digest, authority, custody, provenance, and availability semantics.

## Generalization by projection, Board derivation, and rendering

```text
Provider  -> resolves addressed source objects and optional bytes
Projector -> deterministically maps source objects/relations into Canvas primitives
Board     -> states a premise and arranges existing Objects/Connections
Renderer  -> presents the Board using a visual grammar appropriate to the premise
```

Projectors and renderers are implementation behavior, not new durable source-object families. Board premise/arrangement MAY be durable because they are authored view state.

A valid projector:

1. emits only the portable Canvas grammar unless a later contract explicitly widens it;
2. grounds projected Objects in exact provider references;
3. emits a Connection only when the source supports that relation or the user explicitly creates it;
4. keeps raw projection layout semantically neutral;
5. pins enough source revision information for reproduction;
6. does not write back merely because presentation changes.

A valid Board derivation:

1. states a non-empty premise when it is presented as a Board;
2. reuses grounded Objects/Connections wherever they already answer the premise;
3. creates no duplicate source objects merely for representation;
4. makes Board arrangement explicit and inspectable;
5. leaves provider state and GroundRefs unchanged.

A valid renderer:

1. does not mutate the semantic Canvas/Board document merely by rendering it;
2. chooses a visual representation that answers the Board premise;
3. preserves the distinction between visual fidelity and authority;
4. contains active/untrusted content when such content is rendered;
5. does not invent durable semantic relations from geometry.

Git is the first provider/projector witness. Git trees/blobs remain Git objects; each is projected as a grounded `reference` Object and tree membership becomes `contains`.

## Baseline Board renderer — Directory

Directory Board renders:

- one visible bounded Board frame;
- one row endpoint for each repository Object;
- directory indentation derived from stored `contains` topology;
- one visible branch/edge for each visible stored `contains` Connection;
- collapse/expand as transient presentation state;
- exact GroundRef digest metadata as secondary inspection context.

It renders **no Cards** because content preview is not needed to answer the directory premise.

## Baseline Card renderers

Card rendering remains available to Board premises that need object content.

### Text

UTF-8 text/code resolves from exact provider bytes and renders as escaped readable text. Rendering MUST NOT interpret text as outer-page HTML.

### HTML

HTML/HTM resolves from exact provider bytes and renders visually in an isolated sandbox. The reference renderer MUST disable script execution and external/network capabilities for the preview. HTML rendering is evidence of visual representation, not permission to execute the document.

### Binary fallback

Unknown/non-text bytes render an explicit binary fallback rather than inventing meaning.

## Invariants

1. **Standalone coherence** — Canvas core MUST function without Soveraeign or any other specific provider.
2. **Addressable durability** — anything preserved as meaningful Canvas state MUST have durable identity.
3. **Grounding closure** — every durable derived/annotation object MUST have at least one explicit traversable path to provider-backed ground, unless it directly carries a GroundRef.
4. **No hidden inference** — Canvas MUST explain the stored path by which an object is grounded.
5. **Grouping neutrality** — frames, coordinates, color, proximity, and layout MUST NOT change provider/domain state.
6. **Premise explicitness** — anything presented as a Board MUST expose the premise that justifies its arrangement/representation.
7. **Presentation is not authority** — Board arrangement, Card rendering, labels, badges, visual emphasis, or placement MUST NOT create approval, completion, ratification, authorization, custody, or standing.
8. **Reference, not ownership** — deleting a Canvas/Object/Board MUST NOT imply deletion of referenced provider resources.
9. **Visible relation** — durable semantic connection MUST exist as explicit Connection data rather than inferred geometry.
10. **Provider isolation** — provider-specific concepts MUST NOT become required portable-core fields.
11. **Human/agent grammar parity** — agent-created durable objects/connections/Boards MUST be inspectable through the same grammar as human-created ones.
12. **Projection fidelity** — a projector MUST NOT manufacture source relations for convenience.
13. **Revision closure** — when exact revisions exist, durable source projections MUST identify the exact revision used.
14. **Board non-duplication** — deriving a Board SHOULD NOT duplicate already-grounded source Objects/Connections solely for presentation.
15. **Render fidelity** — a provider-backed Card MUST represent the addressed thing/revision, not silently substitute mutable nearby state.
16. **Active-content containment** — rendering addressed active content MUST NOT silently grant it execution authority in the Canvas host.

## Grounding

A Canvas Object is grounded when it directly contains valid GroundRefs or following stored Connections reaches an Object with valid GroundRefs. `ground_distance` is the derived minimum Connection-hop count to provider-backed ground.

Grounding does not mean truth, authority, approval, or correctness. It means the durable object's meaning is not epistemically floating.

## Persistence

0.1 persistence MUST round-trip identity, Board premise/placement where present, frame membership, connections, and GroundRefs without semantic loss. Rendered provider bytes are not required to be copied into the Canvas document.

## Provider contract

0.1 requires a provider boundary conceptually equivalent to:

```text
resolve(GroundRef) -> Resolution
```

A Resolution MAY include display bytes/content metadata, existence, version, digest, provenance, or other provider-defined facts. Canvas core MUST NOT treat optional provider facts as authority unless the provider declares their semantics.

## 0.1 acceptance witnesses

### Grounded Field

A standalone implementation can create a Canvas, place a grounded local object and note, connect them, move/group them neutrally, save/reload them, and explain the note's grounding path without mutating the referenced resource.

### Repository field

A conforming Git projector can pin an exact commit, enumerate the complete tracked Git tree, emit one grounded `reference` Object for each represented Git tree/blob, emit only real `contains` relations, validate the portable grammar, resolve every GroundRef to the exact Git digest, and reproduce the same semantic projection from the same revision.

The primary source witness is Canvas projecting **its own repository** first.

### Directory Board

The first real Board proves that:

1. its stored premise is `What exists here, and how is it contained?`;
2. it is derived from the repository field without creating any new repository Objects;
3. it preserves every original GroundRef and `contains` Connection;
4. it rearranges Objects into deterministic directory indentation/rows;
5. its renderer shows one bounded Board frame rather than a wall of Cards;
6. each visible parent/child line corresponds to a stored `contains` Connection;
7. collapse/search/selection/zoom/pan are presentation-only;
8. the same field deterministically produces the same Directory Board document.

### Card rendering capability

Separate capability tests continue to prove that exact Git blob bytes can render as UTF-8 text or sandboxed HTML without dirty-working-tree substitution, new durable Object kinds, or execution authority.

## Explicit non-goals for 0.1

- generalized whiteboard drawing;
- multiplayer cursors;
- workflow orchestration;
- executable circuits;
- hidden semantic inference;
- graph database requirements;
- universal scoring;
- provider-specific authority logic;
- Soveraeign dependency;
- treating every placement surface/provider projection as a Board;
- defaulting every Board to Card rendering;
- creating semantic card classes merely to support visual rendering;
- inventing a taxonomy of future Board types before their premises exist.
