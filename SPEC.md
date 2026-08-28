# Canvas 0.1 Contract — Grounded Field

Status: executable baseline

## Definition

Canvas is a shared spatial binding for addressable things. It gives humans and agents one visible grammar for placing, relating, annotating, grouping, rendering, and inspecting durable objects without turning presentation into authority.

Canvas 0.1 does not define workflow execution, domain state transitions, or provider authority. It defines the smallest durable field on which those later capabilities can be composed explicitly.

## Spatial distinctions

### Canvas

Canvas is the spatial field itself: open placement space plus durable Objects, Frames, Connections, and GroundRefs.

### Board

A Board is a bounded authored composition over a Canvas with an explicit premise/question. A placement surface without a premise is not treated as a semantic Board merely because it appears in the historical `boards` array.

A Board SHOULD normally reuse existing grounded Objects and Connections and compose them through Cards, Frames, and arrangement. It MUST NOT duplicate source Objects merely to achieve a different view.

The reusable Board grammar is:

```text
Board premise
+ Cards rendering grounded Objects
+ explicit Connections
+ Frames/layout
```

### First Board — repository containment

The first premise-bearing Board asks:

> **What exists here, and how is it contained?**

Humans may call this a **Directory Board**, but `directory` is not a Canvas primitive, Object kind, renderer, or special Board class.

It is derived from the exact repository field and uses the same grounded Git Objects and the same stored `contains` Connections. It adds Board premise, Frame, and deterministic hierarchical arrangement only.

The directory-like representation emerges from ordinary Cards connected by ordinary `contains` Connections.

### Object

A durable addressable thing placed on the Canvas field or a Board. An Object may reference provider-backed ground or be a Canvas-native note/annotation/mock/derived Object whose meaning remains grounded through explicit Connections.

### Card

A Card is **not a durable Object kind**. It is a bounded visual rendering of an Object/Resolution.

```text
Object + GroundRef
      -> provider resolves exact thing/bytes
      -> renderer chooses a visual body
      -> Card appears on a Board/Canvas
```

A renderer MAY choose structural, text, HTML, image, structured-data, binary, or other strategies. Those strategies MUST NOT create `DirectoryCard`, `TextCard`, `HtmlCard`, `FileCard`, or equivalent semantic Object families merely for presentation.

For provider-backed content, Card rendering SHOULD use the exact revision/digest represented by the GroundRef rather than mutable working-tree state.

### Frame

A neutral visual grouping/boundary primitive. Membership in a Frame MUST NOT imply provider/domain state and a Frame does not create a Board premise.

### Connection

A visible durable relation between addressable endpoints. 0.1 keeps the relation model intentionally small: `connection_id`, `from`, `to`, `kind`, and optional `direction`.

Visible relation geometry MUST be backed by stored Connection data rather than inferred from proximity.

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

## Generalization by projection, Board composition, and rendering

```text
Provider  -> resolves addressed source Objects and optional bytes
Projector -> deterministically maps source Objects/relations into Canvas primitives
Board     -> states a premise and composes existing Objects/Connections
Renderer  -> renders those Objects as Cards and Connections as visible geometry
```

Projectors and renderers are implementation behavior, not new durable source-object families. Board premise/arrangement MAY be durable because they are authored view state.

A valid projector:

1. emits only the portable Canvas grammar unless a later contract explicitly widens it;
2. grounds projected Objects in exact provider references;
3. emits a Connection only when the source supports that relation or the user explicitly creates it;
4. keeps raw projection layout semantically neutral;
5. pins enough source revision information for reproduction;
6. does not write back merely because presentation changes.

A valid Board composition:

1. states a non-empty premise when presented as a Board;
2. reuses grounded Objects/Connections wherever they already answer the premise;
3. uses common Canvas primitives before introducing a new metaphor-specific primitive;
4. makes arrangement/Frame state explicit and inspectable;
5. leaves provider state and GroundRefs unchanged;
6. creates zero new Objects or Connections unless the Board author explicitly authors new semantic content/relations.

A valid renderer:

1. does not mutate the semantic Canvas/Board document merely by rendering it;
2. renders represented Objects through Cards or another already-defined portable visual boundary;
3. renders Connection geometry only from stored Connection data;
4. preserves the distinction between visual fidelity and authority;
5. contains active/untrusted content when such content is rendered.

Git is the first provider/projector witness. Git trees/blobs remain Git Objects; each is projected as a grounded `reference` Object and tree membership becomes `contains`.

## First Board reference rendering

The first Board uses the generic Board renderer with:

```text
premise       What exists here, and how is it contained?
relation      contains
arrangement   hierarchy derived from contains
Objects       unchanged repository Objects
Cards         ordinary Card rendering strategies
Connections   unchanged contains Connections
Frame         one generic Board boundary
```

