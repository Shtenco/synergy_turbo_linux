import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"turbo_orchestrator"/"synergy_contracts.py"
spec=importlib.util.spec_from_file_location("synergy_contracts",PATH)
mod=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(mod)

def base():
    return {"node_id":"n1","profile":"EDGE_CLIENT","attested":False,"development":True,"generation":1,
    "services":[{"name":"ui","role":"EDGE_CLIENT","artifact":"svc","sha256":"1"*64,"argv":["svc"],
    "capabilities":["ui.present"],"limits":{"memory_mib":64,"cpu_seconds":10,"open_files":32}}]}

def test_manifest_is_consumed_without_host_authority_escalation():
    p=mod.consume_node_manifest(base())
    assert p["host_authority"] is False

def test_unattested_dangerous_capability_fails():
    p=base();p["services"][0]["capabilities"]=["treasury.sign"]
    with pytest.raises(ValueError): mod.consume_node_manifest(p)
