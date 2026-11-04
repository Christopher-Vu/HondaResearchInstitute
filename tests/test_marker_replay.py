"""H14's offline test: what the mask takes and leaves, the seeded draw and placebo, and the gates that stop the work."""
import json

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")
import marker_replay as replay  # noqa: E402


def road_frame():
    """A flat grey road below the horizon and a dark sky above it, at the policy camera's size."""
    frame = np.full((512, 1024, 3), 120, dtype=np.uint8)
    frame[:256] = (30, 40, 90)
    return frame


def square(frame, top, left, size, colour):
    frame[top:top + size, left:left + size] = colour


GREEN, CYAN, YELLOW, RED = (0, 245, 56), (172, 241, 240), (244, 246, 83), (248, 59, 71)


@pytest.mark.parametrize("name, colour, size", [("green", GREEN, 6), ("cyan", CYAN, 6), ("yellow", YELLOW, 6), ("red", RED, 12)])
def test_a_rendered_marker_on_the_road_is_found_with_its_colour(name, colour, size):
    frame = road_frame()
    square(frame, 330, 500, size, colour)
    blobs = replay.find_markers(frame)
    assert [blob.colour for blob in blobs] == [name]
    assert (blobs[0].top, blobs[0].left, blobs[0].shape.sum()) == (330, 500, size * size)


def test_a_green_traffic_light_above_the_horizon_is_left_alone():
    frame = road_frame()
    square(frame, 200, 600, 6, GREEN)
    assert replay.find_markers(frame) == []


def test_a_marker_below_the_policys_crop_is_left_alone():
    frame = road_frame()
    square(frame, replay.policy_rows(512) + 5, 500, 6, GREEN)
    assert replay.find_markers(frame) == []


def test_a_white_block_is_found_as_its_own_colour():
    frame = road_frame()
    frame[330:339, 500:514] = (243, 243, 243)
    assert [blob.colour for blob in replay.find_markers(frame)] == [replay.WHITE]


@pytest.mark.parametrize("top, left, height, width", [(330, 300, 6, 60), (300, 500, 40, 6), (330, 500, 4, 4)])
def test_white_lane_paint_crosswalk_stripes_and_specks_are_not_white_blocks(top, left, height, width):
    frame = road_frame()
    frame[top:top + height, left:left + width] = (243, 243, 243)
    assert replay.find_markers(frame) == []


def test_a_pale_road_is_not_a_white_block():
    frame = road_frame()
    frame[330:339, 500:514] = (205, 205, 205)
    assert replay.find_markers(frame) == []


@pytest.mark.parametrize("colour, height, width", [((244, 246, 83), 2, 30), ((0, 245, 56), 3, 60)])
def test_a_long_strip_touching_the_crop_line_is_paint(colour, height, width):
    frame = road_frame()
    rows = replay.policy_rows(512)
    frame[rows - height:rows, 500:500 + width] = colour
    assert replay.find_markers(frame) == []


def test_a_marker_cut_by_the_crop_line_is_still_found():
    frame = road_frame()
    rows = replay.policy_rows(512)
    frame[rows - 3:rows, 500:510] = (0, 245, 56)
    assert [blob.colour for blob in replay.find_markers(frame)] == ["green"]


def test_tail_lights_and_lane_paint_are_left_alone():
    frame = road_frame()
    square(frame, 300, 400, 3, RED)
    frame[320:324, 300:330] = YELLOW
    assert replay.find_markers(frame) == []


def test_a_saturated_body_around_a_marker_coloured_patch_is_left_alone():
    frame = road_frame()
    frame[300:340, 600:680] = (40, 60, 200)
    square(frame, 318, 636, 6, GREEN)
    assert replay.find_markers(frame) == []


def test_large_shapes_are_not_markers():
    frame = road_frame()
    square(frame, 290, 500, 30, GREEN)
    assert replay.find_markers(frame) == []


def test_painting_removes_the_marker_and_changes_nothing_outside_the_grown_mask():
    frame = road_frame()
    square(frame, 330, 500, 6, GREEN)
    painted = replay.paint(frame, replay.find_markers(frame))
    assert replay.find_markers(painted) == []
    changed = np.any(painted != frame, axis=2)
    assert changed[330:336, 500:506].all()
    assert not changed[:330 - replay.GROW_PIXELS - 1].any() and not changed[:, :500 - replay.GROW_PIXELS - 1].any()


