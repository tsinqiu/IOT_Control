from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class AssessmentConfig:
    project_root: Path
    input_csv_dir: Path
    output_csv_dir: Path
    report_step_min: int
    min_flow_cms: float
    min_interval_volume_m3: float


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def load_config(path: str | Path | None = None) -> AssessmentConfig:
    root = PROJECT_ROOT
    config_path = Path(path) if path else root / "config" / "part2_status_assessment.yaml"
    data: dict[str, Any] = {}
    if config_path.exists():
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    paths = data.get("paths", {})
    assessment = data.get("assessment", {})
    return AssessmentConfig(
        project_root=root,
        input_csv_dir=_resolve(root, paths.get("input_csv_dir", "data/processed/part1_csv")),
        output_csv_dir=_resolve(root, paths.get("output_csv_dir", "data/processed/part2_assessment_csv")),
        report_step_min=int(assessment.get("report_step_min", 15)),
        min_flow_cms=float(assessment.get("min_flow_cms", 0.001)),
        min_interval_volume_m3=float(assessment.get("min_interval_volume_m3", 1.0)),
    )


def ensure_directories(config: AssessmentConfig) -> None:
    config.output_csv_dir.mkdir(parents=True, exist_ok=True)
