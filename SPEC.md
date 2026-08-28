# Canvas 0.1 Contract — Grounded Field

Status: executable baseline

## Definition

Canvas is a shared spatial binding for addressable things. It gives humans and agents one visible grammar for placing, relating, annotating, grouping, rendering, and inspecting durable objects without turning presentation into authority.

Canvas 0.1 does not define workflow execution, domain state transitions, or provider authority. It defines the smallest durable field on which those later capabilities can be composed explicitly.

## Spatial distinctions

### Canvas

Canvas is the spatial field itself: open placement space plus durable objects, frames, connections, and grounding references.

### Board

A Board is a premise-bearing authored view over a Canvas. A roadmap Board, architecture Board, release-readiness Board, or discussion Board exists because an actor selected a question/premise and composed objects to answer it.

A raw provider projection is **not automatically a Board**. The complete repository projection is a repository Canvas field/module map that can later participate in many different Boards.

The 0.1 JSON schema predates this distinction and uses `boards`/`board_id` as its placement-surface field. That name is retained for compatibility in 0.1. It MUST NOT be interpreted as proof that every placement surface has Board semantics. Premise-bearing Board semantics should only widen the durable contract when a real authored Board requires them.

### Object

A durable addressable thing placed on the Canvas field. An Object may reference provider-backed ground or be a Canvas-native note/annotation/mock/derived object whose meaning remains grounded through explicit Connections.

### Card

A Card is **not a durable object kind**. It is a bounded visual rendering of an Object/Resolution on the Canvas.

```text
Object + GroundRef
      -> provider resolves exact thing/bytes
      -> renderer chooses a visual body
      -> Card appears on Canvas
```

A renderer MAY choose text, HTML, image, structured-data, binary, or other visual strategies. Those strategies MUST NOT create `TextCard`, `HtmlCard`, `FileCard`, or equivalent semantic object families merely for presentation.

For provider-backed content, Card rendering SHOULD use the exact resolved revision/digest represented by the GroundRef rather than mutable working-tree state.

### Frame

A neutral visual grouping primitive. Membership in a Frame MUST NOT imply provider/domain state.

### Connection

A visible, durable relation between addressable endpoints. 0.1 keeps the relation model intentionally small: `connection_id`, `from`, `to`, `kind`, and optional `direction`.

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

## Generalization by projection and rendering

```text
Provider  -> resolves addressed source objects and optional bytes
Projector -> deterministically maps source objects/relations into Canvas primitives
Renderer  -> presents resolved Objects as Cards on the Canvas
```

Projectors and renderers are implementation behavior, not new durable schema objects.

A valid projector:

1. emits only the portable Canvas grammar unless a later contract explicitly widens it;
2. grounds projected Objects in exact provider references;
3. emits a Connection only when the source supports that relation or the user explicitly creates it;
4. keeps layout/grouping semantically neutral;
5. pins enough source revision information for reproduction;
6. does not write back merely because presentation changes.

A valid renderer:

1. does not mutate the semantic Canvas document merely by rendering it;
2. derives visible content from the addressed Object/Resolution;
3. preserves the distinction between visual fidelity and authority;
4. contains active/untrusted content so rendering cannot silently execute repository behavior;
5. may truncate or simplify a preview while clearly remaining a representation of the same addressed thing.

Git is the first provider/projector witness. Git trees/blobs remain Git objects; each is projected as a grounded `reference` Object and tree membership becomes `contains`.

## Baseline Card renderers

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
6. **Presentation is not authority** — Card rendering, labels, badges, visual emphasis, or placement MUST NOT create approval, completion, ratification, authorization, custody, or standing.
7. **Reference, not ownership** — deleting a Canvas/Object MUST NOT imply deletion of referenced provider resources.
8. **Visible relation** — durable semantic connection MUST exist as explicit Connection data rather than inferred geometry.
9. **Provider isolation** — provider-specific concepts MUST NOT become required portable-core fields.
10. **Human/agent grammar parity** — agent-created durable objects/connections MUST be inspectable through the same grammar as human-created ones.
11. **Projection fidelity** — a projector MUST NOT manufacture source relations for convenience.
12. **Revision closure** — when exact revisions exist, durable source projections MUST identify the exact revision used.
13. **Render fidelity** — a provider-backed Card MUST represent the addressed thing/revision, not silently substitute mutable nearby state.
14. **Active-content containment** — rendering addressed active content MUST NOT silently grant it execution authority in the Canvas host.

## Grounding

A Canvas Object is grounded when it directly contains valid GroundRefs or following stored Connections reaches an Object with valid GroundRefs. `ground_distance` is the derived minimum Connection-hop count to provider-backed ground.

Grounding does not mean truth, authority, approval, or correctness. It means the durable object's meaning is not epistemically floating.

## Persistence

0.1 persistence MUST round-trip identity, placement, frame membership, connections, and GroundRefs without semantic loss. Rendered provider bytes are not required to be copied into the Canvas document.

## Provider contract

0.1 requires a provider boundary conceptually equivalent to:

```text
resolve(GroundRef) -> Resolution
```

A Resolution MAY include display bytes/content metadata, existence, version, digest, provenance, or other provider-defined facts. Canvas core MUST NOT treat optional provider facts as authority unless the provider declares their semantics.

## 0.1 acceptance witnesses

### Grounded Field

A standalone implementation can create a Canvas, place a grounded local object and note, connect them, move/group them neutrally, save/reload them, and explain the note's grounding path without mutating the referenced resource.

### Repository Canvas field

A conforming Git projector can pin an exact commit, enumerate the complete tracked Git tree, emit one grounded `reference` Object for each represented Git tree/blob, emit only real `contains` relations, validate the unchanged semantic grammar, resolve every GroundRef to the exact Git digest, and reproduce the same semantic projection from the same revision.

The primary witness is Canvas projecting **its own repository** first.

### Card rendering

The self-hosted repository Canvas field additionally proves that:

1. exact Git blob bytes can be resolved independently of dirty working-tree state;
2. UTF-8 text is visibly rendered inside its Card;
3. HTML is visibly rendered inside a sandboxed Card;
4. active HTML cannot execute as part of the Canvas host;
5. renderer choice does not create new durable Object kinds;
6. render operations do not mutate the semantic Canvas document.

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
- treating every provider projection as a Board;
- creating semantic card classes merely to support visual rendering.