This configuration is directory-like, but no directory-specific UI primitive is required.

## Baseline Card renderers

### Structural

A Git tree/reference may render as a compact structural Card showing identity and immediate relation context.

### Text

UTF-8 text/code resolves from exact provider bytes and renders as escaped readable text. Rendering MUST NOT interpret text as outer-page HTML.

### HTML

HTML/HTM resolves from exact provider bytes and renders visually in an isolated sandbox. The reference renderer MUST disable script execution and external/network capabilities for the preview. HTML rendering is evidence of visual representation, not permission to execute the document.

### Binary fallback

Unknown/non-text bytes render an explicit fallback rather than inventing meaning.

## Invariants

1. **Standalone coherence** — Canvas core MUST function without Soveraeign or any specific provider.
2. **Addressable durability** — anything preserved as meaningful Canvas state MUST have durable identity.
3. **Grounding closure** — every durable derived/annotation Object MUST have at least one explicit traversable path to provider-backed ground, unless it directly carries a GroundRef.
4. **No hidden inference** — Canvas MUST explain the stored path by which an Object is grounded.
5. **Grouping neutrality** — Frames, coordinates, color, proximity, and layout MUST NOT change provider/domain state.
6. **Premise explicitness** — anything presented as a Board MUST expose the premise that justifies its composition.
7. **Common grammar before special primitive** — Board metaphors SHOULD be expressed with Board + Card + Connection + Frame before new primitives are considered.
8. **Presentation is not authority** — Board arrangement, Card rendering, labels, badges, emphasis, or placement MUST NOT create approval, completion, ratification, authorization, custody, or standing.
9. **Reference, not ownership** — deleting a Canvas/Object/Board MUST NOT imply deletion of referenced provider resources.
10. **Visible relation** — durable semantic connection MUST exist as explicit Connection data rather than inferred geometry.
11. **Provider isolation** — provider-specific concepts MUST NOT become required portable-core fields.
12. **Human/agent grammar parity** — agent-created durable Objects/Connections/Boards MUST be inspectable through the same grammar as human-created ones.
13. **Projection fidelity** — a projector MUST NOT manufacture source relations for convenience.
14. **Revision closure** — when exact revisions exist, durable source projections MUST identify the exact revision used.
15. **Board non-duplication** — deriving a Board SHOULD NOT duplicate already-grounded source Objects/Connections solely for presentation.
16. **Render fidelity** — a provider-backed Card MUST represent the addressed thing/revision, not silently substitute mutable nearby state.
17. **Active-content containment** — rendering addressed active content MUST NOT silently grant it execution authority in the Canvas host.

## Grounding

A Canvas Object is grounded when it directly contains valid GroundRefs or following stored Connections reaches an Object with valid GroundRefs. `ground_distance` is the derived minimum Connection-hop count to provider-backed ground.

Grounding does not mean truth, authority, approval, or correctness. It means the durable Object's meaning is not epistemically floating.

## Persistence

0.1 persistence MUST round-trip identity, Board premise/placement where present, Frame membership, Connections, and GroundRefs without semantic loss. Rendered provider bytes are not required to be copied into the Canvas document.

## Provider contract

0.1 requires a provider boundary conceptually equivalent to:

```text
resolve(GroundRef) -> Resolution
```

A Resolution MAY include display bytes/content metadata, existence, version, digest, provenance, or other provider-defined facts. Canvas core MUST NOT treat optional provider facts as authority unless the provider declares their semantics.

## 0.1 acceptance witnesses

### Grounded Field

A standalone implementation can create a Canvas, place a grounded local Object and note, connect them, move/group them neutrally, save/reload them, and explain the note's grounding path without mutating the referenced resource.

### Repository field

A conforming Git projector can pin an exact commit, enumerate the complete tracked Git tree, emit one grounded `reference` Object for each represented Git tree/blob, emit only real `contains` relations, validate the portable grammar, resolve every GroundRef to the exact Git digest, and reproduce the same semantic projection from the same revision.

The primary source witness is Canvas projecting **its own repository** first.

### First Board

The first real Board proves that:

1. its stored premise is `What exists here, and how is it contained?`;
2. it is composed from the repository field without creating new repository Objects or Connections;
3. it preserves every original Object ID, GroundRef, and `contains` Connection;
4. represented Objects appear through ordinary Cards;
5. stored `contains` Connections appear as visible geometry between those Cards;
6. hierarchical arrangement is derived from relation topology but does not become semantic authority;
7. text and HTML Cards still resolve exact pinned Git bytes;
8. selection/search/focus/zoom/pan are presentation-only;
9. the same field deterministically produces the same Board document;
10. no directory-specific primitive is needed.

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
- creating semantic Card classes merely to support visual rendering;
- creating a primitive/class for each future Board metaphor before common composition fails.
