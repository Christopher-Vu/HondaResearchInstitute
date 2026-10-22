import gapPilots from "@/data/gap-pilots.json";
import layerSweep from "@/data/layer-sweep.json";

// Every measured number on the poster. Sources:
// P4 paired outcomes: results/savio/step5-pilot-p4-main/efficacy.json (c23_paired, prd_9_1)
// Control-gap overlap: results/savio/dev-eval/p4.json (layer 10, k=32 run; all methods tie)
// Layer sweep and pilots: src/data/layer-sweep.json, src/data/gap-pilots.json

function pilot(id: string) {
  const found = gapPilots.gaps.find((gap) => gap.id === id);
  if (!found) throw new Error(`gap pilot ${id} missing from gap-pilots.json`);
  return found;
}

const p4 = pilot("P4");

export const occlusion = {
  blocked: p4.with,
  clear: p4.without,
  ratio: p4.with.failed / p4.without.failed,
  pairs: 60,
  blockedOnly: 31,
  clearOnly: 0,
  // McNemar's test on the 60 pairs, which is the test that matches the paired 31-to-0 count.
  pairedP: "9\u00a0×\u00a010",
  pairedExponent: "−10",
};

export const appearanceGaps = {
  fog: pilot("P3"),
  animals: pilot("P6"),
};

// Step 2 reproductions on Bench2Drive (docs/STATUS.md): Chris 88.34 over 219 routes, Jerry 88.60 over 220.
export const reproduction = { scores: ["88.3", "88.6"], routes: 220 };

export const layers = {
  routes: layerSweep.routes,
  failing: layerSweep.failing,
  chosen: layerSweep.logged_layer,
  scores: layerSweep.layers.map(({ layer, failure_auroc }) => ({ layer, auroc: failure_auroc })),
};

export const controlCheck = {
  developmentFailures: 73,
  plantedFailures: 51,
  overlap: 51 / 73,
  methods: [
    { name: "Our contrastive axes", overlap: 0.699, ours: true },
    { name: "Human failure taxonomy", overlap: 0.699, ours: false },
    { name: "Random axes", overlap: 0.699, ours: false },
  ],
};
