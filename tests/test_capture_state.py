"""The probe-target geometry: which vehicle leads, what counts as occluded, how far the next junction is."""
import pytest

from state_geometry import (EgoFrame, Neighbour, blocked_before_target, find_lead, is_nearby, junction_distance,
                            lead_relative_speed, nearest_pedestrian, occlusion_target, time_to_junction)


def neighbour(forward, right=0.0, forward_speed=0.0, extent=2.4, up=0.0):
    return Neighbour(forward, right, up, forward_speed, extent)


class FakeWaypoint:
    def __init__(self, is_junction=False, following=None):
        self.is_junction = is_junction
        self.following = following

    def next(self, _step):
        return [] if self.following is None else [self.following]


def straight_road(length, junction_at):
    """A lane of `length` unit-spaced waypoints whose waypoint number `junction_at` is a junction."""
    waypoint = None
    for position in reversed(range(length)):
        waypoint = FakeWaypoint(is_junction=position == junction_at, following=waypoint)
    return waypoint


def test_ego_frame_puts_ahead_on_x_right_on_y_and_height_difference_on_z_at_any_heading():
    ahead_when_facing_north = EgoFrame(10.0, 5.0, 1.0, 90.0).locate(10.0, 25.0, 1.0)
    right_when_facing_east = EgoFrame(0.0, 0.0, 0.0, 0.0).locate(0.0, 3.0, -2.0)
    assert ahead_when_facing_north == pytest.approx((20.0, 0.0, 0.0))
    assert right_when_facing_east == pytest.approx((0.0, 3.0, -2.0))


def test_forward_component_ignores_sideways_motion():
    frame = EgoFrame(0.0, 0.0, 0.0, 90.0)
    assert frame.forward_component(4.0, 6.0) == pytest.approx(6.0)


def test_lead_is_the_nearest_vehicle_ahead_inside_the_lane():
    near, far = neighbour(12.0, 0.5), neighbour(30.0)
    assert find_lead([far, near]) is near


@pytest.mark.parametrize("vehicle", [
    neighbour(-8.0), neighbour(0.0), neighbour(20.0, right=1.8), neighbour(20.0, right=-2.5), neighbour(50.5),
])
def test_vehicles_behind_beside_or_beyond_range_are_not_leads(vehicle):
    assert find_lead([vehicle]) is None


def test_lane_edge_and_range_edge_still_count():
    assert find_lead([neighbour(50.0, right=1.75)]) is not None


def test_relative_speed_is_ego_minus_lead_along_the_ego_heading():
    assert lead_relative_speed(10.0, neighbour(20.0, forward_speed=4.0)) == pytest.approx(6.0)
    assert lead_relative_speed(10.0, neighbour(20.0, forward_speed=12.0)) == pytest.approx(-2.0)
    assert lead_relative_speed(10.0, None) is None


def test_distance_counts_height_so_a_walker_parked_below_the_map_is_far():
    assert neighbour(3.0, 4.0, up=12.0).distance == pytest.approx(13.0)
    assert nearest_pedestrian([neighbour(0.0, 0.0, up=-50.5)]) is None


@pytest.mark.parametrize("forward, right, up, nearby", [
    (60.0, 0.0, 0.0, True), (36.0, 48.0, 0.0, True), (60.1, 0.0, 0.0, False), (0.0, 0.0, 20.0, True),
    (0.0, 0.0, -20.1, False), (0.0, 0.0, -50.0, False), (10.0, 0.0, -200.0, False),
])
def test_only_actors_on_the_ego_s_level_and_within_sixty_metres_are_neighbours(forward, right, up, nearby):
    assert is_nearby(forward, right, up) is nearby


def test_nearest_pedestrian_is_euclidean_and_ignores_the_far_ones():
    behind, beside, far = neighbour(-4.0, 0.0), neighbour(3.0, 4.0), neighbour(49.0, 20.0)
    assert nearest_pedestrian([far, beside, behind]) is behind
    assert nearest_pedestrian([far]) is None
    assert nearest_pedestrian([]) is None


def test_occlusion_target_is_whichever_of_lead_and_walker_ahead_is_closer():
    walker = neighbour(15.0, 3.0)
    far_lead, near_lead = neighbour(25.0), neighbour(10.0)
    assert occlusion_target(far_lead, [walker]) is walker
    assert occlusion_target(near_lead, [walker]) is near_lead


def test_occlusion_target_skips_walkers_behind_or_beyond_forty_metres():
    assert occlusion_target(None, [neighbour(-5.0), neighbour(39.0, 15.0), neighbour(30.0, 30.0)]) is None
    lead = neighbour(45.0)
    assert occlusion_target(lead, [neighbour(-5.0), neighbour(39.0, 15.0)]) is lead


def test_occlusion_target_is_none_with_nothing_relevant():
    assert occlusion_target(None, []) is None


def test_the_target_hitting_itself_is_not_occlusion():
    own_front_face = 30.0 - 2.4
    assert not blocked_before_target([own_front_face], 30.0, 2.4)
    assert not blocked_before_target([], 30.0, 2.4)


def test_a_hit_nearer_than_the_target_surface_is_occlusion():
    assert blocked_before_target([18.0, 27.6], 30.0, 2.4)


def test_the_margin_sits_half_a_metre_inside_the_target():
    boundary = 30.0 - 2.4 - 0.5
    assert not blocked_before_target([boundary], 30.0, 2.4)
    assert blocked_before_target([boundary - 0.01], 30.0, 2.4)


def test_junction_distance_is_zero_inside_a_junction():
    assert junction_distance(FakeWaypoint(is_junction=True)) == 0.0


def test_junction_distance_counts_metres_along_the_lane():
    assert junction_distance(straight_road(100, junction_at=17)) == 17.0


def test_junction_exactly_at_the_range_limit_is_found_and_beyond_it_is_not():
    assert junction_distance(straight_road(100, junction_at=50)) == 50.0
    assert junction_distance(straight_road(100, junction_at=51)) is None


def test_lane_that_ends_before_any_junction_gives_none():
    assert junction_distance(straight_road(10, junction_at=99)) is None


def test_time_to_junction_divides_by_speed_with_a_floor_and_a_cap():
    assert time_to_junction(20.0, 10.0) == pytest.approx(2.0)
    assert time_to_junction(20.0, 0.0) == pytest.approx(30.0)
    assert time_to_junction(5.0, 0.0) == pytest.approx(10.0)
    assert time_to_junction(0.0, 8.0) == 0.0
    assert time_to_junction(None, 8.0) is None
