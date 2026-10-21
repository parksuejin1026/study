import sys,json,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'.tools'))
import pymupdf
from question_rules import GROUP_MEANINGS
qs=json.loads((root/'questions.json').read_text(encoding='utf-8'))
sentences=list(dict.fromkeys(q['sentence'] for q in qs))
answers=list(dict.fromkeys(q['answer'] for q in qs))
curated=json.loads((root/'scripts/curated-ko.json').read_text(encoding='utf-8'))
definitions=curated['meanings']
definitions.update(GROUP_MEANINGS)
translations=curated['translations']
assert all(q.get('groupMeaning') or q['answer'] in definitions for q in qs),[q['answer'] for q in qs if not q.get('groupMeaning') and q['answer'] not in definitions]
docs={}
norm=lambda s:re.sub(r'\s+',' ',s).strip()
missing=[]
for q in qs:
 if q['sentence'] not in translations:
  key=(q['file'],q['page'])
  if key not in docs:
   p=pymupdf.open(root/q['file'])[q['page']-1]
   lines=[]
   for b in p.get_text('dict')['blocks']:
    for l in b.get('lines',[]):
     lines.append((''.join(s['text'] for s in l['spans']).strip(),l['bbox']))
   docs[key]=lines
  lines=docs[key]
  ends=[b[1] for t,b in lines if t and re.match('[A-Za-z]',t) and not re.search('[가-힣]',t) and norm(q['sentence']).endswith(norm(t))]
  if ends:
   y=max(ends)
   following=sorted([(t,b) for t,b in lines if b[1]>y+3 and b[0]<800],key=lambda x:x[1][1])
   korean=[];last=y
   for t,b in following:
    if re.match('[A-Za-z]',t) and not re.search('[가-힣]',t):break
    if re.search('[가-힣]',t) and b[1]-last<50:korean.append(t);last=b[1]
    elif korean:break
   if korean:translations[q['sentence']]=' '.join(korean)
  if q['sentence'] not in translations:missing.append(q['sentence'])
 q['translation']=translations.get(q['sentence'],'')
 q['meaning']=q.pop('groupMeaning',None) or definitions[q['answer']]
 q['translationSource']='학습용 보완 해석' if q['week']<=3 else 'PDF 수록 해석'
assert not missing,missing
for q in qs:
 if q['answer']=='addressed':q['meaning']='주소를 적었다' if 'envelope' in q['sentence'] else '연설했다'
(root/'questions.json').write_text(json.dumps(qs,ensure_ascii=False,indent=2),encoding='utf-8')
(root/'questions.js').write_text('window.QUESTIONS = '+json.dumps(qs,ensure_ascii=False)+';',encoding='utf-8')
print(f'Complete: {len(qs)} blanks, {len(sentences)} sentences, {len(answers)} definitions')
