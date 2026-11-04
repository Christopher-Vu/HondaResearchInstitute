"""H17's edits, frame pairing and rule, on toy inputs: no policy, no GPU."""
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

import causal_replay as cr  # noqa: E402
from discovery.contrastive import ContrastiveConfig, Rollout, contrastive_directive  # noqa: E402

HIDDEN = 64


def toy_conditions(q=2):
    basis = cr.orthonormal_basis(torch.randn(q, HIDDEN, generator=torch.Generator().manual_seed(1)))
    control = cr.random_directions(1, HIDDEN, 2)[0]
    return basis, cr.Condition(cr.AXIS, cr.AXIS, basis), cr.Condition("random:0", cr.RANDOM, control)


def test_directions_are_unit_centred_and_fixed_by_the_seed():
    rows = cr.random_directions(5, HIDDEN, 3)
    assert torch.allclose(rows.norm(dim=1), torch.ones(5))
    assert rows.mean(dim=1).abs().max() < 1e-6
    assert torch.equal(rows, cr.random_directions(5, HIDDEN, 3))


def test_axis_removal_leaves_nothing_in_the_span_and_keeps_what_is_orthogonal_to_it():
    basis, axis, _ = toy_conditions()
    tokens = torch.randn(30, HIDDEN, generator=torch.Generator().manual_seed(4))
    edited = cr.edited_tokens(tokens, axis, basis)
    assert (edited @ basis.T).abs().max() < 1e-5
    orthogonal = tokens - cr.removed_part(tokens, basis)
    assert torch.allclose(edited, orthogonal, atol=1e-5)


def test_a_control_moves_each_token_exactly_as_far_as_the_axis_does():
    basis, axis, control = toy_conditions()
    tokens = torch.randn(30, HIDDEN, generator=torch.Generator().manual_seed(5))
    axis_edit = (tokens - cr.edited_tokens(tokens, axis, basis)).norm(dim=1)
    control_edit = (tokens - cr.edited_tokens(tokens, control, basis)).norm(dim=1)
    assert torch.allclose(axis_edit, control_edit, atol=1e-5)


def test_a_control_moves_the_frame_mean_at_least_as_far_as_the_axis_does():
    basis, axis, control = toy_conditions(q=4)
    tokens = torch.randn(30, HIDDEN, generator=torch.Generator().manual_seed(8))
    axis_mean = (tokens - cr.edited_tokens(tokens, axis, basis)).mean(dim=0).norm()
    control_mean = (tokens - cr.edited_tokens(tokens, control, basis)).mean(dim=0).norm()
    control_per_token = (tokens - cr.edited_tokens(tokens, control, basis)).norm(dim=1).mean()
    assert axis_mean < control_mean
    assert torch.isclose(control_mean, control_per_token, atol=1e-4)


class ToyLayer(torch.nn.Module):
    def forward(self, x):
        return x, "cache"


def test_the_hook_edits_only_the_driving_queries_and_keeps_dtype_and_tuple():
    basis, axis, _ = toy_conditions()
    layer = ToyLayer()
    edit = cr.DirectionEdit(layer, 30, basis)
    x = torch.randn(1, 40, HIDDEN, generator=torch.Generator().manual_seed(6)).to(torch.bfloat16)
    edit.condition = axis
    out, cache = layer(x)
    assert cache == "cache" and out.dtype == torch.bfloat16
    assert torch.equal(out[0, :10], x[0, :10])
    assert (out[0, -30:].float() @ basis.T).abs().max() < 0.05
    assert edit.realised_edit > 0 and edit.realised_frame_mean_edit > 0


def test_the_none_condition_is_untouched_and_still_reads_the_live_mean():
    basis, _, _ = toy_conditions()
    layer = ToyLayer()
    edit = cr.DirectionEdit(layer, 30, basis)
    x = torch.randn(1, 40, HIDDEN, generator=torch.Generator().manual_seed(7))
    out, _ = layer(x)
    assert out is x
    assert torch.allclose(edit.live_mean, x[0, -30:].mean(dim=0))
    assert edit.realised_edit == 0.0


def test_zero_really_zeroes():
    basis, _, _ = toy_conditions()
    tokens = torch.ones(30, HIDDEN)
    assert cr.edited_tokens(tokens, cr.Condition(cr.ZERO, cr.ZERO), basis).abs().max() == 0


