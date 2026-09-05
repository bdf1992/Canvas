# First Board — Repository containment

The first real product Board is a **premise-bearing Board over the Canvas repository itself**.

The raw Git repository projection is source field material, not a Board. It contains exact grounded repository Objects and explicit `contains` Connections. A Board begins when those existing things are deliberately composed around a premise.

## Premise

> **What exists here, and how is it contained?**

We may call this a **Directory Board** conversationally because that is the familiar reading of the premise, but `directory` is not a Canvas primitive, Object kind, renderer, or special Board class.

## Composition

```text
Canvas Git repository @ exact commit
        ↓
repository field
  grounded Objects
  contains Connections
        ↓
generic Board
  explicit premise
  generic Frame
  Cards rendering the same Objects
  visible contains Connections
  hierarchical arrangement derived from those Connections
```

The Board creates no repository-specific Object class and duplicates no source Object or Connection. The directory-like meaning emerges from the Cards, their arrangement, and the stored `contains` relations.

## Representation

Every represented repository Object appears through the ordinary Card rendering capability. A tree-backed Object can render as a compact structural Card; text and HTML Objects can use their existing exact-byte renderers. The visible lines between Cards are the stored `contains` Connections.

The first Board therefore proves the reusable grammar we want future Boards to share:

```text
Board premise
+ Cards
+ Connections
+ Frame/layout
```

A roadmap Board, architecture Board, evidence Board, or discussion Board should vary those ingredients rather than introduce a new primitive for each metaphor.

## Why Canvas first

Canvas should prove this Board grammar against its own small repository before using a larger external system. Soveraeign remains a later scale/reference witness using the same projection and Board principles.