def test_placebo_keeps_each_shape_on_empty_road_away_from_the_markers_and_is_seeded():
    frame = road_frame()
    square(frame, 330, 500, 6, GREEN)
    square(frame, 300, 700, 6, YELLOW)
    markers = replay.find_markers(frame)
    placed = replay.placebo_blobs(frame, markers, "26956", 40)
    assert sorted(blob.shape.sum() for blob in placed) == sorted(blob.shape.sum() for blob in markers)
    for spot in placed:
        assert replay.HORIZON_ROW <= spot.top and spot.bottom <= replay.policy_rows(512)
        for marker in markers:
            assert abs(spot.left - marker.left) > replay.PLACEBO_CLEARANCE or abs(spot.top - marker.top) > replay.PLACEBO_CLEARANCE
    again = replay.placebo_blobs(frame, markers, "26956", 40)
    assert [(blob.top, blob.left) for blob in placed] == [(blob.top, blob.left) for blob in again]
    other = replay.placebo_blobs(frame, markers, "26956", 60)
    assert [(blob.top, blob.left) for blob in placed] != [(blob.top, blob.left) for blob in other]


@pytest.mark.parametrize("top", [262, 300, 345])
def test_placebo_sits_in_its_markers_row_band(top):
    frame = road_frame()
    square(frame, top, 500, 6, GREEN)
    markers = replay.find_markers(frame)
    for step in range(20):
        placed = replay.placebo_blobs(frame, markers, "1", step)
        assert abs(placed[0].top - top) <= replay.PLACEBO_ROW_BAND
        assert replay.placebo_row_gap(markers, placed) == abs(placed[0].top - top)


def test_placebo_goes_outside_the_band_only_when_the_band_has_no_room():
    frame = road_frame()
    frame[256:320] = (20, 120, 30)
    markers = [replay.Blob("green", 500, 262, np.ones((6, 6), bool))]
    placed = replay.placebo_blobs(frame, markers, "1", 20)
    assert placed[0].top >= 320 and replay.placebo_row_gap(markers, placed) > replay.PLACEBO_ROW_BAND


def test_placebo_road_includes_thin_stripes_and_leaves_out_a_large_plain_object():
    frame = road_frame()
    frame[325:336, 200:800] = 235
    frame[300:360, 880:960] = 60
    road = replay.empty_road(frame, [])
    assert road[330, 400] and road[345, 400]
    assert not road[330, 920]


def test_a_frame_with_no_road_ahead_gets_no_placebo():
    frame = road_frame()
    square(frame, 330, 500, 6, GREEN)
    markers = replay.find_markers(frame)
    rng = np.random.default_rng(frame.shape[0])
    frame[256:, :, 0] = rng.integers(0, 255, size=frame[256:, :, 0].shape, dtype=np.uint8)
    assert replay.placebo_blobs(frame, markers, "1", 20) is None


def test_the_draw_is_the_protocols_first_forty():
    draw = replay.drawn_routes()
    assert len(draw) == 200 and len(set(draw)) == 200
    assert draw[:5] == ["1486260", "270960", "2475960", "2436760", "318460"]
    assert draw[39] == "1484260"


def fake_route(run, route, steps=(20, 40), inputs=(10, 20, 30, 40)):
    (run / f"route-{route}/frames").mkdir(parents=True)
    (run / f"route-{route}/capture/inputs").mkdir(parents=True)
    for step in (0, *steps):
        (run / f"route-{route}/frames/{step:06d}.png").write_bytes(b"")
    for step in inputs:
        (run / f"route-{route}/capture/inputs/{step:06d}.pt").write_bytes(b"")