def meta(route, base, role, success, gaps=("P4",)):
    return {"route_id": route, "base_id": base, "role": role, "success": success,
            "practice_gaps": list(gaps) if role == cr.SLICE_ROLE else []}


def test_pairs_keep_only_a_failing_slice_with_a_clean_twin():
    metas = [meta("a1", "a", cr.SLICE_ROLE, False), meta("a2", "a", cr.NEIGHBOURHOOD_ROLE, True),
             meta("b1", "b", cr.SLICE_ROLE, False), meta("b2", "b", cr.NEIGHBOURHOOD_ROLE, False),
             meta("c1", "c", cr.SLICE_ROLE, True), meta("c2", "c", cr.NEIGHBOURHOOD_ROLE, True),
             meta("d1", "d", cr.SLICE_ROLE, None), meta("d2", "d", cr.NEIGHBOURHOOD_ROLE, True),
             meta("e1", "e", cr.SLICE_ROLE, False, gaps=("P7",)), meta("e2", "e", cr.NEIGHBOURHOOD_ROLE, True)]
    assert [(a["route_id"], b["route_id"]) for a, b in cr.slice_only_pairs(metas, "P4")] == [("a1", "a2")]


def track(route, base, steps, xs, failure=None, captured=None, role=cr.SLICE_ROLE):
    steps = np.asarray(steps)
    xy = np.column_stack([np.asarray(xs, dtype=float), np.zeros(len(steps))])
    captured = steps[steps % 10 == 0] if captured is None else captured
    return cr.Track(meta(route, base, role, role != cr.SLICE_ROLE), steps, xy, np.zeros((len(steps), HIDDEN)),
                    failure, {int(step): f"{route}/{int(step):06d}.pt" for step in captured})


def test_the_failing_window_is_contrastive_s_and_only_frames_with_inputs_count():
    steps = np.arange(0, 200, 5)
    failing = track("f", "b", steps, steps, failure=100, captured=[50, 60, 70, 95])
    assert steps[cr.failing_rows(failing)].tolist() == [50, 60, 70, 95]


def test_a_twin_frame_is_the_nearest_position_within_the_radius():
    twin = track("t", "b", [0, 10, 20, 30], [0.0, 10.0, 20.0, 30.0], role=cr.NEIGHBOURHOOD_ROLE)
    near = cr.matched_rows(np.array([[9.0, 0.0], [11.0, 0.0], [100.0, 0.0], [np.nan, np.nan]]), twin)
    assert near == {1: 1.0}


def test_selection_keeps_each_pair_whole_drops_unmatched_pairs_and_marks_axis_members():
    steps = np.arange(0, 100, 10)
    good = (track("g1", "g", steps, steps, failure=60), track("g2", "g", steps, steps, role=cr.NEIGHBOURHOOD_ROLE))
    far = (track("h1", "h", steps, steps, failure=60),
           track("h2", "h", steps, steps + 500, role=cr.NEIGHBOURHOOD_ROLE))
    pairs, frames, means = cr.select_frames([good, far], {"g1"}, 0)
    assert [row["failing"] for row in pairs] == ["g1"] and pairs[0]["axis_member"]
    assert {frame["pair"] for frame in frames} == {0}
    assert {frame["arm"] for frame in frames} == {cr.FAILING_ARM, cr.CONTROL_ARM}
    assert len(means) == len(frames)


def test_the_rebuilt_axis_is_the_one_the_directive_names():
    rng = np.random.default_rng(0)
    steps = np.arange(0, 200, 5)

    def rollout(i, failed, plant):
        latents = rng.uniform(0, 0.05, size=(len(steps), 8))
        if plant:
            latents[(steps >= 100) & (steps < 150), 3] = 1.0
        return Rollout(f"r{i}", latents, steps, failed, 150 if failed else None)

    rollouts = [rollout(i, True, i < 30) for i in range(50)] + [rollout(100 + i, False, False) for i in range(60)]
    directive, _ = contrastive_directive(rollouts, ContrastiveConfig())
    axis, effects = cr.axis_from_rollouts(rollouts, directive.axes[0].axis_id)
    assert axis.members == directive.axes[0].rollouts and axis.founder == 3
    assert 3 not in cr.non_failure_latents(effects, 20, 0)


def test_a_rebuilt_axis_that_differs_from_the_stored_one_is_named():
    stored = {"axis_size": 3, "in_key": 2}
    assert cr.reproduction_errors(stored, {"a", "b", "c"}, {"a", "b"}) == []
    assert "axis_size" in cr.reproduction_errors(stored, {"a", "b"}, {"a", "b"})[0]


