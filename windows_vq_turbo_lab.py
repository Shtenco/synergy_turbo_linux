#!/usr/bin/env python3
"""
Windows 10/11 orchestrator:
1) runs baseline benchmark on host Windows,
2) provisions Ubuntu in WSL2 (or optionally Hyper-V stub flow),
3) installs patch-kit dependencies in guest,
4) runs the same benchmark in guest,
5) reports performance delta in percent.

Run this script in elevated PowerShell/CMD with Python 3.10+.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple


BENCHMARK_PY = r'''
import hashlib
import json
import time


def cpu_bench(rounds=6, blocks=7000, block_size=4096):
    timings = []
    payload = (b"vq_turbo" * ((block_size // 8) + 1))[:block_size]
    for _ in range(rounds):
        t0 = time.perf_counter()
        h = hashlib.sha256()
        for i in range(blocks):
            h.update(payload)
            h.update(i.to_bytes(8, "little", signed=False))
        h.digest()
        timings.append(time.perf_counter() - t0)
    timings.sort()
    # robust metric: median
    median_s = timings[len(timings) // 2]
    throughput_mb_s = (blocks * block_size / (1024 * 1024)) / median_s
    return {
        "rounds": rounds,
        "blocks": blocks,
        "block_size": block_size,
        "median_seconds": median_s,
        "throughput_mb_s": throughput_mb_s,
        "all_seconds": timings,
    }


if __name__ == "__main__":
    print(json.dumps(cpu_bench(), ensure_ascii=False))
'''


@dataclass
class BenchResult:
    name: str
    throughput_mb_s: float
    median_seconds: float
    raw_json: dict


@dataclass
class FinalReport:
    mode: str
    baseline: BenchResult
    guest: BenchResult
    percent_delta: float
    timestamp_utc: str


def run(cmd: List[str], check: bool = True, capture: bool = True, shell: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd if not shell else " ".join(cmd),
        check=check,
        capture_output=capture,
        text=True,
        shell=shell,
    )


def ensure_windows() -> None:
    if os.name != "nt":
        raise RuntimeError("This script must be run on Windows 10/11 (os.name == 'nt').")


def write_temp_bench() -> Path:
    tmp = Path(tempfile.gettempdir()) / "vq_turbo_bench.py"
    tmp.write_text(BENCHMARK_PY, encoding="utf-8")
    return tmp


def parse_json_output(stdout: str) -> dict:
    stdout = stdout.strip()
    # find the last JSON object in output
    m = re.search(r"(\{.*\})\s*$", stdout, flags=re.S)
    if not m:
        raise RuntimeError(f"Cannot parse benchmark JSON from output:\n{stdout}")
    return json.loads(m.group(1))


def run_windows_baseline(py_file: Path) -> BenchResult:
    cp = run([sys.executable, str(py_file)])
    data = parse_json_output(cp.stdout)
    return BenchResult(
        name="windows-host",
        throughput_mb_s=float(data["throughput_mb_s"]),
        median_seconds=float(data["median_seconds"]),
        raw_json=data,
    )


def powershell(ps_script: str, check: bool = True) -> subprocess.CompletedProcess:
    ps_bin = shutil.which("powershell") or shutil.which("pwsh")
    if not ps_bin:
        raise RuntimeError("PowerShell not found. Install Windows PowerShell or PowerShell 7 (pwsh).")
    return run([ps_bin, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script], check=check)


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ensure_wsl_features() -> Tuple[bool, str]:
    """Best-effort enable required Windows features. Returns (reboot_required, details)."""
    ps = textwrap.dedent(
        """
        $ErrorActionPreference = 'Stop'
        $features = @('Microsoft-Windows-Subsystem-Linux','VirtualMachinePlatform')
        $reboot = $false
        foreach ($f in $features) {
          $state = (Get-WindowsOptionalFeature -Online -FeatureName $f).State
          if ($state -ne 'Enabled') {
            $res = Enable-WindowsOptionalFeature -Online -FeatureName $f -NoRestart -All
            if ($res.RestartNeeded) { $reboot = $true }
          }
        }
        $wslStatus = ''
        try { $wslStatus = (wsl --status | Out-String) } catch {}
        [PSCustomObject]@{ RebootRequired=$reboot; WslStatus=$wslStatus } | ConvertTo-Json -Compress
        """
    )
    cp = powershell(ps, check=False)
    if cp.returncode != 0:
        msg = (cp.stderr or cp.stdout or "").strip()
        return False, msg
    try:
        payload = json.loads(cp.stdout.strip().splitlines()[-1])
        return bool(payload.get("RebootRequired", False)), str(payload.get("WslStatus", "")).strip()
    except Exception:
        return False, cp.stdout.strip()


def wsl_available() -> bool:
    try:
        cp = run(["wsl", "--status"], check=False)
        return cp.returncode == 0
    except FileNotFoundError:
        return False


def distro_installed(distro: str) -> bool:
    cp = run(["wsl", "-l", "-q"], check=False)
    lines = [ln.strip() for ln in cp.stdout.splitlines() if ln.strip()]
    return distro.lower() in {ln.lower() for ln in lines}


def ensure_wsl_ready_or_raise() -> None:
    if wsl_available():
        return

    if not is_admin():
        raise RuntimeError(
            "WSL is not available and auto-enable requires Administrator rights. "
            "Run PowerShell/CMD as Administrator and re-run the script."
        )

    reboot_required, details = ensure_wsl_features()
    if reboot_required:
        raise RuntimeError(
            "WSL features were enabled, but Windows reboot is required. Reboot and run script again."
        )

    if not wsl_available():
        extra = f" Details: {details}" if details else ""
        raise RuntimeError(
            "WSL still unavailable after auto-enable attempt. Check virtualization in BIOS/UEFI and run `wsl --status`."
            + extra
        )


def ensure_wsl_ubuntu(distro: str) -> None:
    ensure_wsl_ready_or_raise()

    # On some systems this requires elevation/reboot; make it best-effort.
    run(["wsl", "--set-default-version", "2"], check=False)

    if distro_installed(distro):
        return

    ps = textwrap.dedent(
        f"""
        $ErrorActionPreference = 'Stop'
        wsl --install -d {distro}
        """
    )
    try:
        powershell(ps)
    except subprocess.CalledProcessError as exc:
        msg = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(
            "WSL distro installation failed. Run terminal as Administrator and ensure virtualization is enabled in BIOS. "
            f"Original error: {msg}"
        ) from exc

    if not distro_installed(distro):
        raise RuntimeError(
            f"Distro '{distro}' was not detected after install. Open 'wsl' once manually to complete first-run setup, then rerun."
        )


def wsl_exec(command: str, distro: str) -> subprocess.CompletedProcess:
    return run(["wsl", "-d", distro, "--", "bash", "-lc", command])


def run_wsl_benchmark(py_file: Path, distro: str, repo_win_path: Optional[str]) -> BenchResult:
    try:
        wsl_exec("sudo apt-get update -y", distro)
        wsl_exec("sudo apt-get install -y python3 python3-pip build-essential git", distro)
    except subprocess.CalledProcessError as exc:
        msg = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"Failed preparing Ubuntu in WSL. Error: {msg}") from exc

    win_path_escaped = shlex.quote(str(py_file))
    wsl_bench_path = "/tmp/vq_turbo_bench.py"
    wsl_exec(f"cp \"$(wslpath {win_path_escaped})\" {wsl_bench_path}", distro)

    if repo_win_path:
        wsl_repo = "$(wslpath " + shlex.quote(repo_win_path) + ")"
        # best-effort dependencies for kernel build flow
        wsl_exec(f"cd {wsl_repo} && chmod +x build_vq_turbo_kernel.sh || true", distro)
        wsl_exec(
            "sudo apt-get install -y fakeroot libncurses-dev bison flex libssl-dev libelf-dev dwarves clang lld",
            distro,
        )

    cp = wsl_exec(f"python3 {wsl_bench_path}", distro)
    data = parse_json_output(cp.stdout)
    return BenchResult(
        name=f"wsl2-{distro}",
        throughput_mb_s=float(data["throughput_mb_s"]),
        median_seconds=float(data["median_seconds"]),
        raw_json=data,
    )


def hyperv_not_implemented(vm_name: str) -> None:
    raise NotImplementedError(
        "Hyper-V full unattended provisioning is environment-specific (ISO/template/network). "
        f"Requested VM: {vm_name}. Use --mode wsl for out-of-box automation."
    )


def build_report(mode: str, baseline: BenchResult, guest: BenchResult) -> FinalReport:
    delta = ((guest.throughput_mb_s - baseline.throughput_mb_s) / baseline.throughput_mb_s) * 100.0
    return FinalReport(
        mode=mode,
        baseline=baseline,
        guest=guest,
        percent_delta=delta,
        timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


def save_report(report: FinalReport, out_file: Path) -> None:
    payload = asdict(report)
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision WSL/Hyper-V VM and compare benchmark vs host.")
    parser.add_argument("--mode", choices=["wsl", "hyperv"], default="wsl")
    parser.add_argument("--distro", default="Ubuntu")
    parser.add_argument("--hyperv-vm-name", default="VQTurboUbuntu")
    parser.add_argument("--repo-win-path", default="", help="Windows path to repo with patch kit")
    parser.add_argument("--output", default="vq_turbo_benchmark_report.json")
    args = parser.parse_args()

    ensure_windows()
    bench_file = write_temp_bench()

    baseline = run_windows_baseline(bench_file)

    if args.mode == "wsl":
        try:
            ensure_wsl_ubuntu(args.distro)
            guest = run_wsl_benchmark(bench_file, args.distro, args.repo_win_path or None)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    else:
        hyperv_not_implemented(args.hyperv_vm_name)
        return 2

    report = build_report(args.mode, baseline, guest)
    save_report(report, Path(args.output))

    print("=== VQ TURBO BENCHMARK REPORT ===")
    print(f"Host throughput:  {report.baseline.throughput_mb_s:.2f} MB/s")
    print(f"Guest throughput: {report.guest.throughput_mb_s:.2f} MB/s")
    print(f"Delta:            {report.percent_delta:+.2f}%")
    print(f"Saved:            {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
