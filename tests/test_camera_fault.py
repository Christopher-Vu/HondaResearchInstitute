"""Camera faults: the occluded box is black, the rest of the frame and the original are untouched."""
import numpy as np
import pytest

from camera_fault import CameraFault, apply_camera_fault


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


def frames(n):
    return [np.full((4, 4, 4), i, dtype=np.uint8) for i in range(n)]


def test_camera_fault_occlusion_matches_the_stateless_function():
    fault = {"kind": "occlusion", "box": [0.25, 0.2, 0.75, 0.6]}
    assert (CameraFault(fault)(frame()) == apply_camera_fault(frame(), fault)).all()


def test_freeze_holds_the_frame_from_before_each_freeze():
    fault = CameraFault({"kind": "freeze", "period_steps": 4, "duration_steps": 2, "offset_steps": 1})
    seen = [int(fault(f)[0, 0, 0]) for f in frames(9)]
    # Steps 1-2 and 5-6 are frozen on the frames of steps 0 and 4.
    assert seen == [0, 0, 0, 3, 4, 4, 4, 7, 8]


def test_latency_delays_every_frame_by_its_steps():
    fault = CameraFault({"kind": "latency", "delay_steps": 2})
    assert [int(fault(f)[0, 0, 0]) for f in frames(6)] == [0, 0, 0, 1, 2, 3]


def test_no_fault_passes_frames_through_and_bad_settings_are_refused():
    original = frame()
    assert CameraFault(None)(original) is original
    with pytest.raises(ValueError):
        CameraFault({"kind": "freeze", "period_steps": 4, "duration_steps": 4})
    with pytest.raises(ValueError):
        CameraFault({"kind": "smear"})