FAMILIES = [cr.NONE, cr.ZERO, cr.AXIS, cr.FOUNDER] + [cr.RANDOM] * 20 + [cr.LATENT] * 3
FLOOR = cr.SHIFT_FLOORS_M["route_m"]


def values(axis, pairs=30, spread=0.001, seed=0):
    rng = np.random.default_rng(seed)
    out = 0.05 + rng.normal(0, spread, (pairs, len(FAMILIES)))
    out[:, 2] = axis + rng.normal(0, spread, pairs)
    return out


def test_an_axis_above_controls_on_failing_frames_only_reads_as_specific():
    row = cr.read_outcome(values(0.5), values(0.05, seed=1), FAMILIES, FLOOR)
    assert row["clears"] and row["specific"] and row["excess_interval"][0] > 0


def test_an_axis_equally_above_controls_on_both_arms_clears_but_is_not_specific():
    row = cr.read_outcome(values(0.5), values(0.5, seed=1), FAMILIES, FLOOR)
    assert row["clears"] and not row["specific"]


def test_an_axis_inside_the_controls_does_not_clear():
    row = cr.read_outcome(values(0.05), values(0.05, seed=1), FAMILIES, FLOOR)
    assert not row["clears"] and not row["specific"]


def test_a_tiny_shift_above_controls_stays_under_the_rounding_floor():
    low = values(0.02, spread=1e-5) - np.where(np.array(FAMILIES)[None, :] == cr.AXIS, 0, 0.045)
    row = cr.read_outcome(low, low, FAMILIES, FLOOR)
    assert row["excess_interval"][0] > 0 and not row["clears"] and row["stopped_by"] == ["floor"]


def test_a_shift_inside_the_speed_offset_clears_on_route_but_not_on_speed():
    small = values(0.045, spread=1e-5) - np.where(np.array(FAMILIES)[None, :] == cr.AXIS, 0, 0.048)
    assert cr.read_outcome(small, small, FAMILIES, cr.SHIFT_FLOORS_M["route_m"])["clears"]
    speed = cr.read_outcome(small, small, FAMILIES, cr.SHIFT_FLOORS_M["speed_m"])
    assert not speed["clears"] and speed["stopped_by"] == ["floor"]


def test_one_route_cannot_carry_the_read_however_many_frames_it_has():
    failing = values(0.05, spread=0.001)
    failing[0, 2] = 40.0
    row = cr.read_outcome(failing, values(0.05, seed=1), FAMILIES, FLOOR)
    assert row["excess_m"] > 1.0 and row["excess_interval"][0] <= 0.01
    assert row["stopped_by"] == ["interval"]


def test_route_means_weigh_routes_not_frames():
    frames = [{"pair": 0, "arm": cr.FAILING_ARM}] * 9 + [{"pair": 1, "arm": cr.FAILING_ARM}]
    effects = np.ones((10, 2, 3))
    effects[-1] = 3.0
    means = cr.pair_means(effects, frames, [0, 1], cr.FAILING_ARM)
    assert means[:, 0, 0].mean() == 2.0


def test_a_replay_cut_short_reads_only_whole_pairs():
    frames = [{"pair": 0}] * 3 + [{"pair": 1}] * 3
    assert cr.whole_pairs(frames, 3) == [0]
    assert cr.whole_pairs(frames, 5) == [0]
    assert cr.whole_pairs(frames, 6) == [0, 1]


def frame_effects(frame_count):
    effects = np.zeros((frame_count, len(FAMILIES), cr.EFFECT_COLUMNS), dtype=np.float32)
    effects[:, 1, :2] = 1.0
    effects[:, 2:, 2] = 2.0
    effects[:, 4:, :2] = 0.05
    effects[:, 2, :2] = 0.5
    effects[:, 3, :2] = 0.2
    effects[:, 2:, cr.FRAME_MEAN_EDIT_COLUMN] = 2.0
    effects[:, 2, cr.FRAME_MEAN_EDIT_COLUMN] = 0.5
    return effects


def selection_with(pairs):
    frames = []
    for pair in range(pairs):
        frames += [{"pair": pair, "arm": cr.FAILING_ARM}, {"pair": pair, "arm": cr.CONTROL_ARM}]
    return {"axis": {}, "gap": "P4", "sae": "s", "pairs_expected": pairs, "frames": frames,
            "pairs": [{"pair": pair, "axis_member": pair % 2 == 0} for pair in range(pairs)]}


