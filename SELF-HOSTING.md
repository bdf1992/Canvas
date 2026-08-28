# Self-hosting priority

Canvas should prove itself against the smallest real environment that contains its own implementation before it is used to visualize a larger external system.

The first repository board is therefore **this Canvas repository itself**.

## Order of evidence

1. **Canvas -> Canvas** — project the exact Canvas Git revision currently under test into the unchanged Canvas 0.1 grammar and publish that board.
2. **Other Git repositories -> Canvas** — use the same projector unchanged against larger repositories as scale/conformance witnesses.
3. **Additional providers -> Canvas** — add new projectors only when the source has real topology that cannot already be expressed by the existing portable grammar.

A larger repository such as Soveraeign is useful as a later scale witness, but it is not the first product demonstration and must not define the Canvas object model.

## Self-hosting acceptance

For an exact Canvas commit, CI must:

- enumerate the complete tracked Git tree at that commit;
- project every real tree/blob as an ordinary `reference` Object;
- project only Git parent/child membership as `contains` Connections;
- validate the generated document against the unchanged Canvas 0.1 contract;
- resolve every generated GroundRef to its exact Git object;
- regenerate the same commit byte-for-byte;
- render and publish `canvas.canvas.json` and `canvas-board.html` as the primary repository-board artifact.

The board is a projection of the repository; it is not a second repository and has no authority over Git.