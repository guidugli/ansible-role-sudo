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
    text = html_to_text(html).lower()
    stable = re.search(r"stable[^\d]*(\d+)", text)
    oldstable = re.search(r"oldstable[^\d]*(\d+)", text)
    result: list[str] = []
    if stable:
        result.append(stable.group(1))
    if oldstable:
        result.append(oldstable.group(1))
    if len(result) < 2:
        for value in re.findall(r"\b(\d{2})\b", text):
            if value not in result:
                result.append(value)
            if len(result) == 2:
                break
    return result[:2]


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
