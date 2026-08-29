#!/usr/bin/env python3
from pathlib import Path
import shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]

def test_metaram_build_and_run():
    subprocess.run(["make","clean"],cwd=ROOT,check=True);subprocess.run(["make"],cwd=ROOT,check=True)
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"mem.bin";p.write_bytes((b"\0"*4096+b"hello temporal memory"*200)*8)
        r=subprocess.run([str(ROOT/"metaram_bench"),str(p)],cwd=ROOT,check=True,capture_output=True,text=True)
        assert '"effective_ratio"' in r.stdout

def test_metafs_snapshots():
    import importlib.util,sys
    spec=importlib.util.spec_from_file_location("metafs_v2",ROOT/"metafs_v2.py");m=importlib.util.module_from_spec(spec);sys.modules["metafs_v2"]=m;spec.loader.exec_module(m)
    with tempfile.TemporaryDirectory() as td:
        td=Path(td);a=td/"a";b=td/"b";a.mkdir();b.mkdir();(a/"x.txt").write_bytes(b"hello"*5000);(a/"y.bin").write_bytes(bytes(8192));shutil.copy2(a/"x.txt",b/"x.txt");shutil.copy2(a/"y.bin",b/"y.bin")
        q=bytearray((b/"x.txt").read_bytes());q[100:110]=b"0123456789";(b/"x.txt").write_bytes(q);img=td/"x.mfs";st=m.pack_snapshots([("a",100,a),("b",200,b)],img);assert st["ratio"]>1
        ra=td/"ra";rb=td/"rb";m.restore_snapshot(img,"a",ra);m.restore_snapshot(img,"b",rb);assert m.verify(a,ra);assert m.verify(b,rb)

def test_temporal_store():
    import importlib.util,sys
    spec=importlib.util.spec_from_file_location("timeline",ROOT/"metaram_timeline.py");m=importlib.util.module_from_spec(spec);sys.modules["timeline"]=m;spec.loader.exec_module(m)
    s=m.TemporalPageStore();p=bytes(m.PAGE);q=bytearray(p);q[17]=5;q=bytes(q);s.publish(7,42,100,p);s.publish(7,42,200,q);s.publish(7,42,300,q)
    assert s.resolve(7,42,99) is None;assert s.resolve(7,42,150)==p;assert s.resolve(7,42,250)==q;assert s.resolve(7,42,350)==q
