import json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
qs=json.loads((root/'questions.json').read_text(encoding='utf-8'))
assert len({q['id'] for q in qs})==len(qs)
for q in qs:
 assert q['sentence'][q['start']:q['end']]==q['answer'],q
 assert q['translation'] and q['meaning'],q
 assert (root/q['file']).is_file()
 assert q['week'] in range(2,8)
 assert q['week']!=2 or (q['lesson']==1 and q['page'] in range(5,14))
rows=['# PDF 학습 범위 대조표','','예문 236개와 빈칸 425개는 서로 다른 집계입니다. 한 예문에 여러 밑줄이 있으면 각각 학습합니다. 분리된 밑줄을 임의로 합치지 않았습니다.','', '| 주차 | 예문 | 밑줄 빈칸 |','|---|---:|---:|']
for w in range(2,8):
 a=[q for q in qs if q['week']==w]
 rows.append(f'| {w} | {len(set(q["sentence"] for q in a))} | {len(a)} |')
for file in dict.fromkeys(q['file'] for q in qs):
 rows+=['','## '+file]
 for page in dict.fromkeys(q['page'] for q in qs if q['file']==file):
  rows+=['',f'### PDF {page}쪽','']
  for sentence in dict.fromkeys(q['sentence'] for q in qs if q['file']==file and q['page']==page):
   blanks=[q['answer'] for q in qs if q['file']==file and q['page']==page and q['sentence']==sentence]
   rows+=['- '+sentence+'\n  - 밑줄: '+ ' / '.join(blanks)]
(root/'범위검증.md').write_text('\n'.join(rows),encoding='utf-8')
files=['index.html','style.css','app.js','questions.js','questions.json','README.md','범위검증.md','.nojekyll']+list(dict.fromkeys(q['file'] for q in qs))
with zipfile.ZipFile(root/'toeic-study.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in files:z.write(root/name,name)
print(f'Validated {len(qs)} questions, all answers and translations present. Packaged {len(files)} files into toeic-study.zip')
