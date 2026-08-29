#!/usr/bin/env python3
"""
MetaFS-X v0.3
- exact immutable snapshots
- CDC cross-file/cross-snapshot dedup
- previous-generation Zstd dictionary superblocks
- lazy O(1) chunk -> superblock index
- optional external SharedCAS references (same CIDv1 as MetaRAM)
"""
from __future__ import annotations

import argparse,brotli,hashlib,json,lzma,mmap,os,struct,zlib,subprocess
from pathlib import Path
try:
    import zstandard as zstd
except ImportError:
    zstd=None

try:
    from shared_cas import SharedCAS,content_id
except Exception:
    def content_id(d:bytes)->bytes:return hashlib.sha256(d).digest()
    SharedCAS=None

MAGIC=b"MFSX3"
VERSION=3
MIN_CHUNK=4096
AVG_MASK=(1<<14)-1
MAX_CHUNK=65536
SB_TARGET=1<<20
DICT_MAX=65536

SB_ZSTD=1
SB_BROTLI=2
SB_XZ=3
SB_ZSTD_DICT=4
SB_ZLIB_DICT=5
SB_LINEAGE_XOR=6

LOC_INTERNAL=0
LOC_EXTERNAL_CAS=1

GEAR=[int.from_bytes(hashlib.sha256(b"metafs3-gear-"+bytes([i])).digest()[:8],"little") for i in range(256)]

def uv(n:int)->bytes:
    o=bytearray()
    while True:
        b=n&127;n>>=7
        if n:o.append(b|128)
        else:o.append(b);return bytes(o)

def rv(b,p:int):
    x=s=0
    for _ in range(10):
        q=b[p];p+=1;x|=(q&127)<<s
        if not q&128:return x,p
        s+=7
    raise ValueError("varint")

def chunks(d:bytes):
    if not d:
        yield 0,0
        return
    st=0;h=0
    for i,x in enumerate(d):
        h=((h<<1)+GEAR[x])&((1<<64)-1)
        ln=i-st+1
        if ln>=MIN_CHUNK and ((h&AVG_MASK)==0 or ln>=MAX_CHUNK):
            yield st,i+1;st=i+1;h=0
    if st<len(d):yield st,len(d)

def walk(root):
    root=Path(root)
    for p in sorted(root.rglob("*")):
        if p.is_file():yield p.relative_to(root).as_posix(),p

def _zstd_plain(raw:bytes)->bytes:
    if zstd is not None:
        return zstd.ZstdCompressor(level=19,write_checksum=False,write_content_size=True,write_dict_id=False).compress(raw)
    return subprocess.run(["zstd","-q","-19","-c"],input=raw,stdout=subprocess.PIPE,check=True).stdout

def _zstd_plain_dec(pay:bytes,max_output:int=0)->bytes:
    if zstd is not None:
        return zstd.ZstdDecompressor().decompress(pay,max_output_size=max_output or 0)
    return subprocess.run(["zstd","-q","-d","-c"],input=pay,stdout=subprocess.PIPE,check=True).stdout

def _zstd_dict(raw:bytes,dict_raw:bytes)->bytes:
    if zstd is None or not hasattr(zstd,"ZstdCompressionDict"):raise RuntimeError("python zstandard dictionary API unavailable")
    dr=dict_raw[-DICT_MAX:];zd=zstd.ZstdCompressionDict(dr,dict_type=zstd.DICT_TYPE_RAWCONTENT)
    return zstd.ZstdCompressor(level=19,dict_data=zd,write_checksum=False,write_content_size=True,write_dict_id=False).compress(raw)

def _zstd_dict_dec(pay:bytes,dict_raw:bytes,max_output:int)->bytes:
    if zstd is None or not hasattr(zstd,"ZstdCompressionDict"):raise RuntimeError("python zstandard dictionary API unavailable")
    dr=dict_raw[-DICT_MAX:];zd=zstd.ZstdCompressionDict(dr,dict_type=zstd.DICT_TYPE_RAWCONTENT)
    return zstd.ZstdDecompressor(dict_data=zd).decompress(pay,max_output_size=max_output)

