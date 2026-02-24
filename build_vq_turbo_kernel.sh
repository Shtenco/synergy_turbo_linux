#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/linux-5.15-source [--llvm] [--dry-run]"
  exit 1
fi

KDIR="$1"
shift || true
USE_LLVM=0
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
    --llvm) USE_LLVM=1 ;;
    --dry-run) DRY_RUN=1 ;;
    *) echo "Unknown flag: $arg"; exit 1 ;;
  esac
done

PATCH_FILE="$(cd "$(dirname "$0")" && pwd)/virtual_qubit_turbo_5.15.patch"

[[ -d "$KDIR" ]] || { echo "Kernel dir not found: $KDIR"; exit 1; }
[[ -f "$PATCH_FILE" ]] || { echo "Patch file not found: $PATCH_FILE"; exit 1; }

pushd "$KDIR" >/dev/null

if [[ ! -f Makefile ]]; then
  echo "No kernel Makefile in $KDIR"
  exit 1
fi

if [[ $DRY_RUN -eq 1 ]]; then
  patch --dry-run -p1 < "$PATCH_FILE"
  echo "Dry-run OK"
  popd >/dev/null
  exit 0
fi

patch -p1 < "$PATCH_FILE"
cp "/boot/config-$(uname -r)" .config
yes "" | make olddefconfig
scripts/config --enable CONFIG_SCHED_VQ_TURBO || true

BUILD_ARGS=(-j"$(nproc)")
if [[ $USE_LLVM -eq 1 ]]; then
  BUILD_ARGS+=(LLVM=1 LLVM_IAS=1)
fi

make "${BUILD_ARGS[@]}"
make "${BUILD_ARGS[@]}" modules
sudo make modules_install
sudo make install
sudo update-grub

popd >/dev/null

echo "Done. Reboot into new kernel and tune with sysctl kernel.vq_*"
