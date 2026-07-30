#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

make clean all test
mkdir -p results
{
  echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "uname=$(uname -a)"
  echo "compiler=$(${CC:-gcc} --version | head -n1)"
  if [[ -r /proc/cpuinfo ]]; then
    echo "cpu=$(awk -F: '/model name/ {sub(/^[ \t]+/, "", $2); print $2; exit}' /proc/cpuinfo)"
  fi
} > results/environment.txt

./build/turbo-bench-baseline --json | tee results/baseline.json
./build/turbo-bench-native --json | tee results/native.json

printf '\nSaved reproducible benchmark metadata and JSON under %s/results\n' "$ROOT_DIR"