def _zlib_dict(raw:bytes,dict_raw:bytes)->bytes:
    dr=dict_raw[-32768:];c=zlib.compressobj(level=9,method=zlib.DEFLATED,wbits=zlib.MAX_WBITS,memLevel=9,strategy=zlib.Z_DEFAULT_STRATEGY,zdict=dr)
    return c.compress(raw)+c.flush()

def _zlib_dict_dec(pay:bytes,dict_raw:bytes)->bytes:
    dr=dict_raw[-32768:];d=zlib.decompressobj(wbits=zlib.MAX_WBITS,zdict=dr)
    return d.decompress(pay)+d.flush()

def _xor_bytes(a:bytes,b:bytes)->bytes:return bytes(x^y for x,y in zip(a,b))

def _encode_superblock(raw:bytes,dict_raw:bytes|None):
    opts=[(SB_ZSTD,0,_zstd_plain(raw)),(SB_BROTLI,0,brotli.compress(raw,quality=11)),(SB_XZ,0,lzma.compress(raw,format=lzma.FORMAT_XZ,preset=9|lzma.PRESET_EXTREME))]
    if dict_raw:
        try:opts.append((SB_ZSTD_DICT,1,_zstd_dict(raw,dict_raw)))
        except Exception:pass
        try:opts.append((SB_ZLIB_DICT,1,_zlib_dict(raw,dict_raw)))
        except Exception:pass
    return min(opts,key=lambda x:(len(x[2]),x[0]))

