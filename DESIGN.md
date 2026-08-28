# Canvas Interaction Design System

Status: executable design contract

Canvas interaction is governed by the same architectural principle as Canvas data: the interface should reveal addressed things and explicit relations without manufacturing a second hidden system.

## Spatial nouns

- **Canvas** is the open field. It has no meaningful page edge.
- **Card** is a bounded visual rendering of an addressed Object/Resolution.
- **Board** is an authored, premise-bearing view over things on the Canvas. A raw repository projection is not a Board merely because it is spatial.

## Interaction invariants

1. **Content before chrome** — rendered objects are the primary surface. Toolbars, inspectors, labels, and controls are subordinate.
2. **Readable before complete** — the default view MUST NOT shrink the whole field until Cards are illegible merely to show everything at once. Focus is preferred to fit-all.
3. **One spatial gesture model** — wheel/trackpad changes depth (zoom around the pointer); dragging empty field space changes position (pan). The Canvas itself does not scroll vertically or horizontally.
4. **Context is contextual** — metadata/inspection UI appears when an Object is selected and can be dismissed. It MUST NOT permanently consume field area when nothing is selected.
5. **Search navigates** — finding an Object should select/focus it rather than hide unrelated Objects and silently rewrite the visible topology.
6. **Rendering is not authority** — an HTML Card may visually render HTML, but active content is sandboxed. A Card never becomes a hidden runtime merely because its bytes are executable.
7. **Renderer choice is presentation** — text, HTML, image, structured-data, or binary rendering strategies MUST NOT create new semantic Object kinds.
8. **No duplicate controls without evidence** — if a spatial gesture already performs an operation, persistent buttons for the same operation require a demonstrated accessibility or usability need.
9. **Focus has a home** — every field provides a deterministic, readable home/focus state and a simple way to return to it.
10. **The field stays inspectable** — selecting or focusing an Object never mutates the stored Canvas document or provider state.

## Default interaction grammar

```text
wheel / trackpad       zoom at pointer
empty-space drag       pan field
single Card click      select + reveal contextual metadata
double Card click      focus Card
Enter on Card           focus Card
/                       focus Find
Enter in Find           select + focus first match
Escape                  dismiss transient context
0 / Home                return to deterministic home
```

## QA predicates

A desktop self-field is considered interaction-conformant when:

- document/body scrolling remains zero while zooming the Canvas;
- the Canvas viewport occupies the full application surface rather than sharing permanent space with an inspector;
- the initial home scale is at least `0.55` unless a Card renderer explicitly declares a different readable threshold;
- the default UI does not expose separate zoom-in/zoom-out/fit-all/reset controls;
- no metadata panel is visible before selection;
- selecting a Card reveals metadata without changing Canvas JSON;
- search focuses a matching Card without hiding the rest of the topology;
- HTML Cards remain sandboxed with no script/network/form authority;
- Card bodies are generated from exact pinned provider bytes.

## Design test

Before adding a persistent control or semantic visual state, ask:

> What inability in the field/card/connection grammar requires this element to exist?

If the answer is only convenience, styling, or a duplicate route to an existing spatial operation, prefer removing it until executable evidence justifies it.
