# TURBO META OS v37 — hardware runtime qualification

This directory documents the fail-closed GitHub Actions boundary for the first real nested Linux boot.

## Exact input

The self-hosted runner must contain the exact FULL v37 archive at:

`/opt/turbo/TURBO_META_OS_v37_RUNTIME_QUALIFICATION_RC_FULL.zip`

Required SHA-256:

`5f14f0259699472d90735e7d973e30e060f265ae14f7a58ecd419eca972f6faf`

The workflow verifies this SHA before extraction and then verifies the archive's `MANIFEST.sha256` before building anything.

## Runner labels

Intel runner:

- `self-hosted`
- `linux`
- `x64`
- `turbo-intel`

AMD runner:

- `self-hosted`
- `linux`
- `x64`
- `turbo-amd`

## Intel requirements

- `/dev/kvm` is a character device.
- host CPU exposes `vmx`.
- `/sys/module/kvm_intel/parameters/nested` is `Y` or `1`.
- `qemu-system-x86_64` is installed.

The job uses `scripts/runtime_qualify_v37.py --mode kvm-intel --strict` and cannot PASS unless all of the following are observed:

- `TURBO_V37_LINUX_GUEST_BOOT_PASS`
- `TURBO_V37_NATIVE_PLUS_LINUX_BOOT_OBSERVED`
- Intel VMX/EPT availability marker
- no TURBO panic/exception/VM-entry-failure marker

## AMD requirements

- `/dev/kvm` is a character device.
- host CPU exposes `svm`.
- `/sys/module/kvm_amd/parameters/nested` is `Y` or `1`.
- `qemu-system-x86_64` is installed.

The job uses `scripts/runtime_qualify_v37.py --mode kvm-amd --strict` and has the same Linux/native marker requirements plus the AMD SVM/NPT availability marker.

## Why hosted GitHub Actions is separate

The repository's `ubuntu-latest`/`ubuntu-24.04` jobs currently fail before their first step is allocated. A one-line `echo` smoke test reproduces the same zero-step failure, so this is currently a runner/account allocation boundary rather than a TURBO/QEMU failure.

When hosted Actions allocation is restored, the hosted job should be used for QEMU-TCG native qualification. Nested VMX/SVM qualification remains deliberately separate and belongs on labeled physical/self-hosted runners unless the hosted runner explicitly exposes `/dev/kvm` plus nested virtualization.

## PASS semantics

Build success is not runtime success. A hardware job is PASS only when the runtime JSON reports `result=PASS`, `linux_boot_marker_observed=true`, and `native_parallel_observed=true`.

A missing runner, missing KVM, disabled nested virtualization, missing marker, unknown VM-exit, entry failure, or guest panic must never be converted to PASS.
