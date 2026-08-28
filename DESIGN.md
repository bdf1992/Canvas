# Canvas Interaction Design System

Status: executable design contract

Canvas interaction is governed by the same architectural principle as Canvas data: reveal addressed things and explicit relations without manufacturing a second hidden system.

## Spatial nouns

- **Canvas** is the open field. It has no meaningful page edge.
- **Board** is a bounded authored composition with an explicit premise. Without a premise, a placement surface is not a semantic Board.
- **Frame** is neutral visual grouping/boundary inside a Board or Canvas. A Frame does not create the premise.
- **Card** is a bounded visual rendering of an addressed Object/Resolution. It is presentation, not a semantic Object family.
- **Connection** is explicit stored relation data between Objects. Boards may arrange Cards so Connections become the primary topology.

The schema permits an optional `Board.premise` so historical placement surfaces remain readable while real Boards are explicit.

## Board grammar

Do not create a source-metaphor primitive when the same result can be represented by the common Board grammar:

```text
Board premise
+ Cards rendering grounded Objects
+ explicit Connections
+ Frame/layout
```

The Board premise selects and organizes a reading of the existing field. The visual metaphor should emerge from those ingredients.

## First Board: repository containment

The first Board asks:

> **What exists here, and how is it contained?**

Humans may call the result a **Directory Board**, but `directory` is not a Canvas primitive or special renderer.

```text
repository field
  grounded Objects
  contains Connections
        ↓
generic Board
  premise
  Cards rendering those Objects
  visible contains Connections
  hierarchical arrangement derived from those Connections
```

The first Board MUST:

1. render one bounded Board Frame on the infinite Canvas;
2. render represented Objects through the ordinary Card capability;
3. visibly draw stored `contains` Connections between those Cards;
4. derive hierarchy/layout from those Connections without turning geometry into semantic state;
5. preserve exact GroundRefs and source identity;
6. create no new Object or Connection merely to make the directory-like reading work;
7. use the same Board machinery future roadmap/architecture/evidence Boards can use.

## Interaction invariants

1. **Premise before arrangement** — the Board premise explains why these Objects and Connections are composed together.
2. **Common grammar before special primitive** — prefer Board + Card + Connection + Frame over a new metaphor-specific component type.
3. **Content before chrome** — Cards and Connections are the primary surface; controls are subordinate.
4. **Readable before complete** — Home should preserve useful Card readability instead of shrinking everything into illegibility when possible.
5. **One spatial gesture model** — wheel/trackpad changes depth (zoom around pointer); dragging empty Canvas changes position (pan). The document itself does not scroll.
6. **Search navigates** — finding an Object focuses its Card rather than deleting unrelated topology.
7. **Rendering is not authority** — Card rendering never creates approval, completion, custody, ratification, authorization, or standing.
8. **Renderer choice is presentation** — text, HTML, image, structural, or binary Card renderers MUST NOT create new semantic Object kinds.
9. **Connections are data** — visible relation geometry MUST correspond to stored Connection records; proximity alone never invents a relation.
10. **Context is contextual** — selection may highlight incident relations but does not create or mutate them.
11. **Focus has a home** — every Board has a deterministic home state.
12. **Presentation does not mutate ground** — layout, selection, focus, search, pan, zoom, and rendering do not mutate provider state or GroundRefs.

## Default Board interaction grammar

```text
wheel / trackpad       zoom at pointer
empty-space drag       pan Canvas
single Card click      select Card + incident Connections
double Card click      focus Card
Enter on Card           focus Card
/                       focus Find
Enter in Find           focus first matching Card
Escape                  clear transient selection
0 / Home                return to deterministic Board home
```

## QA predicates for the first Board

The self-hosted repository-containment Board is conformant when:

- exactly one premise-bearing Board Frame is visible;
- every represented repository Object is rendered as a `.card` surface;
- text and HTML Cards still render exact pinned Git bytes through the existing Card renderer contract;
- every visible hierarchy edge is backed by a stored `contains` Connection;
- selecting a Card visibly highlights incident Connection geometry;
- there is no `DirectoryBoard`, directory-row, tree-widget, or source-specific semantic primitive required for the representation;
- document/body scrolling remains zero while zooming the Canvas;
- search focuses a matching Card without deleting unrelated topology;
- Board derivation preserves Object IDs, GroundRefs, and Connections exactly;
- Board derivation may add premise/layout/Frame state but creates zero new Objects and zero new Connections.

## Design test

Before adding a persistent control, renderer, Board type, or semantic visual state, ask:

> What inability in Board / Card / Connection / Frame requires this element to exist?

If the same result can be expressed by composing those primitives, prefer composition over a new primitive.
