#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/linux-5.15-source"
  exit 1
fi

KDIR="$1"
PATCH_FILE="$(cd "$(dirname "$0")" && pwd)/virtual_qubit_turbo_5.15.patch"

if [[ ! -d "$KDIR" ]]; then
  echo "Kernel dir not found: $KDIR"
  exit 1
fi
if [[ ! -f "$PATCH_FILE" ]]; then
  echo "Patch file not found: $PATCH_FILE"
  exit 1
fi

pushd "$KDIR" >/dev/null
patch -p1 < "$PATCH_FILE"
cp /boot/config-$(uname -r) .config
yes "" | make oldconfig
scripts/config --enable CONFIG_SCHED_VQ_TURBO || true
make -j"$(nproc)"
make -j"$(nproc)" modules
sudo make modules_install
sudo make install
sudo update-grub
popd >/dev/null

echo "Done. Reboot to use the new kernel."
