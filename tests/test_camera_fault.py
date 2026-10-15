"""Camera faults: the occluded box is black, the rest of the frame and the original are untouched."""
import numpy as np
import pytest

from camera_fault import apply_camera_fault


def frame():
    return np.full((10, 20, 4), 200, dtype=np.uint8)


def test_occlusion_blacks_out_the_box_and_nothing_else():
    original = frame()
    faulty = apply_camera_fault(original, {"kind": "occlusion", "box": [0.25, 0.2, 0.75, 0.6]})
    assert (faulty[2:6, 5:15, :3] == 0).all()
    assert (faulty[:, :, 3] == 200).all() and faulty[0, 0, 0] == 200 and faulty[8, 18, 0] == 200
    assert (original == 200).all()


def test_no_fault_returns_the_frame_unchanged():
    original = frame()
    assert apply_camera_fault(original, None) is original


def test_an_unknown_fault_is_refused():
    with pytest.raises(ValueError):
        apply_camera_fault(frame(), {"kind": "smear"})
