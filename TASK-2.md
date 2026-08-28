# Task 2 — Self-hosted view mechanics

Status: completed / superseded by Directory Board

This task established the reusable view mechanics over the grounded Canvas repository projection: infinite zoom/pan, search/focus, transient selection, and collapse state without mutating source semantics.

Its original mistake was calling the raw repository projection itself a Board. That distinction is now corrected.

## What remains true

The source chain is still:

```text
Git objects + Git tree membership
        ↓
Canvas reference Objects + contains Connections
        ↓
renderer-local interaction state
```

Renderer-local state such as selection, zoom, pan, collapsed directories, search, and focus is presentation-only and is not persisted as provider/domain meaning.

## What changed

The raw repository projection is now called the **repository field**.

The first real Board is **Directory Board**, whose explicit premise is:

> What exists here, and how is it contained?

Directory Board reuses the same grounded Objects and `contains` Connections, renders one bounded Board frame, and represents entries as directory/file rows with visible connection geometry. It does not use Cards.

## Preserved refusals

- no `RepoNode`, `FileCard`, `DirectoryCard`, or other repository-specific semantic Object type;
- no write-back to Git;
- no hidden relationship inference;
- no issue/PR/workflow overlays yet;
- no new source Objects merely to represent UI controls;
- no Soveraeign dependency;
- no Circuit semantics.

The current acceptance surface is defined by `FIRST-BOARD.md`, `DESIGN.md`, and `directory_board.py`.
