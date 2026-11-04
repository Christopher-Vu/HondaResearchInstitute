"""Fail2Drive pairs score as planted gaps: the generalization route is the slice, its base twin the neighbourhood."""
import pytest

from fail2drive_pairs import build


def write(split, name, route_id, scenario=""):
    (split / name).write_text(f'<routes><route id="{route_id}" town="Town13"><scenarios>{scenario}</scenarios></route></routes>')


def test_each_pair_is_one_base_with_the_unseen_scenario_on_the_slice(tmp_path):
    write(tmp_path, "Base_Wall_0095.xml", 95)
    write(tmp_path, "Generalization_Wall_1095.xml", 1095, '<scenario name="RoadBlocked" type="RoadBlocked"/>')
    root, manifest = build(["Wall"], tmp_path)
    slice_, nearby = manifest
    assert (slice_["id"], slice_["role"], slice_["practice_gaps"], slice_["scenario"]) == ("1095", "pilot_slice", ["F2D_Wall"], "RoadBlocked")
    assert (nearby["id"], nearby["role"], nearby["neighbourhood_of"], nearby["scenario"]) == ("95", "pilot_neighbourhood", ["F2D_Wall"], None)
    assert slice_["base_id"] == nearby["base_id"] and len(list(root.iter("route"))) == 2


def test_a_base_without_its_twin_refuses(tmp_path):
    write(tmp_path, "Base_Wall_0095.xml", 95)
    with pytest.raises(FileNotFoundError, match="twin"):
        build(["Wall"], tmp_path)


def test_a_base_twin_without_a_scenario_is_a_runnable_route(tmp_path):
    from route_run import NO_SCENARIO, check_route, route_from_xml
    (tmp_path / "routes.xml").write_text('<routes><route id="95" town="Town13"><scenarios/></route></routes>')
    config = {"route": {"routes_file": str(tmp_path / "routes.xml")}}
    config["route"].update(route_from_xml("95", config))
    assert config["route"]["scenario"] == NO_SCENARIO
    check_route(config)