def names():
    return [family if family not in (cr.RANDOM, cr.LATENT) else f"{family}:{i}" for i, family in enumerate(FAMILIES)]


def test_a_clean_run_reports_a_labelled_rehearsal_never_a_step_nine_verdict():
    effects = frame_effects(60)
    result = cr.build_result(selection_with(30), effects, np.zeros(60), names())
    assert result["dev_rehearsal"] is True and result["step9_verdict"] is False
    assert result["outcome"] == cr.ABOVE_NOT_SHOWN_LARGER
    assert "causal" not in result["outcome"] and "Step 9" in result["label"]


@pytest.mark.parametrize("breaking, check", [
    (lambda e, s: e.__setitem__((..., 0, 0), 0.5), "rerun_p90_m"),
    (lambda e, s: e.__setitem__((..., 1, slice(0, 2)), 0.0), "zeroed_tokens_median_m"),
    (lambda e, s: s.__setitem__(..., 0.5), "site_error_median"),
    (lambda e, s: e.__setitem__((..., slice(4, 24), 2), 2.5), "edit_ratio_worst"),
])
def test_any_failed_check_makes_the_run_untested(breaking, check):
    effects, errors = frame_effects(60), np.zeros(60)
    breaking(effects, errors)
    result = cr.build_result(selection_with(30), effects, errors, names())
    assert result["outcome"] == "untested" and not result["checks"][check]["passes"]


def test_a_result_that_is_not_shown_says_could_not_show_and_names_its_gate():
    effects = frame_effects(60)
    effects[:, 2, :2] = 0.02
    effects[:, 4:, :2] = 0.002
    result = cr.build_result(selection_with(30), effects, np.zeros(60), names())
    assert result["outcome"] == cr.NOT_SHOWN
    assert "could not show" in result["reading"] and "no more than" not in result["reading"]
    assert "route_m: stopped by floor" in result["reading"] and "A 0.020 m" in result["reading"]


def test_a_result_reports_the_frame_mean_edit_and_the_constants_it_was_read_with():
    result = cr.build_result(selection_with(30), frame_effects(60), np.zeros(60), names())
    lengths = result["frame_mean_edit"][cr.FAILING_ARM]
    assert lengths["axis"] == pytest.approx(0.5) and lengths["random_mean"] == pytest.approx(2.0)
    assert result["frame_mean_edit"]["note"] == cr.FRAME_MEAN_NOTE
    assert result["rule"]["shift_floors_m"] == cr.SHIFT_FLOORS_M
    assert result["rule"]["bootstrap_seed"] == cr.BOOTSTRAP_SEED


def test_provenance_names_the_code_and_the_protocol():
    record = cr.provenance()
    assert len(record["code_sha256"]) == 64 and len(record["protocol_sha256"]) == 64


def test_a_run_with_a_broken_site_stops_early_and_a_sound_one_does_not():
    effects = frame_effects(25)
    assert cr.failed_early(effects, np.zeros(25), names()) == []
    assert cr.failed_early(effects, np.full(25, 0.5), names()) == ["site_error_median"]


def test_clearing_only_random_directions_says_so_in_the_reading():
    effects = frame_effects(60)
    effects[:, 24:, :2] = 0.9
    result = cr.build_result(selection_with(30), effects, np.zeros(60), names())
    assert result["outcome"].startswith("above") and cr.NOT_ABOVE_LATENTS in result["reading"]


def test_the_stored_axis_is_h12_s_and_carries_the_best_and_median_beside_it():
    stored = Path(__file__).resolve().parents[1] / "docs/research/data/h12_layer10_plain.json"
    record, spread = cr.stored_axis(stored, "results/savio/h12/sae/L10_k32_s3", "P4_camera_occlusion")
    assert (record["axis_id"], record["axis_size"], record["in_key"]) == ("contrastive-a6", 27, 24)
    assert spread["dictionaries"] == 18 and spread["best_jaccard"] == record["best_jaccard"]
    assert spread["median_jaccard"] == pytest.approx(0.3874, abs=1e-3)
    assert "using the key" in spread["note"]


def test_too_few_whole_pairs_is_untested():
    result = cr.build_result(selection_with(30), frame_effects(30), np.zeros(30), names())
    assert result["pairs_read"] == 15 and result["outcome"] == "untested"
