#!/usr/bin/env python3
"""
Render meta/main.yml from templates/meta_main.yml.j2 using molecule/shared/vars.yml.

Supported input schemas
-----------------------
1) Current role schema (preferred):
   platform_matrix:
     ubuntu: ["26.04", "24.04"]
     debian: ["13", "12"]
     fedora: ["44", "43"]
   images:
     ubuntu: docker.io/library/ubuntu
     debian: docker.io/library/debian
     fedora: registry.fedoraproject.org/fedora

2) Simple fallback schema:
   ubuntu: ["noble", "jammy"]
   debian: ["trixie", "bookworm"]
   fedora: ["44", "43"]

Behavior
--------
- Ubuntu numeric releases are converted to codenames for Galaxy metadata.
- Debian numeric major versions are converted to codenames for Galaxy metadata.
- Fedora versions are kept as strings.
- Unknown Ubuntu/Debian numeric releases raise a clear error rather than silently
  generating incorrect metadata.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

UBUNTU_CODENAME_MAP = {
    "20.04": "focal",
    "22.04": "jammy",
    "24.04": "noble",
    "26.04": "resolute",
}

DEBIAN_CODENAME_MAP = {
    "11": "bullseye",
    "12": "bookworm",
    "13": "trixie",
    "14": "forky",
}

PLATFORM_NAME_MAP = {
    "fedora": "Fedora",
    "ubuntu": "Ubuntu",
    "debian": "Debian",
}

PLATFORM_ORDER = ("fedora", "ubuntu", "debian")


def load_structured_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at top level in {path}")
    return data


def extract_matrix(data: dict[str, Any]) -> dict[str, list[Any]]:
    if "platform_matrix" in data:
        matrix = data["platform_matrix"]
        if not isinstance(matrix, dict):
            raise ValueError("Expected 'platform_matrix' to be a mapping")
        return matrix
    return data


def normalize_versions(platform_key: str, versions: list[Any]) -> list[str]:
    normalized: list[str] = []
    for raw in versions:
        value = str(raw).strip().strip('"').strip("'")
        if not value:
            continue
        if platform_key == "ubuntu":
            if value in UBUNTU_CODENAME_MAP:
                value = UBUNTU_CODENAME_MAP[value]
            else:
                value = value.lower()
                # If it still looks numeric but isn't known, fail fast.
                if value.replace('.', '').isdigit() and value not in UBUNTU_CODENAME_MAP:
                    raise ValueError(f"Unsupported Ubuntu release in metadata renderer: {value}")
        elif platform_key == "debian":
            if value in DEBIAN_CODENAME_MAP:
                value = DEBIAN_CODENAME_MAP[value]
            else:
                value = value.lower()
                if value.isdigit() and value not in DEBIAN_CODENAME_MAP:
                    raise ValueError(f"Unsupported Debian release in metadata renderer: {value}")
        elif platform_key == "fedora":
            value = str(value)
        normalized.append(value)

    seen = set()
    result: list[str] = []
    for v in normalized:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


def matrix_to_platforms(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    platforms: list[dict[str, Any]] = []
    for key in PLATFORM_ORDER:
        versions = matrix.get(key)
        if versions is None:
            continue
        if not isinstance(versions, list):
            raise ValueError(f"Expected list of versions for '{key}', got {type(versions).__name__}")
        items = normalize_versions(key, versions)
        if not items:
            continue
        platforms.append({"name": PLATFORM_NAME_MAP[key], "versions": items})
    if not platforms:
        raise ValueError("No supported platforms found in matrix input")
    return platforms


def render(template_path: Path, output_path: Path, matrix_path: Path) -> None:
    raw = load_structured_file(matrix_path)
    matrix = extract_matrix(raw)
    platforms = matrix_to_platforms(matrix)

    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_path.name)
    content = template.render(
        template_name=template_path.name,
        generated_on=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        platforms=platforms,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content.strip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render meta/main.yml from molecule/shared/vars.yml")
    parser.add_argument(
        "--vars-file",
        default="molecule/shared/vars.yml",
        help="Path to molecule shared vars file (default: molecule/shared/vars.yml)",
    )
    parser.add_argument(
        "--template",
        default="templates/meta_main.yml.j2",
        help="Path to Jinja2 template (default: templates/meta_main.yml.j2)",
    )
    parser.add_argument(
        "--output",
        default="meta/main.yml",
        help="Output file path (default: meta/main.yml)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    render(Path(args.template), Path(args.output), Path(args.vars_file))
