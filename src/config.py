from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "configs" / "default.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or DEFAULT_CONFIG_PATH
    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_path(config: dict[str, Any], key: str) -> Path:
    return (REPO_ROOT / config["paths"][key]).resolve()


def resolve_eval_runs_dir(config: dict[str, Any]) -> Path:
    raw = str(config.get("eval", {}).get("output_dir", "data/eval/runs"))
    p = Path(raw)
    if p.is_absolute():
        return p
    return (REPO_ROOT / raw).resolve()
