# Canvas 0.1 Contract — Grounded Field

Status: execution staging

## Definition

Canvas is a shared spatial binding for addressable things. It gives humans and agents one visible grammar for placing, relating, annotating, grouping, and inspecting durable objects without turning presentation into authority.

Canvas 0.1 does not define workflow execution, domain state transitions, or provider authority. It defines the smallest durable field on which those later capabilities can be composed explicitly.

## Core objects

### Canvas

A durable composition document containing boards, objects, frames, and connections.

Required properties:

- `canvas_id`
- `schema_version`
- `boards`
- `objects`
- `frames`
- `connections`

### Board

A spatial view or bounded arrangement within a Canvas.

A Board owns presentation placement, not semantic state.

### Object

A durable addressable thing placed on a Board.

An Object may be:

- a reference to provider-backed ground;
- a Canvas-native note or annotation;
- a mock or derived object whose meaning remains grounded through explicit connections.

### Frame

A neutral visual grouping primitive.

Membership in a Frame MUST NOT imply provider/domain state.

### Connection

A visible, durable relation between addressable endpoints.

0.1 keeps the relation model intentionally small:

- `connection_id`
- `from`
- `to`
- `kind`
- optional `direction`

Typed measures, scoring, and richer relation vocabularies belong to 0.2.

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

Providers own the semantics of resolution, version, digest, authority, custody, provenance, and availability.

## Invariants

1. **Standalone coherence** — Canvas core MUST function without Soveraeign or any other specific provider.
2. **Addressable durability** — anything preserved as meaningful Canvas state MUST have durable identity.
3. **Grounding closure** — every durable derived/annotation object MUST have at least one explicit traversable path to provider-backed ground, unless the object itself directly carries a `GroundRef`.
4. **No hidden inference** — Canvas MUST be able to explain the stored path by which an object is grounded. It MUST NOT invent unstored semantic relations to satisfy grounding.
5. **Grouping neutrality** — frames, columns, coordinates, color, proximity, and layout MUST NOT change provider/domain state.
6. **Presentation is not authority** — labels, badges, visual emphasis, or placement MUST NOT create approval, completion, ratification, authorization, custody, or standing.
7. **Reference, not ownership** — deleting a Canvas or Object MUST NOT imply deletion of referenced provider resources.
8. **Visible relation** — durable semantic connection MUST exist as explicit Connection data rather than being inferred from geometry.
9. **Provider isolation** — provider-specific concepts MUST NOT become required fields in the portable core schema.
10. **Human/agent grammar parity** — an agent-created durable object or connection MUST be inspectable through the same data grammar as a human-created one.

## Grounding

A Canvas object is grounded when either:

- it directly contains one or more valid `GroundRef`s; or
- following stored Connections reaches an Object with a valid `GroundRef`.

`ground_distance` is a derived value equal to the minimum number of Connection hops required to reach provider-backed ground.

Typical examples:

```text
provider-backed object       distance 0
note -> provider object      distance 1
summary -> note -> provider  distance 2
```

Grounding does not mean truth, authority, approval, or correctness. It means the durable object's meaning is not epistemically floating: the system can show what addressed thing(s) it ultimately points toward.

## Persistence

0.1 persistence MUST round-trip without semantic loss:

```text
create -> save -> close -> reload
```

At minimum, identity, placement, frame membership, connections, and GroundRefs MUST survive the round trip.

## Provider contract

0.1 requires only a minimal provider boundary conceptually equivalent to:

```text
resolve(GroundRef) -> Resolution
```

A Resolution MAY include display bytes/content metadata, existence, version, digest, provenance, or other provider-defined facts. Canvas core MUST NOT treat optional provider facts as authority unless the provider explicitly declares their semantics.

A local/file provider is sufficient for standalone 0.1 acceptance.

## 0.1 acceptance witness

A conforming standalone implementation can, with no Soveraeign installation:

1. create a Canvas and Board;
2. place a local/file-backed object;
3. create a durable note;
4. connect the note to the file-backed object;
5. move and resize the objects;
6. place them in a neutral Frame;
7. save the Canvas;
8. reload it;
9. show that the note's grounding path reaches the file-backed GroundRef;
10. demonstrate that changing layout or frame membership does not mutate the referenced resource.

## Explicit non-goals for 0.1

- generalized whiteboard drawing;
- multiplayer cursors;
- workflow orchestration;
- executable circuits;
- hidden semantic inference;
- graph database requirements;
- universal scoring;
- provider-specific authority logic;
- Soveraeign dependency.

Those may arrive through later contracts where justified by executable evidence.
