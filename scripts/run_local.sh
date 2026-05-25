#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
ansible-galaxy collection install -r requirements.yml

# Update matrix + regenerate inventories
python3 scripts/update_matrix.py

# Run default fast tests
molecule test -s default

# Optional systemd scenario
molecule test -s systemd
