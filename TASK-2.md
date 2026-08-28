# Task 2 — Make the self-board usable

Status: active

The first repository board is the Canvas repository itself. This task improves only the **view mechanics** over that already-grounded projection.

## Constraint

Do not create new semantic Canvas object classes or provider state to make the board easier to use.

The source remains:

```text
Git objects + Git tree membership
        ↓
Canvas reference Objects + contains Connections
        ↓
renderer-local interaction state
```

Renderer-local state such as selection, zoom, pan, collapsed directories, filtering, and focus is presentation-only and is not persisted as domain meaning.

## Acceptance

The generated `canvas-board.html` must let a human:

1. see the entire Canvas repository as one board;
2. distinguish trees from blobs;
3. search/filter by path;
4. select a repository object and inspect its exact path, Git object type, digest, and pinned revision;
5. see its parent/child context from existing `contains` Connections;
6. collapse/expand directory subtrees without changing the Canvas document;
7. zoom and pan around the board;
8. reset to the complete repository view;
9. navigate these controls without creating or mutating any source object;
10. regenerate the same semantic Canvas JSON for the same commit regardless of renderer interaction.

## Refusals

- no `RepoNode`, `FileCard`, `DirectoryCard`, or other repository-specific Canvas schema type;
- no write-back to Git;
- no hidden relationship inference;
- no issue/PR/workflow overlays yet;
- no new Canvas objects merely to represent UI controls;
- no SOV dependency;
- no Circuit semantics.

The board is an interface over the existing repository, not a second repository model.
