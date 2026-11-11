"""Independent fixed counterexamples for grading; no model/student text is executed."""
import json, subprocess, sys
from pathlib import Path
fixtures=[
 ('reset each iteration','s=0\nfor n in range(1,4):\n    s=0\n    s=s+n\nprint(s)\n','3\n',None),
 ('for rebinds target','for total in range(3):\n    total=total+5\nprint(total)\n','7\n',None),
 ('undefined target after empty loop','for i in range(0):\n    print(i)\nprint(i)\n','', 'NameError'),
 ('for has no own local scope','for i in range(2):\n    pass\nprint(i)\n','1\n',None),
 ('range object type','print(type(range(5,2)).__name__)\n','range\n',None),
 ('SyntaxError without indentation issue','if True print(1)\n','', 'SyntaxError'),
 ('two space indentation permitted','if True:\n  print(1)\n','1\n',None),
 ('int truncates instead of nearest rounding','print(int(8.8), round(8.8))\n','8 9\n',None),
 ('integer division accepts floats','print(3.0 // 2.0)\n','1.0\n',None),
 ('finite guard infinity','print(int(float("inf")))\n','', 'OverflowError'),
 ('finite guard nan','print(int(float("nan")))\n','', 'ValueError'),
 ('zero n remains zero','n=0\ns=0\ns=s+n\nprint(s)\n','0\n',None)
]
rows=[]
for name,code,stdout,error in fixtures:
    p=subprocess.run([sys.executable,'-I','-X','utf8','-c',code],capture_output=True,text=True,encoding='utf-8',timeout=2)
    assert p.stdout==stdout,(name,p.stdout)
    assert (p.returncode!=0 and error in p.stderr) if error else p.returncode==0,(name,p.stderr)
    rows.append({'name':name,'code':code,'stdout':p.stdout,'expected_error':error,'returncode':p.returncode,'passed':True})
out={'passed':len(rows),'total':len(rows),'scope':'fixed authored counterexamples only; no assertions about all Python or prose semantics','results':rows}
(Path(__file__).parent.parent/'logs'/'semantic-counterexamples.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(str(len(rows))+'/'+str(len(rows))+' semantic counterexamples verified by native Python')
