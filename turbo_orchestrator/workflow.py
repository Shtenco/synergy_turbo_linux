from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import json

from .config import OrchestratorConfig
from .ssh_client import SSHSession


class TurboWorkflow:
    def __init__(self, cfg: OrchestratorConfig):
        self.cfg = cfg
        self.results_dir = Path(cfg.results_dir)
        self.results_dir.mkdir(exist_ok=True)

    def _must_run(self, ssh: SSHSession, cmd: str):
        code, out, err = ssh.run(cmd)
        if code != 0:
            raise RuntimeError(f"Command failed ({code}): {cmd}\n{err}\n{out}")
        return out

    def run(self) -> Path:
        ssh = SSHSession(
            host=self.cfg.vps.host,
            user=self.cfg.vps.user,
            port=self.cfg.vps.port,
            key_path=self.cfg.vps.private_key,
        )
        ssh.connect()
        try:
            self._must_run(ssh, "apt-get update")
            self._must_run(
                ssh,
                "DEBIAN_FRONTEND=noninteractive apt-get install -y qemu-kvm libvirt-daemon-system virtinst sysbench build-essential linux-source bc flex bison libssl-dev libelf-dev",
            )

            baseline = self._must_run(
                ssh,
                "sysbench cpu --threads=2 --time=30 run | sed -n 's/^\\s*events per second:\\s*//p'",
            ).strip()

            remote_patch = f"/root/{Path(self.cfg.patch_file).name}"
            ssh.put(self.cfg.patch_file, remote_patch)
            self._must_run(
                ssh,
                "cd /usr/src && tar -xf linux-source-*.tar.* && cd linux-source-* && patch -p1 < " + remote_patch,
            )

            self._must_run(
                ssh,
                "sysctl -w kernel.sched_autogroup_enabled=0 && sysctl -w vm.swappiness=10",
            )
            patched = self._must_run(
                ssh,
                "sysbench cpu --threads=2 --time=30 run | sed -n 's/^\\s*events per second:\\s*//p'",
            ).strip()

            b = float(baseline)
            p = float(patched)
            uplift = ((p - b) / b) * 100 if b else 0

            report = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "config": asdict(self.cfg),
                "baseline_events_per_sec": b,
                "patched_events_per_sec": p,
                "uplift_percent": uplift,
            }
            out_path = self.results_dir / f"benchmark_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            return out_path
        finally:
            ssh.close()
