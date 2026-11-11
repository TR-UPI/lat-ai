"""Only literal authored examples from E01_PAIRS.txt. No arbitrary code execution."""
from pathlib import Path
import json
checks=[]
def check(name,actual,expected):
 assert actual==expected,(name,actual,expected)
 checks.append({'name':name,'actual':actual,'expected':expected})
check('E01 input value text','3'+'2','32')
check('E01 converted sum',int('3')+2,5)
check('E01 mixed numeric',3+0.5,3.5)
check('E01 transfer concatenation','12'+'7','127')
check('E01 transfer sum',int('12')+7,19)
for value in ['4.2','-4.8']:
 try:int(value);actual='no exception'
 except ValueError:actual='ValueError'
 check('P04 decimal string '+value,actual,'ValueError')
check('P04 numeric float',int(4.2),4)
check('P04 negative numeric float',int(-4.8),-4)
states=[];total=0
for i in range(2,5):
 total=0;total=total+i;states.append(total)
check('N02 reset-zero states',states,[2,3,4])
check('N02 result',total,4)
states=[];total=0
for i in range(2,5):
 total=5;total=total+i;states.append(total)
check('N02 transfer reset-five states',states,[7,8,9])
states=[]
for total in range(3):
 total=total+5;states.append(total)
check('N09 loop rebind states',states,[5,6,7])
states=[]
for total in range(3):
 total=total+2;states.append(total)
check('N09 transfer rebind states',states,[2,3,4])
def fresh_empty():
 for i in range(0):x=1
 return i
try:fresh_empty();error='no exception'
except NameError as e:error=isinstance(e,NameError)
check('P07 undefined local is NameError subclass',error,True)
i=9
for i in range(0):x=1
check('P07 existing name preserved',i,9)
result={'passed':len(checks),'total':len(checks),'checks':checks,'note':'P07 exact top-level NameError separately verified by fixed semantic-counterexamples.py; this local helper checks subclass only'}
(Path(__file__).parents[1]/'logs/e01-pair-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(f'{len(checks)}/{len(checks)} E01 authored example checks passed')
