from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class VPSConfig:
    host: str = "92.246.131.14"
    user: str = "root"
    port: int = 22
    private_key: str = "Linux Ubuntu.ppk"


@dataclass
class ExperimentConfig:
    vm_name: str = "turbo-bench"
    vm_ram_mb: int = 2048
    vm_vcpus: int = 2
    baseline_profile: str = "linux-2gb-2cpu"
    patched_profile: str = "turbo-kvm-patched"


@dataclass
class OrchestratorConfig:
    vps: VPSConfig
    experiment: ExperimentConfig
    patch_file: str = "virtual_qubit_turbo_5.15.patch"
    results_dir: str = "results"

    @classmethod
    def load(cls, path: str | None = None) -> "OrchestratorConfig":
        if not path:
            return cls(vps=VPSConfig(), experiment=ExperimentConfig())

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            vps=VPSConfig(**data.get("vps", {})),
            experiment=ExperimentConfig(**data.get("experiment", {})),
            patch_file=data.get("patch_file", "virtual_qubit_turbo_5.15.patch"),
            results_dir=data.get("results_dir", "results"),
        )
