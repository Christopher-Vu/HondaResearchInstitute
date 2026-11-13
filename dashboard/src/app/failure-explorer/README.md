# Honda Failure-Axis Explorer

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

Gap summaries are exploratory development results with the best axis chosen
using the key. The inventory below them contains all emitted axes and does not
select axes using a gap key. The recovery flag is copied from the method’s gap
summary: it can refer to another axis than the displayed best-overlap axis.
No score or research rule is recomputed in the dashboard.

## Emitted axis inventory

New `dev_eval.py` reports add an `axes` array to each method entry, including
excluded runs and methods that emitted no axes (`[]`). Each entry preserves the
existing `AxisCard.to_dict()` representation (name, description, rank, provenance,
supporting episodes, gate and causal metadata), plus `axis_size` and
`share_of_failures`. The latter is the number of associated failing rollouts
divided by the corpus failure count, or zero when there are no failures.
The exporter preserves directive order and adds no key-selected labels.

Select a method/run, search by axis ID, name or description, and expand a card
to inspect supporting episode IDs and timestep windows. A 0–0 window is a method
placeholder for some methods; it does not establish when a failure occurred.
Names and descriptions are emitted by the method, not verified causal explanations.
An absent causal verdict displays the schema's default, `untested`.

Older reports without `axes` still load and show their gap summaries. The view
explicitly distinguishes “inventory not exported” from “no axes emitted”. It
never reconstructs an inventory from best-gap matches. New inventories must
come from a separately authorized development evaluation; this change does not
regenerate committed research results or authorize compute work.

All rendered inventory fields are validated before display, including unique
axis/episode IDs, complete support counts, finite values and ordered timestep
windows. The inventory length must equal the reported emitted axis count.
Cross-report comparison remains a separate task.

## Data provenance

JSON files are curated, display-only extracts of the public H18/H19/H20 research results in `docs/research/data/` from the GitHub repository as of 2026-11-09. Jaccard values are rounded to six decimal places; H19 contains the P19 sweep and planted-group summary only. Consult the original research files for full precision and metadata. No sealed data is included.

## Validation

From `dashboard/`, run:

```sh
pnpm install --frozen-lockfile
pnpm run check  # Node 22.18+ for native TypeScript tests
pnpm run build
```

`build` uses Next's supported Webpack backend. This keeps the production check
independent of Turbopack's local process-port requirement; use `next build`
directly when specifically testing Turbopack.

The parser tests use the committed H12 report as a producer-format regression
fixture and a Python-produced synthetic inventory fixture. They cover malformed
fields, excluded runs, null axes, empty reports and incomplete inventories.
`tests/test_dev_eval.py` checks that exporting the inventory leaves every prior
score, bootstrap interval and verdict unchanged on a synthetic corpus, and that
the dashboard fixture still matches the Python exporter.

## Research limitations

- All displayed results are dev-only, not final validation.
- H18 and H20 use different rollout pools.
- The 'best' Jaccard is selected with knowledge of the key.
- H19 reports the settings sweep and planted-failure recovery separately from H18/H20 dictionary medians.
