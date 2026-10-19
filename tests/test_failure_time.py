"""A failing rollout's window ends at its first infraction of any kind, not only its first collision."""
import numpy as np

from harness.failure_time import failure_step

STEPS = np.arange(0, 100, 5)


def failing(**meta):
    return {"success": False, "first_collision_step": None, "infractions": {}, **meta}


def test_a_successful_rollout_has_no_failure_step():
    assert failure_step({"success": True, "first_collision_step": 3}, {"step": STEPS}) is None


def test_a_collision_alone_keeps_its_logged_step():
    assert failure_step(failing(first_collision_step=42), {"step": STEPS}) == 42


def test_a_pure_timeout_gives_none_so_the_window_is_the_last_three_seconds():
    meta = failing(infractions={"route_timeout": 1}, infraction_locations={})
    assert failure_step(meta, {"step": STEPS, "ego_speed": np.full(len(STEPS), 5.0)}) is None


def test_a_located_infraction_is_timed_at_the_ego_s_nearest_approach():
    x = STEPS.astype(float)
    meta = failing(infractions={"red_light": 1}, infraction_locations={"red_light": [[40.2, 0.0]]})
    assert failure_step(meta, {"step": STEPS, "ego_x": x, "ego_y": np.zeros_like(x)}) == 40


def test_a_blocked_ego_is_timed_where_it_first_stopped_not_where_it_sat_longest():
    x = np.minimum(STEPS, 50).astype(float)
    meta = failing(infractions={"vehicle_blocked": 1}, infraction_locations={"vehicle_blocked": [[50.0, 0.0]]})
    assert failure_step(meta, {"step": STEPS, "ego_x": x, "ego_y": np.zeros_like(x)}) == 50


def test_the_earliest_of_collision_and_located_infractions_wins():
    x = STEPS.astype(float)
    meta = failing(first_collision_step=70, infraction_locations={"route_dev": [[30.0, 0.0]]})
    assert failure_step(meta, {"step": STEPS, "ego_x": x, "ego_y": np.zeros_like(x)}) == 30


def test_a_location_far_from_every_ego_position_is_not_a_time():
    x = STEPS.astype(float)
    meta = failing(infraction_locations={"stop_infraction": [[40.0, 500.0]]})
    assert failure_step(meta, {"step": STEPS, "ego_x": x, "ego_y": np.zeros_like(x)}) is None


def test_older_shards_time_a_red_light_when_the_ego_leaves_it_while_moving():
    red = np.zeros(len(STEPS))
    red[2:4] = 1      # stopped at a red, then it turned green: not the infraction
    red[10:13] = 1    # drove through
    speed = np.full(len(STEPS), 6.0)
    speed[3] = 0.0
    meta = failing(infractions={"red_light": 1})
    assert failure_step(meta, {"step": STEPS, "red_light": red, "ego_speed": speed}) == STEPS[13]


def test_older_shards_time_a_blocked_ego_at_the_start_of_its_final_stationary_stretch():
    speed = np.full(len(STEPS), 6.0)
    speed[4:6] = 0.0
    speed[12:] = 0.0
    meta = failing(infractions={"vehicle_blocked": 1})
    assert failure_step(meta, {"step": STEPS, "ego_speed": speed}) == STEPS[12]


def test_older_shards_without_a_proxy_for_the_infraction_give_none():
    meta = failing(infractions={"outside_route_lanes": 1})
    assert failure_step(meta, {"step": STEPS, "ego_speed": np.full(len(STEPS), 6.0)}) is None
