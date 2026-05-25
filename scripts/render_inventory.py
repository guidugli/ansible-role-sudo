#!/usr/bin/env python3
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
VARS = ROOT / "molecule" / "shared" / "vars.yml"

SCENARIOS = ["default", "systemd"]

def host_block(name, image, version):
    return {
        name: {
            "ansible_connection": "containers.podman.podman",
            "container_image": f"{image}:{version}",
            "container_command": "sleep 1d",
        }
    }

def main():
    cfg = yaml.safe_load(VARS.read_text(encoding="utf-8"))
    matrix = cfg["platform_matrix"]
    images = cfg["images"]

    hosts = {}
    for distro, versions in matrix.items():
        for v in versions:
            hn = f"{distro}{v.replace('.','')}"
            hosts.update(host_block(hn, images[distro], v))

    inventory = {
        "all": {
            "children": {
                "molecule": {
                    "hosts": hosts
                }
            }
        }
    }

    for sc in SCENARIOS:
        out = ROOT / "molecule" / sc / "inventory" / "hosts.yml"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml.safe_dump(inventory, sort_keys=False), encoding="utf-8")
        print(f"Wrote {out}")

if __name__ == "__main__":
    main()
