# Canvas Interaction Design System

Status: executable design contract

Canvas interaction is governed by the same architectural principle as Canvas data: the interface should reveal addressed things and explicit relations without manufacturing a second hidden system.

## Spatial nouns

- **Canvas** is the open field. It has no meaningful page edge.
- **Board** is a bounded, authored view with an explicit premise. Without a premise, a placement surface is not a Board.
- **Frame** is neutral visual grouping inside a Board or Canvas. A Frame does not create a premise or semantic state.
- **Card** is one optional bounded visual rendering of an addressed Object/Resolution. Cards are useful when the premise is about the content of individual things; they are not the default representation for every Board.
- **Connection** is explicit stored relation data. When a Board premise is relational, Connections should become primary visible geometry rather than decorative lines behind Cards.

The schema permits an optional `Board.premise` so historical placement surfaces remain readable. In the design contract, only a surface with an explicit premise is treated as a Board.

## First Board: Directory Board

The first real Board answers one question:

> **What exists here, and how is it contained?**

It is derived from the repository field without creating duplicate Objects or Connections.

```text
repository field
  -> same grounded Objects
  -> same contains Connections
  -> Directory Board premise + directory arrangement
  -> directory-tree rendering
```

The Directory Board MUST:

1. render one bounded Board frame on the Canvas;
2. present repository Objects as directory/file rows, not Cards;
3. use hierarchy/indentation to express directory structure;
4. visibly draw each stored `contains` Connection between its endpoints;
5. allow directory collapse/expand as transient view state;
6. keep exact GroundRefs inspectable without turning digest metadata into the primary visual;
7. create no new semantic Objects merely to make the directory view work.

Card rendering remains a Canvas capability for later Boards whose premise calls for content rendering.

## Interaction invariants

1. **Premise before component** — choose the representation that answers the Board premise. Do not default to Cards because Cards exist.
2. **Content before chrome** — Board content and Connections are the primary surface. Toolbars, inspectors, labels, and controls are subordinate.
3. **Readable before complete** — the default view MUST NOT shrink meaningful content until it is illegible merely to show everything at once.
4. **One spatial gesture model** — wheel/trackpad changes depth (zoom around the pointer); dragging empty Canvas space changes position (pan). The Canvas itself does not scroll vertically or horizontally.
5. **Context is contextual** — metadata appears only when it helps answer the current premise. It MUST NOT permanently consume field area without need.
6. **Search navigates** — finding an Object should focus it rather than silently rewrite or filter away the topology.
7. **Rendering is not authority** — visual representation never creates approval, completion, custody, ratification, authorization, or standing.
8. **Renderer choice is presentation** — directory rows, text Cards, HTML Cards, image Cards, and future renderers MUST NOT create source-domain Object kinds.
9. **Connections are data** — visible relation geometry MUST correspond to stored Connection data; geometry alone never invents a relation.
10. **No duplicate controls without evidence** — if a spatial or native gesture already performs an operation, persistent duplicate controls require a demonstrated need.
11. **Focus has a home** — every Board provides a deterministic readable home state and a simple way to return to it.
12. **Presentation does not mutate ground** — selection, collapse, focus, search, pan, zoom, and Board rendering do not mutate provider state or source GroundRefs.

## Directory Board interaction grammar

```text
wheel / trackpad       zoom at pointer
empty-space drag       pan Canvas
single row click        select endpoint / highlight relation context
directory disclosure   collapse / expand descendants
double row click        focus row; directory also toggles
/                       focus Find
Enter in Find           focus first matching path
Escape                  clear transient selection/search context
0 / Home                return to deterministic Board home
```

## QA predicates

A self-hosted Directory Board is interaction-conformant when:

- there is exactly one visible premise-bearing Board frame;
- repository Objects are rendered as directory/file rows rather than `.card` surfaces;
- every visible parent/child relation is backed by a stored `contains` Connection;
- collapsing a directory hides descendants and their Connection geometry without changing Canvas JSON;
- document/body scrolling remains zero while zooming the Canvas;
- the Board remains readable at its deterministic Home scale;
- search focuses a matching path without deleting unrelated topology;
- no file-content iframe/text preview is rendered merely because Card renderers exist;
- GroundRefs and source Objects are unchanged by Board derivation;
- the Directory Board derivation creates zero new Objects and zero new Connections.

## Card rendering remains available

Cards are still appropriate when a Board premise requires inspecting the content of individual addressed things. Text and sandboxed HTML remain baseline Card renderers, but they are capabilities rather than the default Canvas topology view.

Before adding a persistent control, renderer, or semantic visual state, ask:

> What inability in the current Board premise / Object / Connection grammar requires this element to exist?

If the element does not help answer the premise or expose real stored structure, prefer removing it until executable evidence justifies it.
