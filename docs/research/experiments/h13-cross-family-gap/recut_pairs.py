"""Write H13's amended screen: the three pairs that end before their hazard, cut again to run past it.

    PYTHONPATH=adapters/simlingo python docs/research/experiments/h13-cross-family-gap/recut_pairs.py

Each replacement keeps its arm's weather, scenario, parameters and start. Only its id, base id and last waypoints change.
"""
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
from cut_routes import cut_bounds, required_tail_m, trigger_of, waypoints
from dev_routes import manifest_document, routes_document

ROOT = Path(__file__).resolve().parents[3].parent
SCREEN = ROOT / "configs/rollout/step5-pilot-p20-screen.yaml"
AMENDED = ROOT / "configs/rollout/step5-pilot-p20-screen-amended.yaml"
NEW_BASE_IDS = {"64155": "64901", "64223": "64902", "64250": "64903"}
TAIL_PAST_HAZARD_M = 60


def long_route_positions(scenario: ET.Element, first_point: tuple[float, ...], long_routes: list[ET.Element],
                         lead_m: float) -> list[ET.Element]:
    """Waypoints from the same start as the first cut, on the long route it came from, to the first past the required tail."""
    trigger = trigger_of(scenario)
    for route in long_routes:
        if any(other.get("type") == scenario.get("type") and trigger_of(other) == trigger for other in route.iter("scenario")):
            bounds = cut_bounds(waypoints(route), trigger, lead_m, required_tail_m(scenario, TAIL_PAST_HAZARD_M))
            if bounds and waypoints(route)[bounds[0]] == first_point:
                return list(route.iter("position"))[bounds[0]:bounds[1] + 1]
    raise ValueError(f"no long route keeps the start of the cut with trigger {trigger}")


def recut_arm(route: ET.Element, new_base: str, long_routes: list[ET.Element], lead_m: float) -> ET.Element:
    recut = copy.deepcopy(route)
    recut.set("id", new_base + route.get("id")[-2:])
    holder = recut.find("waypoints")
    holder.clear()
    holder.extend(copy.deepcopy(long_route_positions(next(route.iter("scenario")), waypoints(route)[0], long_routes, lead_m)))
    return recut


def amended_screen() -> tuple[str, list[dict]]:
    config = yaml.safe_load(SCREEN.read_text())
    spec = config["pilot"]["cut_routes"]
    long_routes = [route for path in spec["from"] for route in ET.parse(ROOT / path).getroot().iter("route")]
    routes, entries = [], []
    screen_routes = {route.get("id"): route for route in ET.parse(ROOT / config["route"]["routes_file"]).getroot().iter("route")}
    for entry in yaml.safe_load((ROOT / config["route"]["manifest"]).read_text()):
        route, new_base = screen_routes[entry["id"]], NEW_BASE_IDS.get(entry["base_id"])
        if new_base is None:
            routes.append(route)
            entries.append(entry)
            continue
        recut = recut_arm(route, new_base, long_routes, spec["lead_m"])
        routes.append(recut)
        entries.append({**entry, "id": recut.get("id"), "base_id": new_base, "recut_of": entry["base_id"]})
    return routes_document(routes), entries


def main() -> None:
    config = yaml.safe_load(AMENDED.read_text())
    document, entries = amended_screen()
    (ROOT / config["route"]["routes_file"]).write_text(document)
    (ROOT / config["route"]["manifest"]).write_text(manifest_document(entries))
    print(f"{len(entries)} routes, {sum('recut_of' in entry for entry in entries)} re-cut")


if __name__ == "__main__":
    main()
