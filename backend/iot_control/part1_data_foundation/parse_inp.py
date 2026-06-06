from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


ADDED_NODE_IDS = {"G71F320", "G_ADD"}
ADDED_PUMP_IDS = {"G71F320Pp1"}
ADDED_FACILITY_IDS = {"G_ADD"}


@dataclass
class InpModel:
    path: Path
    sections: dict[str, list[list[str]]]


def _tokens(line: str) -> list[str]:
    content = line.split(";", 1)[0].strip()
    if not content:
        return []
    return shlex.split(content)


def parse_inp_file(path: str | Path) -> InpModel:
    path = Path(path)
    sections: dict[str, list[list[str]]] = {}
    current: str | None = None
    section_pattern = re.compile(r"^\s*\[([^\]]+)\]\s*$")

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            match = section_pattern.match(line)
            if match:
                current = match.group(1).upper()
                sections.setdefault(current, [])
                continue
            if current is None or line.startswith(";"):
                continue
            parts = _tokens(raw_line)
            if parts:
                sections[current].append(parts)
    return InpModel(path=path, sections=sections)


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _cell(value: Any) -> Any:
    return "" if value is None else value


def _rows(section: list[list[str]], width: int) -> list[list[str]]:
    return [row + [""] * max(0, width - len(row)) for row in section]


def pump_station_id(pump_id: str) -> str:
    station = re.sub(r"(?:P?p\d+|p\d+)$", "", pump_id, flags=re.IGNORECASE)
    return station or pump_id


def _version_fields(object_id: str, added_ids: set[str]) -> dict[str, Any]:
    is_added = object_id in added_ids
    return {"model_version": "v2" if is_added else "original", "is_added": 1 if is_added else 0}


def _curve_points(rows: list[list[str]]) -> dict[str, list[list[str]]]:
    curves: dict[str, list[list[str]]] = {}
    for row in rows:
        if len(row) >= 3:
            curve_id = row[0]
            point = row[-2:]
            curves.setdefault(curve_id, []).append(point)
    return curves