def pack_snapshots(snapshots,out_path,external_cas=None):
    if external_cas is not None and not hasattr(external_cas,"has"):
        if SharedCAS is None:raise RuntimeError("SharedCAS unavailable")
        external_cas=SharedCAS(external_cas)
    cmap={};chunk_records=[];manifests=[];logical=0;refs=0;external_refs=0
    for gen,(name,ts,root) in enumerate(snapshots):
        files=[];prev_files=({f["path"]:f for f in manifests[-1]["files"]} if manifests else {})
        for rel,p in walk(root):
            d=p.read_bytes();logical+=len(d);ids=[];prev_ids=prev_files.get(rel,{}).get("chunks",[])
            for chunk_pos,(a,b) in enumerate(chunks(d)):
                q=d[a:b];cid=content_id(q);idx=cmap.get(cid)
                if idx is None:
                    ext=bool(external_cas is not None and external_cas.has(cid,len(q)));parent=prev_ids[chunk_pos] if chunk_pos<len(prev_ids) else -1
                    idx=len(chunk_records);cmap[cid]=idx;chunk_records.append({"cid":cid,"data":None if ext else q,"n":len(q),"first_gen":gen,"external":ext,"parent":parent})
                ids.append(idx);refs+=1
                if chunk_records[idx]["external"]:external_refs+=1
            st=p.stat();files.append({"path":rel,"mode":st.st_mode&0o7777,"size":len(d),"sha256":content_id(d).hex(),"chunks":ids})
        manifests.append({"snapshot":name,"timestamp_ns":int(ts),"generation":gen,"files":files})
    loc=[None]*len(chunk_records);superblocks=[]
    def chunk_plain(cid):
        r=chunk_records[cid]
        if r["data"] is not None:return r["data"]
        if external_cas is None:raise ValueError("external predecessor without CAS")
        return external_cas.get(r["cid"])
    for gen in range(len(snapshots)):
        ids=[i for i,r in enumerate(chunk_records) if r["first_gen"]==gen and not r["external"]];buf=bytearray();members=[]
        def flush():
            nonlocal buf,members
            if not members:return
            dict_ids=[];dict_raw=bytearray();seen=set()
            for cid,off,n in members:
                parent=chunk_records[cid].get("parent",-1)
                if parent is None or parent<0 or parent in seen:continue
                if chunk_records[parent]["first_gen"]>=gen:continue
                q=chunk_plain(parent)
                if len(dict_raw)+len(q)>DICT_MAX:
                    take=max(0,DICT_MAX-len(dict_raw))
                    if take:dict_raw+=q[-take:];dict_ids.append(parent);seen.add(parent)
                    break
                dict_raw+=q;dict_ids.append(parent);seen.add(parent)
            raw_bytes=bytes(buf);codec,dict_used,pay=_encode_superblock(raw_bytes,bytes(dict_raw) if dict_raw else None);parent_map=[];residual=bytearray();lineage_ok=False
            for cid,off,n in members:
                parent=chunk_records[cid].get("parent",-1);q=chunk_records[cid]["data"]
                if parent is not None and parent>=0 and chunk_records[parent]["first_gen"]<gen:
                    pq=chunk_plain(parent)
                    if len(pq)==len(q):residual+=_xor_bytes(q,pq);parent_map.append(parent+1);lineage_ok=True;continue
                residual+=q;parent_map.append(0)
            if lineage_ok:
                lopts=[_zstd_plain(bytes(residual)),brotli.compress(bytes(residual),quality=11)];lpay=min(lopts,key=len);map_cost=len(uv(len(parent_map)))+sum(len(uv(x)) for x in parent_map)
                if len(lpay)+map_cost < len(pay)+(sum(len(uv(x)) for x in dict_ids)+len(uv(len(dict_ids)))):codec=SB_LINEAGE_XOR;pay=lpay;dict_ids=[]
            if codec not in (SB_ZSTD_DICT,SB_ZLIB_DICT):dict_ids=[]
            sid=len(superblocks);superblocks.append({"generation":gen,"codec":codec,"dict_ids":dict_ids,"parent_map":parent_map if codec==SB_LINEAGE_XOR else [],"raw_n":len(buf),"payload":pay,"raw":raw_bytes})
            for cid,off,n in members:loc[cid]=(LOC_INTERNAL,sid,off,n)
            buf=bytearray();members=[]
        for cid in ids:
            q=chunk_records[cid]["data"]
            if buf and len(buf)+len(q)>SB_TARGET:flush()
            off=len(buf);buf+=q;members.append((cid,off,len(q)))
        flush()
    for cid,r in enumerate(chunk_records):
        if r["external"]:loc[cid]=(LOC_EXTERNAL_CAS,-1,0,r["n"])
    meta={"version":VERSION,"snapshots":manifests,"logical_bytes":logical,"chunk_refs":refs,"unique_chunks":len(chunk_records),"external_chunk_refs":external_refs,"external_unique_chunks":sum(1 for r in chunk_records if r["external"]),"superblocks":len(superblocks)}
    meta_comp=_zstd_plain(json.dumps(meta,separators=(",",":"),sort_keys=True).encode());out=bytearray(MAGIC)+uv(len(meta_comp))+meta_comp+uv(len(chunk_records))
    for cid,r in enumerate(chunk_records):
        kind,sid,off,n=loc[cid];out+=r["cid"]+bytes([kind])
        if kind==LOC_INTERNAL:out+=uv(sid)+uv(off)+uv(n)
        else:out+=uv(n)
    out+=uv(len(superblocks))
    for sb in superblocks:
        out+=uv(sb["generation"])+bytes([sb["codec"]])+uv(len(sb["dict_ids"]))
        for cid in sb["dict_ids"]:out+=uv(cid)
        out+=uv(len(sb.get("parent_map",[])))
        for x in sb.get("parent_map",[]):out+=uv(x)
        out+=uv(sb["raw_n"])+uv(len(sb["payload"]))+sb["payload"]
    out+=hashlib.sha256(out).digest();Path(out_path).write_bytes(out)
    return {"archive_bytes":len(out),"logical_bytes":logical,"ratio":logical/len(out) if out else 0,"unique_chunks":len(chunk_records),"chunk_refs":refs,"dedup_ref_fraction":1-len(chunk_records)/max(1,refs),"external_unique_chunks":meta["external_unique_chunks"],"external_chunk_refs":external_refs,"superblocks":len(superblocks),"dictionary_superblocks":sum(1 for sb in superblocks if sb["codec"] in (SB_ZSTD_DICT,SB_ZLIB_DICT)),"zlib_dictionary_superblocks":sum(1 for sb in superblocks if sb["codec"]==SB_ZLIB_DICT),"lineage_xor_superblocks":sum(1 for sb in superblocks if sb["codec"]==SB_LINEAGE_XOR),"archive_sha256":hashlib.sha256(out).hexdigest()}

