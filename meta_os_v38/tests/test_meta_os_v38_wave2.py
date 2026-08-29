from pathlib import Path
import json,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

def test_wave2_c_build_and_ipc_path():
    subprocess.run(["make","-f","Makefile.wave2","clean"],cwd=ROOT,check=True);subprocess.run(["make","-f","Makefile.wave2"],cwd=ROOT,check=True)
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"pages.bin";p.write_bytes((bytes(4096)+b"A"*4096+(b"hello"*819)[:4096])*16)
        r=subprocess.run([str(ROOT/"metaram_ipc_bench_wave2"),str(p)],cwd=ROOT,check=True,capture_output=True,text=True);q=json.loads(r.stdout)
        assert q["exact"] is True and q["faults"]==q["pages"] and q["avg_roundtrip_us"]>0

def test_wave2_userfaultfd_is_measured_or_explicitly_unavailable():
    subprocess.run(["make","-f","Makefile.wave2","metaram_uffd_bench_wave2"],cwd=ROOT,check=True)
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"pages.bin";p.write_bytes(b"Z"*4096*4);r=subprocess.run([str(ROOT/"metaram_uffd_bench_wave2"),"raw",str(p)],cwd=ROOT,capture_output=True,text=True)
        assert r.returncode in (0,77)
        if r.returncode==77:assert "USERFAULTFD_UNAVAILABLE" in r.stderr

def test_wave2_metafs_lineage_lazy_exact():
    import metafs_v3
    with tempfile.TemporaryDirectory() as td:
        td=Path(td);a=td/"a";b=td/"b";a.mkdir();b.mkdir();base=(b"node=17 cpu=42.000 latency=3.140 status=OK\n"*1800)[:65536];(a/"state.bin").write_bytes(base);q=bytearray(base)
        for i in range(100,500,37):q[i]^=0x11
        (b/"state.bin").write_bytes(q);img=td/"x.mfs3";st=metafs_v3.pack_snapshots([("a",100,a),("b",200,b)],img);im=metafs_v3.MetaFSImage(img,cache_limit=1)
        try:assert im.read_file("a","state.bin")==base;assert im.read_file("b","state.bin")==bytes(q)
        finally:im.close()
        assert st["ratio"]>1

def test_wave2_shared_cid_zero_duplicate_payload():
    import shared_cas,metaram_cas_bridge,metafs_v3
    with tempfile.TemporaryDirectory() as td:
        td=Path(td);cas=shared_cas.SharedCAS(td/"cas",policy="fast");bridge=metaram_cas_bridge.MetaRAMCASBridge(cas);snap=td/"snap";snap.mkdir()
        for i in range(8):
            page=bytes([i])*4096;(snap/f"page{i}.bin").write_bytes(page);ref=bridge.evict(1,i,1,1000+i,page);assert ref.cid==shared_cas.content_id(page)
        img=td/"shared.mfs3";st=metafs_v3.pack_snapshots([("s",2000,snap)],img,cas);assert st["external_unique_chunks"]==8 and st["superblocks"]==0
        out=td/"out";im=metafs_v3.MetaFSImage(img,cas)
        try:im.restore_snapshot("s",out)
        finally:im.close()
        assert metafs_v3.verify(snap,out)
