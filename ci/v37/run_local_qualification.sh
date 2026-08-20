#!/usr/bin/env bash
set -euo pipefail

ARCHIVE="${1:-/opt/turbo/TURBO_META_OS_v37_RUNTIME_QUALIFICATION_RC_FULL.zip}"
BACKEND="${2:-auto}"
TIMEOUT_SECONDS="${3:-180}"
EXPECTED_SHA="5f14f0259699472d90735e7d973e30e060f265ae14f7a58ecd419eca972f6faf"

fail() { echo "TURBO_V37_LOCAL_QUALIFICATION_FAIL reason=$1" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "missing_tool:$1"; }

need sha256sum
need unzip
need python3
need make
need qemu-system-x86_64

test -f "$ARCHIVE" || fail "archive_missing:$ARCHIVE"
echo "$EXPECTED_SHA  $ARCHIVE" | sha256sum -c - >/dev/null || fail archive_sha256_mismatch

test -c /dev/kvm || fail dev_kvm_missing
[[ -r /dev/kvm && -w /dev/kvm ]] || fail dev_kvm_not_rw

FLAGS="$(awk -F: '/^(flags|Features)/ {print $2; exit}' /proc/cpuinfo 2>/dev/null || true)"

if [[ "$BACKEND" == auto ]]; then
  if grep -qw vmx <<<"$FLAGS"; then
    BACKEND=intel
  elif grep -qw svm <<<"$FLAGS"; then
    BACKEND=amd
  else
    fail no_vmx_or_svm_cpu_flag
  fi
fi

case "$BACKEND" in
  intel)
    grep -qw vmx <<<"$FLAGS" || fail vmx_flag_missing
    test -r /sys/module/kvm_intel/parameters/nested || fail kvm_intel_nested_status_missing
    grep -Eiq '^(Y|1)$' /sys/module/kvm_intel/parameters/nested || fail kvm_intel_nested_disabled
    MODE=kvm-intel
    BACKEND_MARKER=TURBO_V37_VMX_RUNTIME_AVAILABLE
    ;;
  amd)
    grep -qw svm <<<"$FLAGS" || fail svm_flag_missing
    test -r /sys/module/kvm_amd/parameters/nested || fail kvm_amd_nested_status_missing
    grep -Eiq '^(Y|1)$' /sys/module/kvm_amd/parameters/nested || fail kvm_amd_nested_disabled
    MODE=kvm-amd
    BACKEND_MARKER=TURBO_V37_SVM_RUNTIME_AVAILABLE
    ;;
  *) fail "invalid_backend:$BACKEND" ;;
esac

WORK="${TURBO_V37_WORK:-$(mktemp -d -t turbo-v37-qualify.XXXXXX)}"
KEEP_WORK="${TURBO_V37_KEEP_WORK:-0}"
cleanup() {
  if [[ "$KEEP_WORK" != 1 ]]; then rm -rf "$WORK"; fi
}
trap cleanup EXIT

SRC="$WORK/source"
BUILD="$WORK/build"
STATUS="$WORK/runtime-status.json"
mkdir -p "$SRC" "$BUILD"

unzip -q "$ARCHIVE" -d "$SRC"
ROOT="$(find "$SRC" -mindepth 1 -maxdepth 1 -type d | head -n1)"
test -n "$ROOT" || fail archive_root_missing
cd "$ROOT"
sha256sum -c MANIFEST.sha256 >/dev/null || fail source_manifest_mismatch

echo "TURBO_V37_LOCAL_SOURCE_MANIFEST_PASS backend=$BACKEND root=$ROOT"
qemu-system-x86_64 --version | head -n1

# Prove KVM can actually initialize before spending time rebuilding TURBO.
set +e
timeout 5s qemu-system-x86_64 \
  -machine q35,accel=kvm -cpu host -m 128M -smp 2 \
  -nodefaults -no-user-config -display none -monitor none -serial none -S \
  >/dev/null 2>"$WORK/kvm-preflight.stderr"
KVM_RC=$?
set -e
[[ $KVM_RC -eq 124 ]] || { cat "$WORK/kvm-preflight.stderr" >&2 || true; fail "kvm_initialization_rc:$KVM_RC"; }
echo "TURBO_V37_KVM_INIT_PASS backend=$BACKEND"

export LC_ALL=C LANG=C TZ=UTC PYTHONHASHSEED=0 ZERO_AR_DATE=1 SOURCE_DATE_EPOCH=1700000000

make BUILD="$BUILD" test
make BUILD="$BUILD" sanitize
make BUILD="$BUILD" audit
make BUILD="$BUILD" qemu-loader block-device-image

python3 scripts/runtime_qualify_v37.py \
  --mode "$MODE" \
  --build "$BUILD" \
  --status "$STATUS" \
  --timeout "$TIMEOUT_SECONDS" \
  --skip-build --strict

LOG="$BUILD/runtime-v37-${MODE}.log"
test -f "$LOG" || fail runtime_log_missing
grep -Fq TURBO_V37_LINUX_GUEST_BOOT_PASS "$LOG" || fail linux_boot_marker_missing
grep -Fq TURBO_V37_NATIVE_PLUS_LINUX_BOOT_OBSERVED "$LOG" || fail native_parallel_marker_missing
grep -Fq "$BACKEND_MARKER" "$LOG" || fail backend_runtime_marker_missing

if grep -Eq 'TURBO_(PANIC|EXCEPTION)|TURBO_V37_(VMX|SVM)_ENTRY_FAIL' "$LOG"; then
  fail panic_exception_or_vm_entry_failure_observed
fi

python3 - "$STATUS" <<'PY'
import json, sys
p=sys.argv[1]
d=json.load(open(p, encoding='utf-8'))
assert d.get('result') == 'PASS', d
assert d.get('linux_boot_marker_observed') is True, d
assert d.get('native_parallel_observed') is True, d
print('TURBO_V37_RUNTIME_JSON_PASS')
PY

EVIDENCE_OUT="${TURBO_V37_EVIDENCE_OUT:-$PWD/v37-runtime-evidence-${BACKEND}}"
mkdir -p "$EVIDENCE_OUT"
cp -f "$STATUS" "$EVIDENCE_OUT/runtime-status.json"
cp -f "$LOG" "$EVIDENCE_OUT/runtime.log"
cp -f "$WORK/kvm-preflight.stderr" "$EVIDENCE_OUT/kvm-preflight.stderr"
for f in turbo-kernel.elf turbo-vmm.elf turbo-block-device.img; do
  [[ -f "$BUILD/$f" ]] && cp -f "$BUILD/$f" "$EVIDENCE_OUT/$f"
done
(
  cd "$EVIDENCE_OUT"
  sha256sum ./* > SHA256SUMS
)

echo "TURBO_V37_LOCAL_HARDWARE_RUNTIME_PASS backend=$BACKEND evidence=$EVIDENCE_OUT"