def test_a_frame_needs_both_files_and_a_route_without_any_gives_way_to_the_next(tmp_path):
    fake_route(tmp_path, "1")
    (tmp_path / "route-2").mkdir()
    fake_route(tmp_path, "3")
    fake_route(tmp_path, "4")
    frames, used, passed_over = replay.usable_frames(tmp_path, ["1", "2", "3", "4"], routes_used=2)
    assert used == ["1", "3"] and passed_over == ["2"]
    assert [(frame.route, frame.step) for frame in frames] == [("1", 20), ("1", 40), ("3", 20), ("3", 40)]


@pytest.mark.parametrize("report, passes", [
    (None, False),
    ({"frames_viewed": None, "coloured_dots_visible": None, "coloured_dots_caught": None,
      "frames_touching_traffic_light_or_vehicle": None}, False),
    ({"frames_viewed": 50, "coloured_dots_visible": 100, "coloured_dots_caught": 90, "frames_touching_traffic_light_or_vehicle": 0}, True),
    ({"frames_viewed": 50, "coloured_dots_visible": 100, "coloured_dots_caught": 89, "frames_touching_traffic_light_or_vehicle": 0}, False),
    ({"frames_viewed": 50, "coloured_dots_visible": 100, "coloured_dots_caught": 100, "frames_touching_traffic_light_or_vehicle": 1}, False),
    ({"frames_viewed": 49, "coloured_dots_visible": 100, "coloured_dots_caught": 100, "frames_touching_traffic_light_or_vehicle": 0}, False),
    ({"frames_viewed": 50, "coloured_dots_visible": 0, "coloured_dots_caught": 0, "frames_touching_traffic_light_or_vehicle": 0}, False),
])
def test_the_mask_check_gate(report, passes):
    assert replay.mask_check_passes(report) == passes


def viewed(**white):
    return {"frames_viewed": 50, "coloured_dots_visible": 100, "coloured_dots_caught": 90,
            "frames_touching_traffic_light_or_vehicle": 0, **white}


@pytest.mark.parametrize("white, holds, passes", [
    (dict(white_rings_drawn=20, white_rings_not_on_a_block=2, white_blocks_visible=20, white_blocks_caught=18), True, True),
    (dict(white_rings_drawn=20, white_rings_not_on_a_block=3, white_blocks_visible=20, white_blocks_caught=20), False, True),
    (dict(white_rings_drawn=20, white_rings_not_on_a_block=0, white_blocks_visible=20, white_blocks_caught=17), False, True),
    (dict(white_rings_drawn=0, white_rings_not_on_a_block=0, white_blocks_visible=0, white_blocks_caught=0), True, True),
    (dict(white_rings_drawn=20, white_rings_not_on_a_block=None, white_blocks_visible=20, white_blocks_caught=20), False, True),
])
def test_white_blocks_join_the_mask_gate_only_while_their_rule_holds(white, holds, passes):
    report = viewed(**white)
    assert replay.white_rule_holds(report) == holds
    assert replay.mask_check_passes(report) == passes


def test_white_blocks_that_are_missed_count_against_the_gate_while_the_rule_holds():
    report = {**viewed(white_rings_drawn=100, white_rings_not_on_a_block=0, white_blocks_visible=100, white_blocks_caught=90),
              "coloured_dots_caught": 89}
    assert replay.white_rule_holds(report) and not replay.mask_check_passes(report)


def test_the_reproduction_gate_stops_above_five_percent():
    assert replay.reproduction_passes(5, 100)
    assert not replay.reproduction_passes(6, 100)
    assert not replay.reproduction_passes(0, 0)


class FakeReplayer:
    def __init__(self, failing):
        self.failing = failing

    def reproduces(self, frame):
        return frame.step not in self.failing


def refs(count):
    return [replay.FrameRef("1", step, None, None) for step in range(count)]


def test_the_reproduction_gate_drops_a_mismatching_frame_and_writes_its_report(tmp_path):
    kept = replay.reproduction_gate(FakeReplayer({3}), refs(40), tmp_path)
    assert len(kept) == 39 and 3 not in [frame.step for frame in kept]
    assert json.loads((tmp_path / "reproduction.json").read_text()) == {"frames": 40, "dropped": 1, "passed": True}


def test_the_reproduction_gate_stops_the_work_above_five_percent(tmp_path):
    with pytest.raises(SystemExit):
        replay.reproduction_gate(FakeReplayer({0, 1, 2}), refs(40), tmp_path)
    assert not json.loads((tmp_path / "reproduction.json").read_text())["passed"]


