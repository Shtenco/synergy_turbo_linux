#!/usr/bin/env python3
"""Shared immutable compressed content-addressed store for MetaRAM and MetaFS."""
from __future__ import annotations
import hashlib,os,struct,zlib
from pathlib import Path
import lz4.block

CID_BYTES=32
MAGIC=b"SC1"
RAW=0
ZERO=1
LZ4=2
ZLIB=3

def content_id(data:bytes)->bytes:
    return hashlib.sha256(data).digest()

def cid_hex(data_or_cid)->str:
    if isinstance(data_or_cid,(bytes,bytearray)) and len(data_or_cid)==CID_BYTES:
        return bytes(data_or_cid).hex()
    return content_id(bytes(data_or_cid)).hex()

class SharedCAS:
    """
    CID is always SHA-256 of plaintext content. Representation is independent.

    policy="fast": ZERO / LZ4 / RAW, intended for MetaRAM cold page-in.
    policy="compact": additionally considers zlib-9, intended for archival tiers.
    """
    def __init__(self,root,policy="fast"):
        if policy not in ("fast","compact"):raise ValueError("policy")
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.policy=policy

    def path_for(self,cid:bytes)->Path:
        h=cid.hex()
        return self.root/h[:2]/h[2:4]/h

    @staticmethod
    def _encode(data:bytes,policy:str)->bytes:
        data=bytes(data);n=len(data)
        if n and not any(data):
            codec=ZERO;payload=b""
        else:
            opts=[(RAW,data)]
            if data:
                q=lz4.block.compress(data,mode="fast",acceleration=1,store_size=False)
                opts.append((LZ4,q))
                if policy=="compact":
                    opts.append((ZLIB,zlib.compress(data,9)))
            codec,payload=min(opts,key=lambda x:(len(x[1]),x[0]))
        return MAGIC+bytes([codec])+struct.pack("<I",n)+payload

    @staticmethod
    def _decode(blob:bytes)->bytes:
        if len(blob)<8 or blob[:3]!=MAGIC:raise ValueError("CAS object magic")
        codec=blob[3];n=struct.unpack("<I",blob[4:8])[0];payload=blob[8:]
        if codec==RAW:data=payload
        elif codec==ZERO:data=bytes(n)
        elif codec==LZ4:data=lz4.block.decompress(payload,uncompressed_size=n)
        elif codec==ZLIB:data=zlib.decompress(payload)
        else:raise ValueError("CAS codec")
        if len(data)!=n:raise ValueError("CAS object length")
        return data

    @staticmethod
    def _plaintext_len(path:Path)->int:
        with path.open("rb") as f:
            h=f.read(8)
        if len(h)<8 or h[:3]!=MAGIC:raise ValueError("CAS object header")
        return struct.unpack("<I",h[4:8])[0]

    def has(self,cid:bytes,n:int|None=None)->bool:
        p=self.path_for(cid)
        if not p.exists():return False
        return n is None or self._plaintext_len(p)==n

    def put(self,data:bytes)->bytes:
        data=bytes(data);cid=content_id(data);p=self.path_for(cid)
        if p.exists():
            if self.get(cid)!=data:raise ValueError("CAS digest collision/corruption")
            return cid
        p.parent.mkdir(parents=True,exist_ok=True)
        tmp=p.with_suffix(".tmp-"+str(os.getpid()))
        tmp.write_bytes(self._encode(data,self.policy))
        os.replace(tmp,p)
        return cid

    def get(self,cid:bytes)->bytes:
        p=self.path_for(cid);data=self._decode(p.read_bytes())
        if content_id(data)!=cid:raise ValueError("CAS object hash mismatch")
        return data

    def bytes(self)->int:
        return sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())

    def objects(self)->int:
        return sum(1 for p in self.root.rglob("*") if p.is_file())

    def logical_bytes(self)->int:
        total=0
        for p in self.root.rglob("*"):
            if p.is_file():total+=self._plaintext_len(p)
        return total
