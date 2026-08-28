# Canvas 0.1 Witness

This witness proves the standalone Grounded Field contract without Soveraeign or third-party Python packages.

From the repository root:

```bash
python -m unittest -v tests.test_canvas01
python canvas01.py validate fixtures/grounded-field.canvas.json
python canvas01.py ground-path fixtures/grounded-field.canvas.json object-note --root .
python canvas01.py inspect fixtures/grounded-field.canvas.json
```

Expected facts:

- all tests pass;
- the fixture validates against `schema/canvas-0.1.schema.json` and the semantic invariants;
- `object-note` reaches `object-source` through `connection-note-source`;
- `ground_distance` for `object-note` is `1`;
- the terminal `GroundRef` resolves through the standalone `local-file` provider to `fixtures/example.txt`;
- moving objects does not change GroundRefs or Connections;
- changing frame membership does not change grounding semantics;
- save/reload round-trips without semantic loss;
- an ungrounded durable note is refused;
- a local-file GroundRef cannot escape the configured provider root.

## Mutation witness

To create a changed copy without mutating the source fixture:

```bash
python canvas01.py move \
  fixtures/grounded-field.canvas.json \
  object-source 200 220 260 160 \
  --output /tmp/moved.canvas.json

python canvas01.py frame-members \
  /tmp/moved.canvas.json \
  frame-working-set object-note \
  --output /tmp/regrouped.canvas.json

python canvas01.py validate /tmp/regrouped.canvas.json
```

The external `fixtures/example.txt` resource remains unchanged. Layout and grouping are Canvas presentation state only.