def test_reproduces_compares_the_png_rebuild_with_the_saved_pixel_values(tmp_path):
    from PIL import Image
    from types import SimpleNamespace
    png = tmp_path / "000020.png"
    frame = road_frame()
    Image.fromarray(frame).save(png)
    replayer = replay.Replayer.__new__(replay.Replayer)
    replayer.torch = SimpleNamespace(equal=np.array_equal)
    replayer.dtype, replayer.device = None, None
    replayer.pixel_values = lambda rgb: rgb
    ref = replay.FrameRef("1", 20, png, tmp_path / "000020.pt")
    replayer.load_frame = lambda *_: SimpleNamespace(camera_images=frame)
    assert replayer.reproduces(ref)
    replayer.load_frame = lambda *_: SimpleNamespace(camera_images=frame + 1)
    assert not replayer.reproduces(ref)


@pytest.mark.parametrize("excess_m, start", [(0.0199, "Under 2"), (0.02, "2 to 7"), (0.07, "2 to 7"), (0.0701, "Over 7"), (-0.01, "Under 2")])
def test_the_excess_reading_table(excess_m, start):
    assert replay.excess_reading(excess_m).startswith(start)


def test_nearest_marker_estimate_falls_with_image_row():
    frame = road_frame()
    near = replay.Blob("green", 500, 340, np.ones((6, 6), bool))
    far = replay.Blob("green", 500, 275, np.ones((6, 6), bool))
    assert replay.nearest_marker_m([near, far], *frame.shape[:2]) < replay.nearest_marker_m([far], *frame.shape[:2])
    assert replay.nearest_marker_m([near], *frame.shape[:2]) == pytest.approx(358.5 * 2.0 / 90, abs=0.1)
    assert replay.nearest_marker_m([replay.Blob("green", 500, 240, np.ones((6, 6), bool))], *frame.shape[:2]) == float("inf")


def row(route, painted, placebo, colours=("green",), nearest=10.0, lowest=300, gap=5):
    fields = lambda value: {"route_m": value, "speed_m": value, "layer_driving_mean": value}  # noqa: E731
    return {"route": route, "step": 20, "colours": list(colours), "nearest_marker_m": nearest,
            "lowest_marker_row": lowest, "placebo_row_gap": gap,
            "painted": fields(painted), "placebo": fields(placebo)}


def test_summary_takes_painted_median_minus_placebo_median_and_splits_groups():
    rows = [row(str(i % 8), 0.05, 0.01, colours=("green", "cyan") if i % 2 else ("green",), nearest=10.0 if i % 4 else 30.0)
            for i in range(40)]
    report = replay.summarize(rows)
    assert report["excess_route_m"] == pytest.approx(0.04)
    assert report["reading"].startswith("2 to 7")
    groups = report["groups"]
    assert groups["all"]["frames"] == 40 and groups["all"]["routes"] == 8
    assert groups["colour: cyan"]["frames"] == 20 and "colour: red" not in groups
    assert groups["nearest under 15 m"]["frames"] == 30 and groups["nearest 15 m or more"]["frames"] == 10
    assert groups["all"]["route_m"]["excess_median_interval_90"] == pytest.approx([0.04, 0.04])


def test_summary_reports_excess_by_row_band_and_by_how_well_the_placebo_matched():
    rows = [row(str(i), 0.05, 0.01, lowest=270 if i < 3 else 300 if i < 7 else 340, gap=5 if i % 2 else 30) for i in range(10)]
    groups = replay.summarize(rows)["groups"]
    assert groups["lowest marker above row 280"]["frames"] == 3
    assert groups["lowest marker in rows 280 to 319"]["frames"] == 4
    assert groups["lowest marker at row 320 or below"]["frames"] == 3
    assert groups["placebo within 15 rows of its marker"]["frames"] == 5
    assert groups["lowest marker in rows 280 to 319"]["route_m"]["excess_median"] == pytest.approx(0.04)


