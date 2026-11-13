# Honda Failure-Axis Explorer — Experiment Comparison

## Install

Copy `ExperimentComparison.tsx`, `h18_result.json`, `h19_result.json`, and `h20_result.json` into:

`dashboard/src/app/failure-explorer/`

Then add to `dashboard/src/app/failure-explorer/page.tsx`:

```tsx
import ExperimentComparison from "./ExperimentComparison";
```

Within the page JSX, add `<ExperimentComparison />` above `<AxisImporter />`.

## Data provenance

JSON files are curated, display-only extracts of the public H18/H19/H20 research results in `docs/research/data/` from the GitHub repository as of 2026-11-09. Jaccard values are rounded to six decimal places; H19 contains the P19 sweep and planted-group summary only. Consult the original research files for full precision and metadata. No sealed data is included.

## Validation

Run `cd dashboard && npm run build` (or `pnpm build`) after copying. The build has not been run against the full repository in this environment.

## Research limitations

- All displayed results are dev-only, not final validation.
- H18 and H20 use different rollout pools.
- The 'best' Jaccard is selected with knowledge of the key.
- H19 reports the settings sweep and planted-failure recovery separately from H18/H20 dictionary medians.
