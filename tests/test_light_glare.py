"""Traffic-light glare geometry: boxes ahead land in the image, boxes behind the lens or off-image do not."""
import numpy as np

from light_glare import camera_to_world, glare_rects

WIDTH, HEIGHT, FOV = 1024, 512, 110
MOUNT = (-1.5, 0.0, 2.0)


def box(centre, half=0.3):
    signs = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)])
    return np.array(centre) + half * signs


def ego(x=0.0, y=0.0, yaw_degrees=0.0):
    yaw = np.radians(yaw_degrees)
    matrix = np.eye(4)
    matrix[:2, :2] = [[np.cos(yaw), -np.sin(yaw)], [np.sin(yaw), np.cos(yaw)]]
    matrix[:2, 3] = (x, y)
    return matrix


def rects(boxes, ego_matrix=None):
    world_to_camera = np.linalg.inv(camera_to_world(ego() if ego_matrix is None else ego_matrix, MOUNT))
    return glare_rects(world_to_camera, boxes, WIDTH, HEIGHT, FOV)


def centre_of(rect):
    return (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2


def test_a_box_straight_ahead_lands_in_the_image_centre_and_is_padded():
    (rect,) = rects([box((18.5, 0, 2.0))])
    assert centre_of(rect) == (WIDTH / 2, HEIGHT / 2)
    assert rect[2] - rect[0] >= 4 * 2


def test_a_box_to_the_right_lands_right_of_centre():
    (rect,) = rects([box((18.5, 5, 2.0))])
    assert centre_of(rect)[0] > WIDTH / 2


def test_a_box_behind_the_camera_is_skipped():
    assert rects([box((-10, 0, 2.0))]) == []


def test_a_box_partly_off_image_is_clipped():
    (rect,) = rects([box((6, 8, 2.0), half=1.0)])
    assert rect[2] == WIDTH and rect[0] < WIDTH


def test_a_box_wholly_off_image_is_dropped():
    assert rects([box((6, 40, 2.0))]) == []


def test_the_ego_yaw_is_respected():
    world_box = box((18.5, 0, 2.0))
    assert len(rects([world_box])) == 1
    assert rects([world_box], ego(yaw_degrees=90)) == []
