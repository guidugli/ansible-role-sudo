#!/usr/bin/env python3
import re
import sys
import urllib.request
import yaml
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SHARED_VARS = ROOT / "molecule" / "shared" / "vars.yml"

UBUNTU_RELEASES_URL = "https://www.releases.ubuntu.com/"  # source of release list [3](https://www.releases.ubuntu.com/)
DEBIAN_RELEASES_URL = "https://www.debian.org/releases/"  # stable/oldstable listed [4](https://www.debian.org/releases/)
FEDORA_EOL_URL = "https://endoflife.date/fedora"          # supported releases listed [5](https://endoflife.date/fedora)

def _parse_major_minor(v: str) -> tuple[int, int]:
    """
    Parse versions like '26.04' into (26, 4). Used for Ubuntu ordering checks.
    """
    major, minor = v.split(".")
    return int(major), int(minor)


def sanity_check_matrix(data: dict) -> None:
    """
    Validates the computed matrix before writing vars.yml.

    Guardrails:
      - Each distro must have exactly two versions
      - No duplicates (e.g., '15','15')
      - Ubuntu versions must look like YY.MM and be in descending order (newest first)
      - Debian versions must be numeric majors and stable >= oldstable
      - Fedora versions must be numeric majors and newest >= older
    """
    if not isinstance(data, dict):
        raise RuntimeError(f"Matrix sanity check failed: expected dict, got {type(data)}")

    pm = data.get("platform_matrix")
    images = data.get("images")
    if not isinstance(pm, dict) or not isinstance(images, dict):
        raise RuntimeError("Matrix sanity check failed: missing or invalid 'platform_matrix'/'images' keys")

    required_distros = ("ubuntu", "debian", "fedora")
    for distro in required_distros:
        if distro not in pm:
            raise RuntimeError(f"Matrix sanity check failed: missing distro '{distro}' in platform_matrix")
        if distro not in images:
            raise RuntimeError(f"Matrix sanity check failed: missing distro '{distro}' in images")

        versions = pm[distro]
        if not isinstance(versions, list):
            raise RuntimeError(f"{distro}: expected a list of versions, got {type(versions)}")
        if len(versions) != 2:
            raise RuntimeError(f"{distro}: expected exactly 2 versions, got {versions}")
        if not all(isinstance(v, str) and v.strip() for v in versions):
            raise RuntimeError(f"{distro}: versions must be non-empty strings, got {versions}")
        if versions[0] == versions[1]:
            raise RuntimeError(f"{distro}: duplicate versions detected: {versions}")

    # Ubuntu: LTS-only YY.MM format + descending order (newest first)
    ubuntu = pm["ubuntu"]
    for v in ubuntu:
        if not __import__("re").match(r"^\d{2}\.\d{2}$", v):
            raise RuntimeError(f"ubuntu: expected YY.MM format (e.g., '26.04'), got {v!r}")
    if _parse_major_minor(ubuntu[0]) < _parse_major_minor(ubuntu[1]):
        raise RuntimeError(f"ubuntu: expected descending order (newest first), got {ubuntu}")

    # Debian: stable + oldstable are integer majors, stable >= oldstable
    # Debian releases page explicitly defines stable and oldstable. [1](https://www.debian.org/releases/)
    debian = pm["debian"]
    if not all(v.isdigit() for v in debian):
        raise RuntimeError(f"debian: expected numeric major versions, got {debian}")
    if int(debian[0]) < int(debian[1]):
        raise RuntimeError(f"debian: expected stable >= oldstable, got {debian}")

    # Fedora: numeric majors, newest >= older
    fedora = pm["fedora"]
    if not all(v.isdigit() for v in fedora):
        raise RuntimeError(f"fedora: expected numeric major versions, got {fedora}")
    if int(fedora[0]) < int(fedora[1]):
        raise RuntimeError(f"fedora: expected newest >= older, got {fedora}")

def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

def latest_two_ubuntu_lts(html: str):
    """
    Return the latest two Ubuntu LTS major versions (e.g., 26.04, 24.04).
    Source: Ubuntu Releases page lists LTS entries explicitly. [1](https://www.releases.ubuntu.com/)
    """
    # Capture only entries that explicitly say "LTS"
    # Examples on the page: "Ubuntu 26.04 LTS", "Ubuntu 24.04.4 LTS". [1](https://www.releases.ubuntu.com/)
    matches = re.findall(r"Ubuntu\s+(\d{2}\.\d{2})(?:\.\d+)?\s+LTS", html)

    # De-dup while preserving order as they appear on the page (newest first there typically)
    seen, lts_versions = set(), []
    for v in matches:
        if v not in seen:
            seen.add(v)
            lts_versions.append(v)

    # If the page ordering ever changes, sort numerically descending as a safety net:
    def ver_key(x):
        major, minor = x.split(".")
        return (int(major), int(minor))

    lts_versions = sorted(lts_versions, key=ver_key, reverse=True)
    return lts_versions[:2]

def latest_two_ubuntu(html: str):
    # Match "Ubuntu 26.04 LTS" or "Ubuntu 25.10"
    # releases.ubuntu.com lists these prominently [3](https://www.releases.ubuntu.com/)
    versions = re.findall(r"Ubuntu\s+(\d{2}\.\d{2})(?:\.\d+)?\s*(?:LTS)?", html)
    # Keep unique in order
    seen, out = set(), []
    for v in versions:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out[:2]

def html_to_text(html: str) -> str:
    import re
    # Remove script/style and tags
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    html = re.sub(r"(?s)<.*?>", " ", html)
    # Decode the most common entities used on these pages
    html = html.replace("&mdash;", "-").replace("&nbsp;", " ")
    # Collapse whitespace
    return re.sub(r"\s+", " ", html).strip()

def latest_two_debian(html: str):
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

def latest_two_fedora(html: str):
    # endoflife.date lists supported Fedora releases (e.g., 44, 43) [5](https://endoflife.date/fedora)
    # Grab the first two release numbers in the table.
    versions = re.findall(r">\s*(\d{2})\s*<", html)
    # De-dup while preserving order
    seen, out = set(), []
    for v in versions:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out[:2]

def main():
    ubuntu = latest_two_ubuntu_lts(fetch(UBUNTU_RELEASES_URL))
    debian = latest_two_debian(fetch(DEBIAN_RELEASES_URL))
    fedora = latest_two_fedora(fetch(FEDORA_EOL_URL))

    data = {
        "platform_matrix": {
            "ubuntu": ubuntu,
            "debian": debian,
            "fedora": fedora
        },
        "images": {
            "ubuntu": "docker.io/library/ubuntu",
            "debian": "docker.io/library/debian",
            "fedora": "registry.fedoraproject.org/fedora"
        }
    }

    sanity_check_matrix(data)

    SHARED_VARS.parent.mkdir(parents=True, exist_ok=True)
    SHARED_VARS.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    print(f"Wrote {SHARED_VARS}")

    # Regenerate inventory files for scenarios
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "render_inventory.py")])

if __name__ == "__main__":
    main()
