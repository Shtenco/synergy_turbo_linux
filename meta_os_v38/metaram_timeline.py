#!/usr/bin/env python3
"""Sparse temporal virtual page history prototype."""
from __future__ import annotations
from bisect import bisect_right
from dataclasses import dataclass
import hashlib
import lz4.block

PAGE=4096
RAW=0;ZERO=1;LZ4=2;SAME_PREV=3;XOR_LZ4=4;CONTENT_REF=5

@dataclass
class Version:
    ts:int
    codec:int
    payload:bytes
    prev:int
    digest:bytes

class TemporalPageStore:
    def __init__(self):
        self.lines={}
        self.content={}
        self.physical_payload_bytes=0

    @staticmethod
    def _xor(a,b):return bytes(x^y for x,y in zip(a,b))

    def publish(self,space,vpn,ts,page):
        if len(page)!=PAGE:raise ValueError("page must be 4096 bytes")
        key=(int(space),int(vpn));line=self.lines.setdefault(key,[])
        if line and ts<=line[-1].ts:raise ValueError("timestamps must increase per page")
        dg=hashlib.sha256(page).digest();prev_page=self.resolve(space,vpn,line[-1].ts) if line else None
        if not any(page):v=Version(ts,ZERO,b"",len(line)-1,dg)
        elif prev_page==page:v=Version(ts,SAME_PREV,b"",len(line)-1,dg)
        elif dg in self.content:v=Version(ts,CONTENT_REF,dg,len(line)-1,dg)
        else:
            direct=lz4.block.compress(page,mode="fast",acceleration=1,store_size=False);codec=LZ4;pay=direct
            if prev_page is not None:
                xp=lz4.block.compress(self._xor(page,prev_page),mode="fast",acceleration=1,store_size=False)
                if len(xp)<len(pay):codec=XOR_LZ4;pay=xp
            if len(pay)>=PAGE-32:codec=RAW;pay=page
            v=Version(ts,codec,pay,len(line)-1,dg);self.content[dg]=page;self.physical_payload_bytes+=len(pay)
        line.append(v);return v

    def _materialize_index(self,key,idx):
        v=self.lines[key][idx]
        if v.codec==ZERO:return bytes(PAGE)
        if v.codec==CONTENT_REF:return self.content[v.payload]
        if v.codec==SAME_PREV:return self._materialize_index(key,v.prev)
        if v.codec==RAW:return v.payload
        if v.codec==LZ4:return lz4.block.decompress(v.payload,uncompressed_size=PAGE)
        if v.codec==XOR_LZ4:
            prev=self._materialize_index(key,v.prev);x=lz4.block.decompress(v.payload,uncompressed_size=PAGE);return self._xor(x,prev)
        raise ValueError("codec")

    def resolve(self,space,vpn,ts):
        key=(int(space),int(vpn));line=self.lines.get(key)
        if not line:return None
        i=bisect_right([v.ts for v in line],int(ts))-1
        if i<0:return None
        page=self._materialize_index(key,i)
        if hashlib.sha256(page).digest()!=line[i].digest:raise ValueError("digest")
        return page

    def logical_versions(self):return sum(len(v) for v in self.lines.values())
    def metadata_bytes_estimate(self):return self.logical_versions()*32
    def physical_bytes_estimate(self):return self.physical_payload_bytes+self.metadata_bytes_estimate()
