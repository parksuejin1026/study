import sys, re, json, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'.tools'))
import pymupdf
root=Path(__file__).resolve().parents[1]
questions=[]
for file in sorted(root.glob('*.pdf')):
 week,lesson=map(int,re.search(r'_(\d+)\D+_(\d+)',file.name).groups())
 if week==2 and lesson==2: continue
 for page_no,p in enumerate(pymupdf.open(file),1):
  text=p.get_text()
  if week>2 and ('기본단어다지기' not in text or '문맥' in text):continue
  if week==2 and not 5<=page_no<=13:continue
  lines=[]
  for b in p.get_text('rawdict')['blocks']:
   for l in b.get('lines',[]):
    chars=[c for s in l['spans'] for c in s['chars']]
    t=''.join(c['c'] for c in chars).strip()
    if t:lines.append((t,chars,l['bbox']))
  under=[d['rect'] for d in p.get_drawings() if 0<d['rect'].height<1.6 and d['rect'].width>4]
  sentences=[]; current=[]
  for t,chars,box in lines:
   if re.match(r'^[A-Za-z]',t) and not re.search('[가-힣:]',t) and (len(t.split())>=3 or current) and not t.startswith(('Collocation','CV(')):
    current+=chars
    if re.search(r'[.!?]["”]?$',t):sentences.append(current);current=[]
   else:
    if current:sentences.append(current);current=[]
  if current:sentences.append(current)
  for chars in sentences:
   sentence=''.join(c['c'] for c in chars)
   # Separate wrapped lines without disturbing character offsets.
   expanded=[]
   for c in chars:
    if expanded and c['origin'][1]-expanded[-1]['origin'][1]>5:expanded.append(dict(c,c=' '))
    expanded.append(c)
   chars=expanded;sentence=''.join(c['c'] for c in chars).strip()
   if len(sentence.split())<5:continue
   spans=[]
   for u in under:
    ids=[i for i,c in enumerate(chars) if c['c'].strip() and u.x0-1<=(c['bbox'][0]+c['bbox'][2])/2<=u.x1+1 and 0<u.y0-c['origin'][1]<5]
    if ids:spans.append((min(ids),max(ids)+1))
   for start,end in sorted(set(spans)):
    while end>start and chars[end-1]['c'] in ' .,;:!?':end-=1
    while start<end and chars[start]['c'].isspace():start+=1
    answer=''.join(c['c'] for c in chars[start:end]).strip()
    if not re.search('[A-Za-z]',answer):continue
    after=[t for t,_,b in lines if b[1]>chars[-1]['bbox'][1] and re.search('[가-힣]',t)]
    translation=after[0] if after and chars[-1]['bbox'][1]+65>next(b[1] for t,_,b in lines if t==after[0]) else ''
    prior=[t for t,_,b in lines if b[1]<chars[0]['bbox'][1] and re.search('[가-힣]',t) and b[1]>chars[0]['bbox'][1]-90 and not any(x in t for x in ['다지기','예문','어휘'])]
    identity=hashlib.sha256(f'{file.name}|{page_no}|{sentence}|{start}|{end}'.encode()).hexdigest()[:12]
    questions.append(dict(id=f'w{week}l{lesson}p{page_no}-{identity}',week=week,lesson=lesson,page=page_no,file=file.name,sentence=sentence,answer=answer,start=start,end=end,meaning=prior[-1] if prior else '',translation=translation))
(root/'questions.json').write_text(json.dumps(questions,ensure_ascii=False,indent=2),encoding='utf-8')
(root/'questions.js').write_text('window.QUESTIONS = '+json.dumps(questions,ensure_ascii=False)+';',encoding='utf-8')
print('Questions:',len(questions))
for w in range(2,8):print(w,sum(q['week']==w for q in questions))
