# First Board — Directory Board

The first real product Board is a **Directory Board over the Canvas repository itself**.

The raw Git repository projection is source field material, not a Board. It contains the exact grounded repository Objects and explicit `contains` Connections. A Board begins when that field is given an explicit premise.

## Premise

> **What exists here, and how is it contained?**

That makes Directory Board the smallest useful first Board because Git already supplies exact evidence for the premise: trees, blobs, and tree membership.

## Derivation

```text
Canvas Git repository @ exact commit
        ↓
repository field
  grounded reference Objects
  contains Connections
        ↓
Directory Board
  same Objects
  same GroundRefs
  same Connections
  explicit premise
  deterministic directory arrangement
```

The Board creates no repository-specific Object class and duplicates no source Object or Connection.

## Representation

Directory Board uses directory/file rows and visible branch lines. It does **not** use Cards because reading file contents is not required to answer the directory premise.

Card rendering remains available for later Boards whose premises require content inspection.

## Why Canvas first

Canvas should prove its Board semantics against its own small repository before using a larger external system. Soveraeign remains a later scale/reference witness using the same projection and Board principles.
