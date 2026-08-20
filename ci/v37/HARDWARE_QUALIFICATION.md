# TURBO META OS v37 — hardware runtime qualification

This directory defines the fail-closed boundary for the first real nested Linux boot on Intel VMX/EPT and AMD SVM/NPT.

## Exact input

The self-hosted runner or local qualification host must contain the exact FULL v37 archive:

`/opt/turbo/TURBO_META_OS_v37_RUNTIME_QUALIFICATION_RC_FULL.zip`

Required SHA-256:

`5f14f0259699472d90735e7d973e30e060f265ae14f7a58ecd419eca972f6faf`

Before any build or VM entry, `run_local_qualification.sh` verifies both this outer SHA and the archive's `MANIFEST.sha256`.

## One-command local qualification

From a checkout of this PR branch on the hardware host:

```bash
bash ci/v37/run_local_qualification.sh \
  /opt/turbo/TURBO_META_OS_v37_RUNTIME_QUALIFICATION_RC_FULL.zip \
  auto 180
```

`auto` selects Intel when `vmx` is exposed and AMD when `svm` is exposed. Explicit backends are `intel` and `amd`.

The script performs, in order:

1. exact archive SHA verification;
2. `/dev/kvm` read/write and CPU virtualization preflight;
3. nested virtualization verification;
4. bounded QEMU/KVM initialization smoke test;
5. full source `MANIFEST.sha256` verification;
6. deterministic `make test`;
7. ASan/UBSan `make sanitize`;
8. hardened `make audit`;
9. fresh qemu-loader/block-device build;
10. strict `runtime_qualify_v37.py` hardware run;
11. serial marker and negative-failure-marker validation;
12. machine-readable evidence + `SHA256SUMS` export.

Default evidence directories are `v37-runtime-evidence-intel/` or `v37-runtime-evidence-amd/` next to the caller's checkout. Override with `TURBO_V37_EVIDENCE_OUT`.

## GitHub self-hosted runner labels

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

The GitHub workflow calls the same local qualification script, so local and Actions semantics cannot silently diverge.

## Intel requirements

- Linux x86-64 host;
- `/dev/kvm` character device, readable/writable by the runner account;
- CPU exposes `vmx`;
- `kvm_intel` loaded;
- `/sys/module/kvm_intel/parameters/nested` is `Y` or `1`;
- `qemu-system-x86_64`, `make`, `python3`, `unzip`, `sha256sum`, and `timeout` available.

PASS additionally requires the real runtime markers:

- `TURBO_V37_LINUX_GUEST_BOOT_PASS`
- `TURBO_V37_NATIVE_PLUS_LINUX_BOOT_OBSERVED`
- `TURBO_V37_VMX_EPT_AVAILABLE`

## AMD requirements

- Linux x86-64 host;
- `/dev/kvm` character device, readable/writable by the runner account;
- CPU exposes `svm`;
- `kvm_amd` loaded;
- `/sys/module/kvm_amd/parameters/nested` is `Y` or `1`;
- the same toolchain requirements as Intel.

PASS additionally requires:

- `TURBO_V37_LINUX_GUEST_BOOT_PASS`
- `TURBO_V37_NATIVE_PLUS_LINUX_BOOT_OBSERVED`
- `TURBO_V37_SVM_NPT_AVAILABLE`

## Negative evidence is fatal

Any `[TURBO PANIC]`, `[TURBO EXCEPTION]`, VMX/SVM entry failure, missing marker, KVM initialization failure, stale source manifest, incorrect archive SHA, disabled nested virtualization, or runtime JSON result other than `PASS` terminates qualification.

Build success alone is never runtime success.

## Hosted GitHub Actions status

On 2026-08-21 the repository's `ubuntu-latest` and `ubuntu-24.04` jobs were rechecked. Even a one-step `echo` smoke workflow failed before its first step was allocated (`steps=[]`). The QEMU environment probe behaves identically. Therefore this is currently a GitHub-hosted runner/account allocation boundary, not a TURBO or QEMU runtime failure.

Those hosted probe workflows are now `workflow_dispatch` only so this external outage does not create red checks on every PR commit. Once hosted allocation is restored, they can be run manually to qualify QEMU-TCG and discover whether `/dev/kvm`/nested virtualization are exposed.

Nested Intel/AMD proof remains deliberately assigned to labeled self-hosted hardware unless a hosted runner explicitly proves equivalent KVM/nested capabilities.
