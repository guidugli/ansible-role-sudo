#!/usr/bin/env python3
"""Render Molecule inventories from molecule/shared/vars.yml."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
VARS_FILE = ROOT / 'molecule' / 'shared' / 'vars.yml'
SCENARIOS = ('default', 'systemd')


def load_vars(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'Expected top-level mapping in {path}')
    return data


def build_inventory(data: dict[str, Any]) -> dict[str, Any]:
    matrix = data.get('platform_matrix', {})
    images = data.get('images', {})
    if not isinstance(matrix, dict) or not isinstance(images, dict):
        raise ValueError('platform_matrix and images must both be mappings')

    hosts: dict[str, Any] = {}
    for distro, versions in matrix.items():
        if not isinstance(versions, list):
            raise ValueError(f'Expected list of versions for {distro}')
        if distro not in images:
            raise ValueError(f'Missing image mapping for distro {distro}')

        for version in versions:
            version_str = str(version)
            host_name = f"{distro}{version_str.replace('.', '')}"
            hosts[host_name] = {
                'ansible_connection': 'containers.podman.podman',
                'container_image': f"{images[distro]}:{version_str}",
                'container_command': 'sleep 1d',
            }

    return {'all': {'children': {'molecule': {'hosts': hosts}}}}


def dump_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(
        data,
        sort_keys=False,
        default_flow_style=False,
        explicit_start=True,
    )


def main() -> None:
    inventory = build_inventory(load_vars(VARS_FILE))
    rendered = dump_yaml(inventory)

    for scenario in SCENARIOS:
        out_file = ROOT / 'molecule' / scenario / 'inventory' / 'hosts.yml'
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(rendered, encoding='utf-8')
        print(f'Wrote {out_file}')


if __name__ == '__main__':
    main()