def build_static_tables(model: InpModel) -> dict[str, pd.DataFrame]:
    sections = model.sections
    pumps = _rows(sections.get("PUMPS", []), 7)
    pump_inlets = {row[1] for row in pumps if len(row) > 1}
    pump_outlets = {row[2] for row in pumps if len(row) > 2}

    coord_map = {row[0]: row[1:3] for row in _rows(sections.get("COORDINATES", []), 3)}
    nodes: list[dict[str, Any]] = []

    for row in _rows(sections.get("JUNCTIONS", []), 6):
        node_id = row[0]
        coords = coord_map.get(node_id, ["", ""])
        nodes.append(
            {
                "node_id": node_id,
                "node_type": "junction",
                "invert_elevation": _cell(_float(row[1])),
                "max_depth": _cell(_float(row[2])),
                "initial_depth": _cell(_float(row[3])),
                "surcharge_depth": _cell(_float(row[4])),
                "ponded_area": _cell(_float(row[5])),
                "x_coord": _cell(_float(coords[0])),
                "y_coord": _cell(_float(coords[1])),
                "is_storage": False,
                "is_outfall": False,
                "is_pump_station_forebay": node_id in pump_inlets,
                **_version_fields(node_id, ADDED_NODE_IDS),
            }
        )

    for row in _rows(sections.get("STORAGE", []), 8):
        node_id = row[0]
        coords = coord_map.get(node_id, ["", ""])
        nodes.append(
            {
                "node_id": node_id,
                "node_type": "storage",
                "invert_elevation": _cell(_float(row[1])),
                "max_depth": _cell(_float(row[2])),
                "initial_depth": _cell(_float(row[3])),
                "surcharge_depth": "",
                "ponded_area": _cell(_float(row[7] if len(row) > 7 else "")),
                "x_coord": _cell(_float(coords[0])),
                "y_coord": _cell(_float(coords[1])),
                "is_storage": True,
                "is_outfall": False,
                "is_pump_station_forebay": node_id in pump_inlets,
                **_version_fields(node_id, ADDED_NODE_IDS),
            }
        )

    for row in _rows(sections.get("OUTFALLS", []), 3):
        node_id = row[0]
        coords = coord_map.get(node_id, ["", ""])
        nodes.append(
            {
                "node_id": node_id,
                "node_type": "outfall",
                "invert_elevation": _cell(_float(row[1])),
                "max_depth": "",
                "initial_depth": "",
                "surcharge_depth": "",
                "ponded_area": "",
                "x_coord": _cell(_float(coords[0])),
                "y_coord": _cell(_float(coords[1])),
                "is_storage": False,
                "is_outfall": True,
                "is_pump_station_forebay": node_id in pump_inlets,
                **_version_fields(node_id, ADDED_NODE_IDS),
            }
        )

    node_info = pd.DataFrame(nodes)
    node_lookup = {row["node_id"]: row for row in nodes}
    xsections = {row[0]: row for row in _rows(sections.get("XSECTIONS", []), 7)}
    losses = {row[0]: row for row in _rows(sections.get("LOSSES", []), 4)}

    conduits: list[dict[str, Any]] = []
    for row in _rows(sections.get("CONDUITS", []), 8):
        link_id, inlet, outlet = row[0], row[1], row[2]
        length = _float(row[3])
        inlet_offset = _float(row[5]) or 0.0
        outlet_offset = _float(row[6]) or 0.0
        inlet_invert = _float(node_lookup.get(inlet, {}).get("invert_elevation"))
        outlet_invert = _float(node_lookup.get(outlet, {}).get("invert_elevation"))
        slope = ""
        if length and inlet_invert is not None and outlet_invert is not None:
            slope = (inlet_invert + inlet_offset - outlet_invert - outlet_offset) / length
        xs = xsections.get(link_id, ["", "", "", "", "", "", ""])
        loss = losses.get(link_id, ["", "", "", ""])
        conduits.append(
            {
                "link_id": link_id,
                "link_type": "conduit",
                "inlet_node": inlet,
                "outlet_node": outlet,
                "length": _cell(length),
                "roughness": _cell(_float(row[4])),
                "shape": xs[1],
                "max_depth_or_diameter": _cell(_float(xs[2])),
                "inlet_offset": _cell(inlet_offset),
                "outlet_offset": _cell(outlet_offset),
                "slope": _cell(slope),
                "minor_loss_inlet": _cell(_float(loss[1])),
                "minor_loss_outlet": _cell(_float(loss[2])),
                "minor_loss_average": _cell(_float(loss[3])),
                **_version_fields(link_id, set()),
            }
        )

    curve_points = _curve_points(sections.get("CURVES", []))
    pump_counts: dict[str, int] = {}
    for row in pumps:
        pump_counts[pump_station_id(row[0])] = pump_counts.get(pump_station_id(row[0]), 0) + 1

    pump_info = pd.DataFrame(
        [
            {
                "pump_id": row[0],
                "pump_station_id": pump_station_id(row[0]),
                "inlet_node": row[1],
                "outlet_node": row[2],
                "pump_curve": row[3],
                "initial_status": row[4],
                "startup_depth": _cell(_float(row[5])),
                "shutoff_depth": _cell(_float(row[6])),
                "is_parallel_pump": pump_counts.get(pump_station_id(row[0]), 0) > 1,
                "curve_points": json.dumps(curve_points.get(row[3], []), ensure_ascii=False),
                **_version_fields(row[0], ADDED_PUMP_IDS),
            }
            for row in pumps
        ]
    )

    facilities: list[dict[str, Any]] = []
    for section_name, facility_type in [("ORIFICES", "orifice"), ("WEIRS", "weir"), ("OUTLETS", "outlet")]:
        for row in _rows(sections.get(section_name, []), 7):
            facilities.append(
                {
                    "facility_id": row[0],
                    "facility_type": facility_type,
                    "inlet_node": row[1],
                    "outlet_node": row[2],
                    "crest_height": _cell(_float(row[4] if facility_type == "orifice" else row[4])),
                    "discharge_coefficient": _cell(_float(row[5] if len(row) > 5 else "")),
                    "initial_setting": "",
                    "curve_or_rating": row[6] if len(row) > 6 else "",
                    **_version_fields(row[0], ADDED_FACILITY_IDS),
                }
            )
    for row in _rows(sections.get("OUTFALLS", []), 3):
        facilities.append(
            {
                "facility_id": row[0],
                "facility_type": "outfall",
                "inlet_node": row[0],
                "outlet_node": "",
                "crest_height": _cell(_float(row[1])),
                "discharge_coefficient": "",
                "initial_setting": "",
                "curve_or_rating": row[2],
                **_version_fields(row[0], ADDED_FACILITY_IDS),
            }
        )

    subareas = {row[0]: row for row in _rows(sections.get("SUBAREAS", []), 7)}
    infiltrations = {row[0]: row for row in _rows(sections.get("INFILTRATION", []), 6)}
    polygons: dict[str, list[list[str]]] = {}
    for row in _rows(sections.get("POLYGONS", []), 3):
        polygons.setdefault(row[0], []).append(row[1:3])

    subcatchments = []
    for row in _rows(sections.get("SUBCATCHMENTS", []), 9):
        sub_id = row[0]
        subcatchments.append(
            {
                "subcatchment_id": sub_id,
                "rain_gage_id": row[1],
                "outlet_node": row[2],
                "area": _cell(_float(row[3])),
                "impervious_percent": _cell(_float(row[4])),
                "width": _cell(_float(row[5])),
                "slope": _cell(_float(row[6])),
                "curb_length": _cell(_float(row[7])),
                "snow_pack": row[8],
                "polygon_points": json.dumps(polygons.get(sub_id, []), ensure_ascii=False),
                "subarea_params": json.dumps(subareas.get(sub_id, []), ensure_ascii=False),
                "infiltration_params": json.dumps(infiltrations.get(sub_id, []), ensure_ascii=False),
                **_version_fields(sub_id, set()),
            }
        )

    return {
        "node_info": node_info,
        "conduit_info": pd.DataFrame(conduits),
        "pump_info": pump_info,
        "facility_info": pd.DataFrame(facilities),
        "subcatchment_info": pd.DataFrame(subcatchments),
    }
