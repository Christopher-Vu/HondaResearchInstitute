"""Build a routes file and manifest from Fail2Drive's own route pairs, for a reproduction screen on our harness.

    python adapters/simlingo/fail2drive_pairs.py configs/rollout/f2d-repro-screen.yaml PedestriansOnRoad Wall ...

Fail2Drive ships each pair as two single-route files in `fail2drive_split/`: `Base_<name>_<id>.xml` (the in-distribution
twin, id N) and `Generalization_<name>_<1000 + N>.xml` (the same road with the unseen scenario). Each pair becomes one
base: the generalization route is the slice of gap `F2D_<name>` and the base route its neighbourhood, so
`src/harness/efficacy.py` scores it as it scores a planted gap. Routes are copied unchanged; weather comes from the file.
The config's `route.routes_file` and `route.manifest` name the outputs.
"""
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPLIT = ROOT / ".runtime/fail2drive-src/fail2drive_split"
GENERALIZATION_OFFSET = 1000


def pairs(split: Path, name: str) -> list[tuple[Path, Path]]:
    found = []
    for base in sorted(split.glob(f"Base_{name}_*.xml")):
        number = int(re.fullmatch(rf"Base_{name}_(\d+)\.xml", base.name).group(1))
        twin = split / f"Generalization_{name}_{number + GENERALIZATION_OFFSET:04d}.xml"
        if not twin.is_file():
            raise FileNotFoundError(f"{base.name} has no generalization twin {twin.name}")
        found.append((base, twin))
    if not found:
        raise FileNotFoundError(f"no Base_{name}_*.xml in {split}")
    return found


def only_route(path: Path) -> ET.Element:
    routes = list(ET.parse(path).getroot().iter("route"))
    if len(routes) != 1:
        raise ValueError(f"{path} holds {len(routes)} routes, expected 1")
    return routes[0]


def entry(route: ET.Element, base_id: str, name: str, slice_: bool) -> dict:
    scenarios = [s.get("type") for s in route.iter("scenario")]
    return {"id": route.get("id"), "base_id": base_id, "town": route.get("town"),
            "scenario": scenarios[0] if scenarios else None, "role": "pilot_slice" if slice_ else "pilot_neighbourhood",
            "practice_gaps": [f"F2D_{name}"] if slice_ else [], "neighbourhood_of": [] if slice_ else [f"F2D_{name}"],
            "source": "fail2drive"}


def build(names: list[str], split: Path = SPLIT) -> tuple[ET.Element, list[dict]]:
    root, manifest = ET.Element("routes"), []
    for name in names:
        for base_file, twin_file in pairs(split, name):
            base, twin = only_route(base_file), only_route(twin_file)
            base_id = f"f2d-{base.get('id')}"
            for route, slice_ in ((twin, True), (base, False)):
                root.append(route)
                manifest.append(entry(route, base_id, name, slice_))
    ids = [item["id"] for item in manifest]
    if len(ids) != len(set(ids)):
        raise ValueError("route ids repeat across the chosen pairs")
    return root, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("config", type=Path)
    parser.add_argument("names", nargs="+", help="Fail2Drive scenario names, e.g. PedestriansOnRoad")
    args = parser.parse_args()
    route = yaml.safe_load(args.config.read_text())["route"]
    root, manifest = build(args.names)
    ET.indent(root)
    ET.ElementTree(root).write(ROOT / route["routes_file"])
    (ROOT / route["manifest"]).write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"{len(manifest) // 2} pairs, {len(manifest)} routes -> {route['routes_file']}")


if __name__ == "__main__":
    main()
