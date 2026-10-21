import json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
qs=json.loads((root/'questions.json').read_text(encoding='utf-8'))
assert len({q['id'] for q in qs})==len(qs)
assert len({q['sentence'] for q in qs})==len(qs)
for q in qs:
 blanks=q['blanks']
 assert blanks and all(0<=b['start']<b['end']<=len(q['sentence']) for b in blanks),q
 assert all(a['end']<=b['start'] for a,b in zip(blanks,blanks[1:])),q
 assert ' … '.join(q['sentence'][b['start']:b['end']] for b in blanks)==q['answer'],q
 assert q['translation'] and q['meaning'],q
 assert (root/q['file']).is_file()
 assert q['week'] in range(2,8)
 assert q['week']!=2 or (q['lesson']==1 and q['page'] in range(5,14))
rows=['# PDF 학습 범위 대조표','',f'예문 {len(set(q["sentence"] for q in qs))}개 · {len(qs)}문항. 예문 하나당 한 문제로 모든 출제 표현을 함께 비웁니다. 문장에 뜻을 알려준 설명용 단어는 제외합니다. 아래 … 표시는 사이의 문장을 남기는 분리 빈칸입니다.','', '| 주차 | 예문 | 문항 |','|---|---:|---:|']
for w in range(2,8):
 a=[q for q in qs if q['week']==w]
 rows.append(f'| {w} | {len(set(q["sentence"] for q in a))} | {len(a)} |')
for file in dict.fromkeys(q['file'] for q in qs):
 rows+=['','## '+file]
 for page in dict.fromkeys(q['page'] for q in qs if q['file']==file):
  rows+=['',f'### PDF {page}쪽','']
  for sentence in dict.fromkeys(q['sentence'] for q in qs if q['file']==file and q['page']==page):
   blanks=[q['answer'] for q in qs if q['file']==file and q['page']==page and q['sentence']==sentence]
   rows+=['- '+sentence+'\n  - 출제 표현: '+ ' / '.join(blanks)]
(root/'범위검증.md').write_text('\n'.join(rows),encoding='utf-8')
files=['index.html','style.css','app.js','questions.js','questions.json','README.md','범위검증.md','.nojekyll']+list(dict.fromkeys(q['file'] for q in qs))
with zipfile.ZipFile(root/'toeic-study.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in files:z.write(root/name,name)
print(f'Validated {len(qs)} questions, all answers and translations present. Packaged {len(files)} files into toeic-study.zip')
