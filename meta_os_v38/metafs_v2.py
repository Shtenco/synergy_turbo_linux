#!/usr/bin/env python3
"""MetaFS-X v0.2: CDC dedup + solid superblocks + exact snapshots."""
from __future__ import annotations
import argparse,brotli,hashlib,json,lzma,os
from pathlib import Path
import zstandard as zstd

MAGIC=b"MFSX2";SB_TARGET=1<<20
_ZC=zstd.ZstdCompressor(level=19,write_checksum=False,write_content_size=True,write_dict_id=False)
_ZD=zstd.ZstdDecompressor()
GEAR=[int.from_bytes(hashlib.sha256(b"metafs2-"+bytes([i])).digest()[:8],"little") for i in range(256)]
MIN_CHUNK=4096;MASK=(1<<14)-1;MAX_CHUNK=65536
ZSTD=1;BROTLI=2;XZ=3

def uv(n):
    o=bytearray()
    while True:
        b=n&127;n>>=7
        if n:o.append(b|128)
        else:o.append(b);return bytes(o)
def rv(b,p):
    x=s=0
    while True:
        q=b[p];p+=1;x|=(q&127)<<s
        if not q&128:return x,p
        s+=7
def chunks(d):
    st=0;h=0
    for i,x in enumerate(d):
        h=((h<<1)+GEAR[x])&((1<<64)-1);ln=i-st+1
        if ln>=MIN_CHUNK and ((h&MASK)==0 or ln>=MAX_CHUNK):
            yield st,i+1;st=i+1;h=0
    if st<len(d):yield st,len(d)
    if not d:yield 0,0
def walk(root):
    for p in sorted(Path(root).rglob("*")):
        if p.is_file():yield p.relative_to(root).as_posix(),p
def enc_sb(raw):
    opts=[(ZSTD,_ZC.compress(raw)),(BROTLI,brotli.compress(raw,quality=11)),(XZ,lzma.compress(raw,format=lzma.FORMAT_XZ,preset=9|lzma.PRESET_EXTREME))]
    return min(opts,key=lambda x:(len(x[1]),x[0]))
def dec_sb(codec,pay):
    if codec==ZSTD:return _ZD.decompress(pay)
    if codec==BROTLI:return brotli.decompress(pay)
    if codec==XZ:return lzma.decompress(pay)
    raise ValueError("sb codec")

def pack_snapshots(snapshots,out_path):
    cmap={};chunks_raw=[];man=[];refs=0;logical=0
    for name,ts,root in snapshots:
        files=[]
        for rel,p in walk(root):
            d=p.read_bytes();logical+=len(d);ids=[]
            for a,b in chunks(d):
                q=d[a:b];dg=hashlib.sha256(q).digest();cid=cmap.get(dg)
                if cid is None:
                    cid=len(chunks_raw);cmap[dg]=cid;chunks_raw.append((dg,q))
                ids.append(cid);refs+=1
            st=p.stat()
            files.append({"path":rel,"mode":st.st_mode&0o7777,"size":len(d),"sha256":hashlib.sha256(d).hexdigest(),"chunks":ids})
        man.append({"snapshot":name,"timestamp_ns":int(ts),"files":files})

    loc=[None]*len(chunks_raw);superblocks=[];buf=bytearray();members=[]
    def flush():
        nonlocal buf,members
        if not members:return
        sid=len(superblocks);raw=bytes(buf);codec,pay=enc_sb(raw);superblocks.append((codec,len(raw),pay))
        for cid,off,n in members:loc[cid]=(sid,off,n)
        buf=bytearray();members=[]
    for cid,(dg,q) in enumerate(chunks_raw):
        if buf and len(buf)+len(q)>SB_TARGET:flush()
        off=len(buf);buf+=q;members.append((cid,off,len(q)))
    flush()

    meta={"version":2,"snapshots":man,"logical_bytes":logical,"chunk_refs":refs,"unique_chunks":len(chunks_raw),"superblocks":len(superblocks)}
    mc=_ZC.compress(json.dumps(meta,separators=(",",":"),sort_keys=True).encode())
    o=bytearray(MAGIC)+uv(len(mc))+mc+uv(len(chunks_raw))
    for cid,(dg,q) in enumerate(chunks_raw):
        sid,off,n=loc[cid];o+=dg+uv(sid)+uv(off)+uv(n)
    o+=uv(len(superblocks))
    for codec,n,pay in superblocks:o+=bytes([codec])+uv(n)+uv(len(pay))+pay
    o+=hashlib.sha256(o).digest();Path(out_path).write_bytes(o)
    return {"archive_bytes":len(o),"logical_bytes":logical,"ratio":logical/len(o),"unique_chunks":len(chunks_raw),"chunk_refs":refs,"dedup_ref_fraction":1-len(chunks_raw)/max(1,refs),"superblocks":len(superblocks),"archive_sha256":hashlib.sha256(o).hexdigest()}

def read_image(path):
    b=Path(path).read_bytes()
    if b[:5]!=MAGIC or hashlib.sha256(b[:-32]).digest()!=b[-32:]:raise ValueError("image")
    p=5;ml,p=rv(b,p);meta=json.loads(_ZD.decompress(b[p:p+ml]).decode());p+=ml
    nc,p=rv(b,p);idx=[]
    for _ in range(nc):
        dg=b[p:p+32];p+=32;sid,p=rv(b,p);off,p=rv(b,p);n,p=rv(b,p);idx.append((dg,sid,off,n))
    ns,p=rv(b,p);sbs=[]
    for _ in range(ns):
        codec=b[p];p+=1;n,p=rv(b,p);ln,p=rv(b,p);pay=b[p:p+ln];p+=ln
        raw=dec_sb(codec,pay)
        if len(raw)!=n:raise ValueError("sb len")
        sbs.append(raw)
    if p!=len(b)-32:raise ValueError("trailing")
    chunks_out=[]
    for dg,sid,off,n in idx:
        q=sbs[sid][off:off+n]
        if hashlib.sha256(q).digest()!=dg:raise ValueError("chunk sha")
        chunks_out.append(q)
    return meta,chunks_out

def restore_snapshot(image,snapshot,dest):
    meta,chunks_out=read_image(image);sn=next(x for x in meta["snapshots"] if x["snapshot"]==snapshot)
    for f in sn["files"]:
        p=Path(dest)/f["path"];p.parent.mkdir(parents=True,exist_ok=True)
        d=b"".join(chunks_out[i] for i in f["chunks"])[:f["size"]]
        if hashlib.sha256(d).hexdigest()!=f["sha256"]:raise ValueError("file sha")
        p.write_bytes(d);os.chmod(p,f["mode"])
    return len(sn["files"])

def verify(root,dest):
    a={r:hashlib.sha256(p.read_bytes()).digest() for r,p in walk(root)}
    b={r:hashlib.sha256(p.read_bytes()).digest() for r,p in walk(dest)}
    return a==b

if __name__=="__main__":
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("pack");p.add_argument("out");p.add_argument("spec",nargs="+")
    p=sub.add_parser("restore");p.add_argument("image");p.add_argument("snapshot");p.add_argument("dest")
    a=ap.parse_args()
    if a.cmd=="pack":
        ss=[]
        for s in a.spec:
            n,t,p=s.split(":",2);ss.append((n,int(t),Path(p)))
        print(json.dumps(pack_snapshots(ss,a.out),indent=2))
    else:print(restore_snapshot(a.image,a.snapshot,a.dest))