class MetaFSImage:
    def __init__(self,path,external_cas=None,cache_limit=8):
        self.path=Path(path);self.fd=self.path.open("rb");self.mm=mmap.mmap(self.fd.fileno(),0,access=mmap.ACCESS_READ);self.cache={};self.cache_order=[];self.cache_limit=max(1,int(cache_limit));self.external_cas=external_cas
        if external_cas is not None and not hasattr(external_cas,"get"):
            if SharedCAS is None:raise RuntimeError("SharedCAS unavailable")
            self.external_cas=SharedCAS(external_cas)
        self._parse_index()
    def close(self):self.mm.close();self.fd.close()
    def _parse_index(self):
        b=self.mm
        if b[:len(MAGIC)]!=MAGIC:raise ValueError("magic")
        if hashlib.sha256(b[:-32]).digest()!=b[-32:]:raise ValueError("image sha")
        p=len(MAGIC);ml,p=rv(b,p);self.meta=json.loads(_zstd_plain_dec(bytes(b[p:p+ml])).decode());p+=ml;nc,p=rv(b,p);self.chunk_index=[None]*nc
        for i in range(nc):
            cid=bytes(b[p:p+32]);p+=32;kind=b[p];p+=1
            if kind==LOC_INTERNAL:sid,p=rv(b,p);off,p=rv(b,p);n,p=rv(b,p);self.chunk_index[i]=(cid,kind,sid,off,n)
            elif kind==LOC_EXTERNAL_CAS:n,p=rv(b,p);self.chunk_index[i]=(cid,kind,-1,0,n)
            else:raise ValueError("chunk location kind")
        ns,p=rv(b,p);self.superblocks=[None]*ns
        for sid in range(ns):
            gen,p=rv(b,p);codec=b[p];p+=1;nd,p=rv(b,p);dict_ids=[]
            for _ in range(nd):q,p=rv(b,p);dict_ids.append(q)
            npmap,p=rv(b,p);parent_map=[]
            for _ in range(npmap):q,p=rv(b,p);parent_map.append(q)
            raw_n,p=rv(b,p);ln,p=rv(b,p);poff=p;p+=ln;self.superblocks[sid]={"generation":gen,"codec":codec,"dict_ids":dict_ids,"parent_map":parent_map,"raw_n":raw_n,"payload_off":poff,"payload_n":ln}
        if p!=len(b)-32:raise ValueError("trailing")
        self.sb_members=[[] for _ in self.superblocks]
        for cid,entry in enumerate(self.chunk_index):
            _dg,kind,sid,off,n=entry
            if kind==LOC_INTERNAL:self.sb_members[sid].append((off,cid,n))
        for q in self.sb_members:q.sort()
    def _cache_put(self,sid,raw):
        if sid in self.cache:return
        self.cache[sid]=raw;self.cache_order.append(sid)
        while len(self.cache_order)>self.cache_limit:
            old=self.cache_order.pop(0)
            if old!=sid:self.cache.pop(old,None)
    def load_superblock(self,sid:int)->bytes:
        q=self.cache.get(sid)
        if q is not None:return q
        sb=self.superblocks[sid];pay=bytes(self.mm[sb["payload_off"]:sb["payload_off"]+sb["payload_n"]]);codec=sb["codec"]
        if codec==SB_ZSTD:raw=_zstd_plain_dec(pay,sb["raw_n"])
        elif codec==SB_BROTLI:raw=brotli.decompress(pay)
        elif codec==SB_XZ:raw=lzma.decompress(pay)
        elif codec in (SB_ZSTD_DICT,SB_ZLIB_DICT):
            if not sb["dict_ids"]:raise ValueError("missing dictionary")
            parts=[];remaining=DICT_MAX
            for cid in sb["dict_ids"]:
                q=self.get_chunk(cid)
                if len(q)>remaining:q=q[-remaining:]
                parts.append(q);remaining-=len(q)
                if remaining<=0:break
            dict_raw=b"".join(parts);raw=_zstd_dict_dec(pay,dict_raw,sb["raw_n"]) if codec==SB_ZSTD_DICT else _zlib_dict_dec(pay,dict_raw)
        elif codec==SB_LINEAGE_XOR:
            try:residual=_zstd_plain_dec(pay,sb["raw_n"])
            except Exception:residual=brotli.decompress(pay)
            if len(residual)!=sb["raw_n"] or len(sb["parent_map"])!=len(self.sb_members[sid]):raise ValueError("lineage residual")
            out=bytearray(sb["raw_n"])
            for (off,cid,n),px in zip(self.sb_members[sid],sb["parent_map"]):
                q=residual[off:off+n]
                if px:
                    parent=self.get_chunk(px-1)
                    if len(parent)!=n:raise ValueError("lineage parent length")
                    q=_xor_bytes(q,parent)
                out[off:off+n]=q
            raw=bytes(out)
        else:raise ValueError("superblock codec")
        if len(raw)!=sb["raw_n"]:raise ValueError("superblock length")
        self._cache_put(sid,raw);return raw
    def get_chunk(self,cid_num:int)->bytes:
        cid,kind,sid,off,n=self.chunk_index[cid_num]
        if kind==LOC_EXTERNAL_CAS:
            if self.external_cas is None:raise ValueError("external CAS required")
            q=self.external_cas.get(cid)
        else:q=self.load_superblock(sid)[off:off+n]
        if len(q)!=n or content_id(q)!=cid:raise ValueError("chunk identity")
        return q
    def read_file(self,snapshot:str,path:str)->bytes:
        sn=next(x for x in self.meta["snapshots"] if x["snapshot"]==snapshot);f=next(x for x in sn["files"] if x["path"]==path);d=b"".join(self.get_chunk(i) for i in f["chunks"])[:f["size"]]
        if content_id(d).hex()!=f["sha256"]:raise ValueError("file identity")
        return d
    def restore_snapshot(self,snapshot:str,dest):
        sn=next(x for x in self.meta["snapshots"] if x["snapshot"]==snapshot);dest=Path(dest)
        for f in sn["files"]:
            p=dest/f["path"];p.parent.mkdir(parents=True,exist_ok=True);d=b"".join(self.get_chunk(i) for i in f["chunks"])[:f["size"]]
            if content_id(d).hex()!=f["sha256"]:raise ValueError("file identity")
            p.write_bytes(d);os.chmod(p,f["mode"])
        return len(sn["files"])

def verify(root,dest):
    a={r:content_id(p.read_bytes()) for r,p in walk(root)};b={r:content_id(p.read_bytes()) for r,p in walk(dest)};return a==b

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest="cmd",required=True);p=sub.add_parser("pack");p.add_argument("out");p.add_argument("spec",nargs="+");p.add_argument("--cas");p=sub.add_parser("restore");p.add_argument("image");p.add_argument("snapshot");p.add_argument("dest");p.add_argument("--cas");a=ap.parse_args()
    if a.cmd=="pack":
        ss=[]
        for x in a.spec:n,t,path=x.split(":",2);ss.append((n,int(t),Path(path)))
        print(json.dumps(pack_snapshots(ss,a.out,a.cas),indent=2))
    else:
        im=MetaFSImage(a.image,a.cas)
        try:print(im.restore_snapshot(a.snapshot,a.dest))
        finally:im.close()
if __name__=="__main__":main()
