"""Fixed authored examples only; never execute student text or model output."""
import json
from pathlib import Path
checks=[]
def check(name, actual, expected):
    assert actual == expected, (name, actual, expected)
    checks.append({'name':name,'actual':actual,'expected':expected})
check('str input digits',type('12').__name__,'str')
check('mixed numeric types',3+0.5,3.5)
check('string concatenation','12'+'3','123')
check('string repetition','a'*3,'aaa')
check('float int truncation',int(4.8),4)
check('negative float truncation',int(-4.8),-4)
for name, operation, expected in [('decimal string',lambda:int('4.8'),'ValueError'),('str plus int',lambda:'3'+2,'TypeError'),('zero step',lambda:range(0,4,0),'ValueError')]:
    try: operation(); actual='no error'
    except Exception as exc: actual=type(exc).__name__
    check(name,actual,expected)
check('negative range',list(range(-2,-8,-3)),[-2,-5])
for k in range(1,4):
    k=k+7
check('body modifies loop variable after final binding',k,10)
k=9
for k in range(4,4):
    k=k+1
check('empty loop preserves existing variable',k,9)
s=0
for n in range(1,4):
    s=s+n
check('sum before replacement',s,6)
s=2
check('following replacement',s,2)
for n in [-3,0,4]:
    s=0
    s=s+n
    check('conditional pair n='+str(n),s,n)
s=0
for i in range(3):
    s=s+i
s=s-10
check('Claude fragment versus whole program',s,-7)
t=0
for i in range(3):
    for i in range(3):
        t=t+1
    t=t+i
check('Claude nested loop separate from supported analyzer',t,15)
out={'passed':len(checks),'checks':checks,'scope':'fixed authored references, not arbitrary Python execution; nested loop is a negative analyzer-scope fixture'}
(Path(__file__).parent.parent/'logs'/'fact-reference-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(str(len(checks))+'/'+str(len(checks))+' native Python fact references passed')
