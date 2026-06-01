#!/usr/bin/env python3
"""Render meta/main.yml from templates/meta_main.yml.j2."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]

UBUNTU_CODENAME_MAP = {
    '20.04': 'focal',
    '22.04': 'jammy',
    '24.04': 'noble',
    '26.04': 'resolute',
}

DEBIAN_CODENAME_MAP = {
    '11': 'bullseye',
    '12': 'bookworm',
    '13': 'trixie',
    '14': 'forky',
}

PLATFORM_NAME_MAP = {
    'fedora': 'Fedora',
    'ubuntu': 'Ubuntu',
    'debian': 'Debian',
}

PLATFORM_ORDER = ('fedora', 'ubuntu', 'debian')

# Set to True only if Galaxy / ansible-lint metadata validation lags behind
# newer Fedora releases and rejects valid Fedora version strings.
RENDER_FEDORA_AS_ALL = True


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'Expected top-level mapping in {path}')
    return data


def extract_matrix(data: dict[str, Any]) -> dict[str, Any]:
    matrix = data.get('platform_matrix', data)
    if not isinstance(matrix, dict):
        raise ValueError("Expected 'platform_matrix' to be a mapping")
    return matrix


def normalize_versions(platform_key: str, versions: list[Any]) -> list[str]:
    normalized: list[str] = []

    if platform_key == 'fedora' and RENDER_FEDORA_AS_ALL:
        return ['all']

    for raw in versions:
        value = str(raw).strip().strip('"').strip("'")
        if not value:
            continue

        if platform_key == 'ubuntu':
            if value in UBUNTU_CODENAME_MAP:
                normalized.append(UBUNTU_CODENAME_MAP[value])
            elif value.replace('.', '').isdigit():
                raise ValueError(
                    f'Unsupported Ubuntu release in metadata renderer: {value}'
                )
            else:
                normalized.append(value.lower())

        elif platform_key == 'debian':
            if value in DEBIAN_CODENAME_MAP:
                normalized.append(DEBIAN_CODENAME_MAP[value])
            elif value.isdigit():
                raise ValueError(
                    f'Unsupported Debian release in metadata renderer: {value}'
                )
            else:
                normalized.append(value.lower())

        else:
            normalized.append(value)

    return normalized


def matrix_to_platforms(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    platforms: list[dict[str, Any]] = []

    for key in PLATFORM_ORDER:
        versions = matrix.get(key)
        if versions is None:
            continue

        if not isinstance(versions, list):
            raise ValueError(
                f"Expected list of versions for '{key}', got {type(versions).__name__}"
            )

        rendered_versions = normalize_versions(key, versions)
        if not rendered_versions:
            continue

        platforms.append(
            {
                'name': PLATFORM_NAME_MAP[key],
                'versions': rendered_versions,
            }
        )

    if not platforms:
        raise ValueError('No supported platforms found in matrix input')

    return platforms


def render(template_path: Path, output_path: Path, vars_path: Path) -> None:
    vars_data = load_yaml(vars_path)
    matrix = extract_matrix(vars_data)
    platforms = matrix_to_platforms(matrix)

    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template(template_path.name)
    rendered = template.render(
        template_name=template_path.name,
        platforms=platforms,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered.rstrip() + '\n', encoding='utf-8')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Render meta/main.yml from molecule/shared/vars.yml'
    )
    parser.add_argument(
        '--vars-file',
        default='molecule/shared/vars.yml',
        help='Path to shared vars file (default: molecule/shared/vars.yml)',
    )
    parser.add_argument(
        '--template',
        default='templates/meta_main.yml.j2',
        help='Path to metadata template (default: templates/meta_main.yml.j2)',
    )
    parser.add_argument(
        '--output',
        default='meta/main.yml',
        help='Output path (default: meta/main.yml)',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    render(ROOT / args.template, ROOT / args.output, ROOT / args.vars_file)


if __name__ == '__main__':
    main()
