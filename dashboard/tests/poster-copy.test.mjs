import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const dashboard = new URL("../", import.meta.url);

test("poster copy labels the study stages and does not claim unmeasured retraining", async () => {
  const [poster, figures] = await Promise.all([
    readFile(new URL("src/components/poster/Poster.tsx", dashboard), "utf8"),
    readFile(new URL("src/components/poster/Figures.tsx", dashboard), "utf8"),
  ]);

  for (const label of ["1. The problem", "2. What the method does", "3. Evidence from a planted control", "4. Controls and decoys"]) {
    assert.ok(poster.includes(label), `missing poster section label: ${label}`);
  }
  assert.match(poster, /development control, not a final result/);
  assert.match(figures, /fresh routes against simple baselines/);
  assert.doesNotMatch(figures, /generate those scenarios and retrain/);
});