def test_the_census_compares_replayed_frames_with_those_that_had_no_room(tmp_path):
    fates = [(replay.REPLAYED, 50, 300, 0), (replay.REPLAYED, 70, 320, 1), (replay.NO_PLACEBO_SPOT, 200, 280, 1), (replay.NO_MARKER, 0, 0, 0)]
    (tmp_path / "rows.jsonl").write_text("")
    (tmp_path / "census.jsonl").write_text("".join(
        json.dumps({"route": "1", "step": i, "fate": fate, "marker_pixels": pixels, "lowest_marker_row": lowest, "white_blocks": white}) + "\n"
        for i, (fate, pixels, lowest, white) in enumerate(fates)))
    report = replay.write_summary(tmp_path, {})
    assert report["frames_read"] == 4 and report["frames_by_fate"] == {replay.REPLAYED: 2, replay.NO_MARKER: 1, replay.NO_PLACEBO_SPOT: 1}
    assert report["frames_with_white_block"] == 2
    assert report["replayed_against_no_room"][replay.REPLAYED]["marker_pixels"]["median"] == 60
    assert report["replayed_against_no_room"][replay.NO_PLACEBO_SPOT]["lowest_marker_row"]["median"] == 280


class StubReplayer:
    def replay(self, ref, rgb, markers, placebo):
        return row(ref.route, 0.05, 0.01)


def test_white_blocks_stay_out_of_the_mask_when_their_rule_fails_and_are_still_counted(tmp_path):
    from PIL import Image
    frame = road_frame()
    frame[330:339, 500:514] = (243, 243, 243)
    png = tmp_path / "000020.png"
    Image.fromarray(frame).save(png)
    ref = replay.FrameRef("1", 20, png, tmp_path / "000020.pt")
    replay.replay_frames(StubReplayer(), [ref], tmp_path, paint_white=False)
    assert replay.read_census(tmp_path)[0]["fate"] == replay.NO_MARKER and replay.read_census(tmp_path)[0]["white_blocks"] == 1
    replay.replay_frames(StubReplayer(), [ref], tmp_path, paint_white=True)
    assert replay.read_census(tmp_path)[0]["fate"] == replay.REPLAYED and len(replay.read_rows(tmp_path)) == 1


def test_the_bootstrap_resamples_routes_not_frames():
    rows = [row("a", 0.1, 0.0) for _ in range(100)] + [row("b", 0.0, 0.0)]
    low, high = replay.shift_summary(rows, "route_m")["painted"]["median_interval_90"]
    assert low == pytest.approx(0.0) and high == pytest.approx(0.1)


def test_summary_written_from_rows_survives_a_job_that_ran_out_of_time(tmp_path):
    (tmp_path / "rows.jsonl").write_text("".join(json.dumps(row(str(i), 0.03, 0.0)) + "\n" for i in range(4)))
    report = replay.write_summary(tmp_path, {"run": "x"})
    assert report["frames_replayed"] == 4 and json.loads((tmp_path / "summary.json").read_text())["run"] == "x"


def test_sheets_list_each_blobs_colour_and_area_and_prefill_the_white_ring_count(tmp_path):
    from PIL import Image
    frame = road_frame()
    square(frame, 330, 500, 6, GREEN)
    frame[300:309, 700:714] = (243, 243, 243)
    png = tmp_path / "000020.png"
    Image.fromarray(frame).save(png)
    replay.write_sheets([replay.FrameRef("1", 20, png, png)], tmp_path)
    listed = json.loads((tmp_path / "mask-check-frames.json").read_text())[0]["blobs"]
    assert sorted((blob["colour"], blob["area"]) for blob in listed) == [("green", 36), ("white", 126)]
    assert json.loads((tmp_path / "mask-check.json").read_text())["white_rings_drawn"] == 1


def test_the_sheet_stacks_the_crop_raw_above_ringed():
    frame = road_frame()
    square(frame, 330, 500, 6, GREEN)
    panel = replay.mask_panel(frame, replay.find_markers(frame))
    rows = replay.policy_rows(512)
    assert panel.shape == (2 * rows, 1024, 3)
    assert np.array_equal(panel[:rows], frame[:rows])
    assert np.any(panel[rows:] != frame[:rows])
