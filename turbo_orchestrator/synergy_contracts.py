from __future__ import annotations

from typing import Any


UPSTREAM_CONTRACT_ID = "synergy.runtime.node-manifest/v1"

KNOWN_ROLES = {
    "EDGE_CLIENT","P2P_RELAY","CONTENT_CACHE","NEXUS_COMPUTE",
    "BLOCKCHAIN_PEER","BLOCKCHAIN_VALIDATOR","METAPAY_GATEWAY",
    "FINANCIAL_SERVICE","BUSINESS_AUTOPILOT","FULL_SYNERGY_NODE",
}
DANGEROUS_CAPS = {"blockchain.validate","finance.execute","treasury.sign","update.activate"}


def consume_node_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("profile","")) not in KNOWN_ROLES:
        raise ValueError("unknown node profile")
    services=payload.get("services")
    if not isinstance(services,list) or len(services)>64:
        raise ValueError("services must be list <=64")
    attested=bool(payload.get("attested"))
    normalized=[]
    for s in services:
        digest=str(s.get("sha256","")).lower()
        if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid service sha256")
        caps=[str(x) for x in s.get("capabilities",[])]
        if set(caps)&DANGEROUS_CAPS and not attested:
            raise ValueError("dangerous capability requires attested node")
        limits=s.get("limits") or {}
        if int(limits.get("memory_mib",0))<16 or int(limits.get("cpu_seconds",0))<1 or int(limits.get("open_files",0))<16:
            raise ValueError("invalid service limits")
        normalized.append({
            "name":str(s["name"]),"role":str(s["role"]),
            "artifact":str(s["artifact"]),"sha256":digest,
            "argv":list(s["argv"]),"capabilities":caps,"limits":dict(limits),
        })
    return {
        "node_id":str(payload["node_id"]),
        "profile":str(payload["profile"]),
        "attested":attested,
        "development":bool(payload.get("development")),
        "generation":int(payload.get("generation",1)),
        "services":normalized,
        "host_authority":False,
    }
