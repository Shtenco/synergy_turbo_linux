#!/usr/bin/env python3
"""MetaRAM -> SharedCAS bridge: cold evicted pages become immutable CID objects."""
from __future__ import annotations
from dataclasses import dataclass
from shared_cas import SharedCAS,content_id

PAGE=4096

@dataclass
class ColdPageRef:
    space:int
    vpn:int
    generation:int
    timestamp_ns:int
    cid:bytes

class MetaRAMCASBridge:
    def __init__(self,cas:SharedCAS):
        self.cas=cas
        self.refs={}

    def evict(self,space:int,vpn:int,generation:int,timestamp_ns:int,page:bytes)->ColdPageRef:
        if len(page)!=PAGE:raise ValueError("page size")
        cid=self.cas.put(page)
        ref=ColdPageRef(space,vpn,generation,timestamp_ns,cid)
        self.refs[(space,vpn,generation)]=ref
        return ref

    def page_in(self,space:int,vpn:int,generation:int)->bytes:
        ref=self.refs[(space,vpn,generation)]
        data=self.cas.get(ref.cid)
        if len(data)!=PAGE:raise ValueError("CAS page size")
        return data
