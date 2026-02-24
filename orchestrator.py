#!/usr/bin/env python3
from __future__ import annotations

import argparse

from turbo_orchestrator.config import OrchestratorConfig
from turbo_orchestrator.workflow import TurboWorkflow


def main() -> int:
    parser = argparse.ArgumentParser(description="Windows-driven VPS KVM turbo orchestrator")
    parser.add_argument("--config", help="Path to JSON config", default=None)
    args = parser.parse_args()

    cfg = OrchestratorConfig.load(args.config)
    workflow = TurboWorkflow(cfg)
    report = workflow.run()
    print(f"Benchmark report saved: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
