# Task 2 — Self-hosted view mechanics

Status: completed / superseded by generic Board composition

This task established reusable view mechanics over the grounded Canvas repository projection: infinite zoom/pan, search/focus, and transient selection without mutating source semantics.

Its original mistake was calling the raw repository projection itself a Board. A later mistake overcorrected by creating a literal directory-tree primitive. Both are now superseded.

## What remains true

```text
Git Objects + Git tree membership
        ↓
Canvas reference Objects + contains Connections
        ↓
Board composition + renderer-local interaction state
```

Selection, zoom, pan, search, focus, and relation highlighting are presentation-only and are not persisted as provider/domain meaning.

## Current first Board

The repository field is composed into a generic premise-bearing Board:

> What exists here, and how is it contained?

The Board reuses the same grounded Objects and `contains` Connections, renders those Objects through ordinary Cards, draws the Connections between those Cards, and derives hierarchical arrangement from those Relations.

Calling the result a “Directory Board” describes the human reading of the composition. It does not introduce `DirectoryBoard`, directory rows, directory nodes, or other directory-specific Canvas primitives.

## Preserved refusals

- no `RepoNode`, `FileCard`, `DirectoryCard`, `DirectoryBoard`, or other repository-specific semantic type;
- no write-back to Git;
- no hidden relationship inference;
- no issue/PR/workflow overlays yet;
- no new source Objects merely to represent UI controls;
- no Soveraeign dependency;
- no Circuit semantics.

The current acceptance surface is defined by `FIRST-BOARD.md`, `../../DESIGN.md`, and `../../board_view.py`.
