#!/usr/bin/env python3
"""
Update molecule/shared/vars.yml with the current supported platform matrix.

This script writes YAML in a yamllint-friendly style:
- explicit document start (---)
- block style maps/lists
- indented sequences under mappings
"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SHARED_VARS = ROOT / "molecule" / "shared" / "vars.yml"

UBUNTU_RELEASES_URL = "https://www.releases.ubuntu.com/"
DEBIAN_RELEASES_URL = "https://www.debian.org/releases/"
FEDORA_EOL_URL = "https://endoflife.date/fedora"

DEFAULT_IMAGES = {
    "ubuntu": "docker.io/library/ubuntu",
    "debian": "docker.io/library/debian",
    "fedora": "registry.fedoraproject.org/fedora",
}


class IndentSafeDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def latest_two_ubuntu_lts(html: str) -> list[str]:
    matches = re.findall(r"Ubuntu\s+(\d{2}\.\d{2})(?:\.\d+)?\s+LTS", html)
    seen: list[str] = []
    for value in matches:
        if value not in seen:
            seen.append(value)
    return seen[:2]


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", html)
    html = re.sub(r"(?s)<.*?>", " ", html)
    html = html.replace("&nbsp;", " ").replace("&ndash;", "-")
    return re.sub(r"\s+", " ", html).strip()


def latest_two_debian(html: str) -> list[str]:
    """
    Return [stable, oldstable] from Debian releases page.

    Debian's 'Index of releases' table contains rows whose Status cell includes:
      - 'Current <q>stable</q> release'
      - 'Current <q>oldstable</q> release'
    [1](https://www.debian.org/releases/)
    """
    import re

    # Extract each table row separately so we never match across rows.
    rows = re.findall(r"(?is)<tr>\s*(.*?)\s*</tr>", html)

    stable = None
    oldstable = None

    for row in rows:
        # Find the first <td>...</td> which is the version for that row.
        m_ver = re.search(r"(?is)<td>\s*([0-9]+(?:\.[0-9]+)?)\s*</td>", row)
        if not m_ver:
            continue
        ver = m_ver.group(1)

        # Look for the status markers inside THIS row only
        if re.search(r"(?is)Current\s*<q>\s*stable\s*</q>\s*release", row):
            stable = ver

        if re.search(r"(?is)Current\s*<q>\s*oldstable\s*</q>\s*release", row):
            oldstable = ver

    if not stable or not oldstable:
        raise RuntimeError(
            "Unable to parse Debian stable/oldstable from debian.org/releases "
            f"(stable={stable!r}, oldstable={oldstable!r})."
        )

    return [stable, oldstable]

def latest_two_fedora(html: str) -> list[str]:
    versions = re.findall(r">\s*(\d{2})\s*<", html)
    seen: list[str] = []
    for value in versions:
        if value not in seen:
            seen.append(value)
    return seen[:2]


def _parse_major_minor(value: str) -> tuple[int, int]:
    major, minor = value.split(".")
    return int(major), int(minor)


def sanity_check_matrix(data: dict[str, Any]) -> None:
    for key in ("ubuntu", "debian", "fedora"):
        if key not in data["platform_matrix"]:
            raise ValueError(f"Missing platform key in matrix: {key}")

    ubuntu = data["platform_matrix"]["ubuntu"]
    if len(ubuntu) != 2:
        raise ValueError(f"Expected exactly two Ubuntu versions, got: {ubuntu}")
    if _parse_major_minor(ubuntu[0]) <= _parse_major_minor(ubuntu[1]):
        raise ValueError(f"Ubuntu versions are not ordered newest->older: {ubuntu}")

    debian = data["platform_matrix"]["debian"]
    if len(debian) != 2 or not all(item.isdigit() for item in debian):
        raise ValueError(f"Unexpected Debian version list: {debian}")
    if int(debian[0]) <= int(debian[1]):
        raise ValueError(f"Debian versions are not ordered newest->older: {debian}")

    fedora = data["platform_matrix"]["fedora"]
    if len(fedora) != 2 or not all(item.isdigit() for item in fedora):
        raise ValueError(f"Unexpected Fedora version list: {fedora}")
    if int(fedora[0]) <= int(fedora[1]):
        raise ValueError(f"Fedora versions are not ordered newest->older: {fedora}")


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.dump(
        data,
        Dumper=IndentSafeDumper,
        sort_keys=False,
        default_flow_style=False,
        explicit_start=True,
        indent=4,
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    ubuntu = latest_two_ubuntu_lts(fetch(UBUNTU_RELEASES_URL))
    debian = latest_two_debian(fetch(DEBIAN_RELEASES_URL))
    fedora = latest_two_fedora(fetch(FEDORA_EOL_URL))

    data = {
        "platform_matrix": {
            "ubuntu": ubuntu,
            "debian": debian,
            "fedora": fedora,
        },
        "images": DEFAULT_IMAGES,
    }

    sanity_check_matrix(data)
    write_yaml(SHARED_VARS, data)
    print(f"Wrote {SHARED_VARS}")


if __name__ == "__main__":
    main()
