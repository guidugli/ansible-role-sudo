#!/usr/bin/env bash
set -euo pipefail
host="${1:-ubuntu2404}"
podman exec -it "$host" /bin/bash 2>/dev/null || podman exec -it "$host" sh
