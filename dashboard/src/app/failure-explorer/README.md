# Honda Failure-Axis Explorer — Experiment Comparison

## Development report importer

Open `/failure-explorer` and select a JSON report produced by
`src/discovery/dev_eval.py`, for example `docs/research/data/h12_layer10_plain.json`.
Processing stays in the browser. Select a method/run to inspect its best axis per
gap, overlap, support and recovery flag. Excluded runs remain visible and are
labelled; their scores do not count toward the evaluation rule.

The supported format has `layer`, `corpus` and a `methods` map. All fields used
by the view are validated before rendering, with a field path in errors.
The obsolete `runs`/`contrastive_axes` format and experiment-specific aggregate
files such as H18/H20 are not supported by this importer. Those experiments have
their own comparison view. Reports with no methods or no gap summaries show an
empty state; a null axis is displayed as “No axis”.

These are exploratory development summaries with axes chosen using the key,
not full axis inventories. The recovery flag is copied from the method’s gap
summary: it can refer to another axis than the displayed best-overlap axis.
No score or research rule is recomputed in the dashboard.

## Data provenance

JSON files are curated, display-only extracts of the public H18/H19/H20 research results in `docs/research/data/` from the GitHub repository as of 2026-11-09. Jaccard values are rounded to six decimal places; H19 contains the P19 sweep and planted-group summary only. Consult the original research files for full precision and metadata. No sealed data is included.

## Validation

From `dashboard/`, run:

```sh
node --test tests/evaluation-report.test.mjs  # Node 22.18+ for native TypeScript
npx next typegen
npx tsc --noEmit
npx eslint src/app/failure-explorer/AxisImporter.tsx src/app/failure-explorer/evaluation-report.ts tests/evaluation-report.test.mjs
npm run build
```

The parser tests use the committed H12 report as a producer-format regression
fixture and cover malformed fields, excluded runs, null axes and empty reports.

## Research limitations

- All displayed results are dev-only, not final validation.
- H18 and H20 use different rollout pools.
- The 'best' Jaccard is selected with knowledge of the key.
- H19 reports the settings sweep and planted-failure recovery separately from H18/H20 dictionary medians.
