'use strict';
const $=id=>document.getElementById(id), QUESTIONS=window.QUESTIONS, KEY='toeic-midterm-v1';
const escapeHTML=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state={version:1,items:{},exams:[],sessions:{}},session=null,position=0,noteId=null,timer=null,storageAvailable=true;
try{const saved=localStorage.getItem(KEY);if(saved){const parsed=JSON.parse(saved);if(parsed.version===1&&parsed.items&&Array.isArray(parsed.exams))state=parsed;}}catch{storageAvailable=false;}
const record=id=>state.items[id]||{};
state.sessions=state.sessions&&typeof state.sessions==='object'&&!Array.isArray(state.sessions)?state.sessions:{};
const questionById=new Map(QUESTIONS.map(q=>[q.id,q]));
function storedSession(title,s=state.sessions[title]){
 if(!s||s.revision!==2||!Array.isArray(s.ids)||!s.ids.length||new Set(s.ids).size!==s.ids.length||!Number.isInteger(s.position)||s.position<0||s.position>=s.ids.length||!Number.isFinite(s.started)||typeof s.mock!=='boolean'||(s.mock&&!Number.isFinite(s.deadline))||!s.answers||!s.options)return null;
 for(const id of s.ids){const q=questionById.get(id),options=s.options[id],a=s.answers[id];if(!q||!Array.isArray(options)||options.length!==4||!options.every(o=>o&&typeof o.answer==='string'&&typeof o.meaning==='string')||new Set(options.map(o=>o.answer)).size!==4||!options.some(o=>o.answer===q.answer&&o.meaning===q.meaning)||a&&(!options.some(o=>o.answer===a.choice)||a.correct!==(a.choice===q.answer)))return null;}
 return {...s,title,questions:s.ids.map(id=>questionById.get(id)),finished:false};
}
function rememberSession(){
 if(!session||session.finished)return;
 state.sessions[session.title]={revision:2,ids:session.questions.map(q=>q.id),position,answers:session.answers,options:session.options,mock:session.mock,started:session.started,deadline:session.deadline};
}
function resume(title){
 const saved=storedSession(title);if(!saved)return false;
 clearInterval(timer);session=saved;position=saved.position;state.activeSession=title;save();show('study');render();
 if(session.mock){tick();if(!session.finished)timer=setInterval(tick,1000);}else $('timer').textContent='';
 return true;
}
function blankSentence(q,html=false){
 let result='',cursor=0;
 const blanks=q.blanks||[{start:q.start,end:q.end}];
 for(const [i,{start,end}] of blanks.entries()){const text=q.sentence.slice(cursor,start),label=blanks.length>1?`(${i+1}) `:'';result+=(html?escapeHTML(text):text)+(html?`<span class="blank">${label}________</span>`:`${label}________`);cursor=end;}
 const tail=q.sentence.slice(cursor);return result+(html?escapeHTML(tail):tail);
}
function toast(message){$('toast').textContent=message;$('toast').style.display='block';clearTimeout(toast.timeout);toast.timeout=setTimeout(()=>$('toast').style.display='none',3500);}
function save(){rememberSession();try{localStorage.setItem(KEY,JSON.stringify(state));storageAvailable=true;return true;}catch{storageAvailable=false;toast('자동 저장을 사용할 수 없습니다. 기록 내보내기로 백업하세요.');return false;}}
function update(id,patch){state.items[id]={...record(id),...patch,updatedAt:new Date().toISOString()};return save();}
function shuffle(values){const a=[...values];for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
function show(view){for(const id of ['home','study','result'])$(id).hidden=id!==view;}
function dashboard(){
 $('total').textContent=new Set(QUESTIONS.map(q=>q.sentence)).size;
 $('attempted').textContent=QUESTIONS.filter(q=>record(q.id).attempts).length;
 $('wrong').textContent=QUESTIONS.filter(q=>record(q.id).wrong&&!record(q.id).mastered).length;
 $('mastered').textContent=QUESTIONS.filter(q=>record(q.id).mastered).length;
 $('scope-note').textContent=`예문 ${QUESTIONS.length}개 · ${QUESTIONS.length}문항. 예문마다 출제 표현을 여러 빈칸으로 함께 묻습니다. 문장에 뜻을 알려준 단어는 출제하지 않습니다.`;
 const resumable=Object.keys(state.sessions).filter(title=>storedSession(title));
 $('resume-list').replaceChildren();$('resume-panel').hidden=!resumable.length;
 for(const title of resumable){const saved=state.sessions[title],b=document.createElement('button');b.textContent=`${title} 이어 풀기 · ${saved.position+1}/${saved.ids.length}`;b.onclick=()=>resume(title);$('resume-list').append(b);}
 $('weeks').innerHTML='';
 const names={2:'어휘와 전치사의 연결',3:'토익 기본 어휘',4:'채용과 업무',5:'사무실과 직장 생활',6:'주차별 핵심 어휘',7:'주차별 핵심 어휘'};
 for(let week=2;week<=7;week++){
  const all=QUESTIONS.filter(q=>q.week===week),active=all.filter(q=>!record(q.id).mastered),done=all.filter(q=>record(q.id).mastered).length;
  const b=document.createElement('button');b.className='week-card';b.innerHTML=`<span class="number">WEEK ${String(week).padStart(2,'0')}</span><span class="arrow">↗</span><h3>${week}주차</h3><p>${names[week]}</p><p>예문 ${all.length}개 · ${all.length}문항</p><p>학습 가능 ${active.length} · 암기 완료 ${done}</p><div class="mini-progress"><i style="width:${done/all.length*100}%"></i></div>`;
  b.onclick=()=>start(active,`${week}주차 학습`,false);$('weeks').append(b);
 }
}
function optionsFor(q){
 const normalize=s=>s.toLowerCase().trim();
 const seen=new Set([normalize(q.answer)]),pool=[];
 const targets=q.targets||[q];
 // Replace a whole teaching expression, preserving the number/order of blanks.
 const candidates=shuffle(QUESTIONS.filter(x=>x.week===q.week&&x.lesson===q.lesson)).concat(shuffle(QUESTIONS));
 for(const source of candidates){
  for(const replacement of source.targets||[source]){
   for(const [i,target] of targets.entries()){
    if(replacement.blanks.length!==target.blanks.length)continue;
    const parts=targets.map((t,j)=>j===i?replacement:t),slots=[];
    for(const [j,t] of parts.entries())t.blanks.forEach((b,k)=>slots.push({start:targets[j].blanks[k].start,answer:(j===i?source.sentence:q.sentence).slice(b.start,b.end)}));
    const answer=slots.sort((a,b)=>a.start-b.start).map(s=>s.answer).join(' … '),key=normalize(answer);
    if(seen.has(key))continue;seen.add(key);pool.push({answer,meaning:parts.map(t=>t.meaning).join(' / ')});
    if(pool.length===3)return shuffle([{answer:q.answer,meaning:q.meaning},...pool]);
   }
  }
 }
 return shuffle([{answer:q.answer,meaning:q.meaning},...pool]);
}
function start(pool,title,mock){
 if(resume(title))return;
 if(!pool.length){toast('학습할 문제가 없습니다. 암기 완료 관리에서 문제를 해제할 수 있습니다.');return;}
 if(mock&&pool.length<35){toast(`모의고사를 시작하려면 예문이 35개 이상 필요합니다. 현재 ${pool.length}개입니다.`);return;}
 // Avoid asking multiple blanks from the same sentence within a mock exam.
 let selected=shuffle(pool);
 if(mock){const sentences=new Set();selected=selected.filter(q=>{if(sentences.has(q.sentence))return false;sentences.add(q.sentence);return true;});if(selected.length<35){toast('서로 다른 예문이 35개 이상 있어야 모의고사를 시작할 수 있습니다.');return;}selected=selected.slice(0,35);}
 session={title,mock,questions:selected,answers:{},options:{},started:Date.now(),deadline:mock?Date.now()+50*60*1000:null,finished:false};
 selected.forEach(q=>session.options[q.id]=optionsFor(q));position=0;state.activeSession=title;save();show('study');render();
 clearInterval(timer);if(mock){tick();timer=setInterval(tick,1000);}else $('timer').textContent='';
 $('study').scrollIntoView({behavior:'smooth',block:'start'});
}
function tick(){if(!session?.mock||session.finished)return;const seconds=Math.max(0,Math.ceil((session.deadline-Date.now())/1000));$('timer').textContent=`남은 시간 ${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`;if(!seconds)finish();}
function render(){
 const q=session.questions[position],a=session.answers[q.id];
 $('session-title').textContent=session.title;$('q-meta').textContent=`${q.week}주차 · ${q.lesson}교시 · PDF ${q.page}쪽`;$('position').textContent=`${position+1} / ${session.questions.length}`;
 $('bar').style.width=`${(position+1)/session.questions.length*100}%`;
 $('sentence').innerHTML=blankSentence(q,true);
 $('answer-guide').textContent=q.blanks.length>1?'빈칸 번호 순서대로 들어갈 표현을 고르세요.':'빈칸에 들어갈 표현을 고르세요.';
 $('options').innerHTML='';session.options[q.id].forEach((option,i)=>{
  const value=option.answer,b=document.createElement('button');b.innerHTML=`<span>${i+1}</span>${escapeHTML(value.split(' … ').map((part,j)=>q.blanks.length>1?`(${j+1}) ${part}`:part).join(' / '))}`;b.disabled=!!a;
  if(a&&value===q.answer)b.classList.add('correct');if(a&&a.choice===value&&value!==q.answer)b.classList.add('incorrect');
  b.onclick=()=>answer(q,value);$('options').append(b);
 });
 $('feedback').hidden=!a;
 if(a)$('feedback').innerHTML=`<h3>${a.correct?'정답입니다 ✓':'다시 기억해 보세요'}</h3><p><b>정답</b> ${escapeHTML(q.answer)} · ${escapeHTML(q.meaning||'뜻 확인 필요')}</p><p>${escapeHTML(q.translation||'해석 확인 필요')}</p><div class="option-meanings"><b>선지별 단어 뜻</b><ol>${session.options[q.id].map(o=>`<li><strong>${escapeHTML(o.answer)}</strong> · ${escapeHTML(o.meaning)}${o.answer===q.answer?' <small>(정답)</small>':''}</li>`).join('')}</ol></div><p><small>${escapeHTML(q.translationSource||'')}</small></p><a target="_blank" rel="noopener" href="${encodeURI(q.file)}#page=${q.page}">원본 PDF ${q.page}쪽 확인 ↗</a>`;
 $('memorize').checked=!!record(q.id).mastered;$('prev').disabled=position===0;$('next').disabled=!a&& !session.mock;
 $('next').textContent=position===session.questions.length-1?'학습 결과 보기 →':'다음 문제 →';
 $('note').textContent=record(q.id).note?'오답 노트 · 메모 있음':'오답 노트';
}
function answer(q,choice){if(session.answers[q.id])return;const correct=choice===q.answer;session.answers[q.id]={choice,correct};const prev=record(q.id);update(q.id,{attempts:(prev.attempts||0)+1,correctCount:(prev.correctCount||0)+(correct?1:0),wrong:!correct,lastChoice:choice});dashboard();render();}
function finish(){
 if(!session||session.finished)return;session.finished=true;clearInterval(timer);delete state.sessions[session.title];state.activeSession=null;save();
 const answered=Object.keys(session.answers).length,correct=Object.values(session.answers).filter(a=>a.correct).length,total=session.questions.length;
 const wrong=session.questions.filter(q=>!session.answers[q.id]?.correct);
 for(const q of wrong)if(!session.answers[q.id])update(q.id,{wrong:true});
 if(session.mock){state.exams.unshift({date:new Date().toISOString(),correct,total,answered,seconds:Math.round((Date.now()-session.started)/1000)});state.exams=state.exams.slice(0,100);save();}
 show('result');dashboard();$('result').innerHTML=`<div class="result-card"><p class="eyebrow">${session.mock?'MOCK EXAM':'STUDY'} COMPLETE</p><h2>${escapeHTML(session.title)} 결과</h2><div class="score">${correct}<small> / ${total}</small></div><p>정답률 ${Math.round(correct/total*100)}% · 오답 ${answered-correct}개 · 미응답 ${total-answered}개</p><button id="result-retry" class="primary">이번 오답·미응답 다시 풀기</button><button id="result-home">학습 목록으로</button><div class="result-list">${wrong.map(q=>`<p>${q.week}주차 ${q.lesson}교시 ${q.page}쪽 · ${escapeHTML(q.sentence)}<br><b>${escapeHTML(q.answer)}</b></p>`).join('')}</div></div>`;
 $('result-retry').onclick=()=>start(session.mock?wrong:wrong.filter(q=>!record(q.id).mastered),'이번 오답 다시 풀기',false);$('result-home').onclick=()=>show('home');$('result').scrollIntoView({behavior:'smooth'});
}
$('next').onclick=()=>{if(position===session.questions.length-1)finish();else{position++;save();render();}};
$('prev').onclick=()=>{if(position>0){position--;save();render();}};
$('exit').onclick=()=>{clearInterval(timer);state.activeSession=null;save();show('home');dashboard();};
$('mock').onclick=()=>start(QUESTIONS,'35문항 모의고사',true);
$('retry').onclick=()=>start(QUESTIONS.filter(q=>record(q.id).wrong&&!record(q.id).mastered),'오답만 다시 풀기',false);
$('memorize').onchange=e=>{update(session.questions[position].id,{mastered:e.target.checked});dashboard();};
$('note').onclick=()=>{const q=session.questions[position];noteId=q.id;$('note-context').textContent=`${q.week}주차 ${q.lesson}교시 · ${q.page}쪽 / ${blankSentence(q)}`;$('note-text').value=record(q.id).note||'';$('note-status').textContent='입력할 때 자동 저장됩니다.';$('note-dialog').showModal();};
$('note-text').oninput=()=>{$('note-status').textContent=update(noteId,{note:$('note-text').value})?'자동 저장됨':'저장 실패 · 기록 내보내기로 백업하세요.';};
$('note-close').onclick=()=>$('note-dialog').close();$('note-dialog').onclose=()=>{if(session&&!session.finished)render();};
$('records').onclick=()=>{$('history').innerHTML='<h3>최근 모의고사</h3>'+ (state.exams.length?state.exams.map(e=>`<p>${escapeHTML(new Date(e.date).toLocaleString('ko-KR'))} · ${e.correct}/${e.total} · ${Math.floor(e.seconds/60)}분 ${e.seconds%60}초</p>`).join(''):'<p>아직 모의고사 기록이 없습니다.</p>');$('storage-status').textContent=storageAvailable?'이 브라우저에 자동 저장 중입니다.':'자동 저장을 사용할 수 없습니다. 기록을 내보내세요.';$('records-dialog').showModal();};
$('export').onclick=()=>{const blob=new Blob([JSON.stringify({...state,exportedAt:new Date().toISOString()},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`toeic-study-${new Date().toISOString().slice(0,10)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('import').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{
 if(file.size>5*1024*1024)throw Error('파일이 너무 큽니다.');const data=JSON.parse(await file.text());if(data.version!==1||!data.items||typeof data.items!=='object'||Array.isArray(data.items)||!Array.isArray(data.exams))throw Error('지원하지 않는 기록 형식입니다.');
 const known=new Set(QUESTIONS.map(q=>q.id)),items={};
 for(const [id,r] of Object.entries(data.items)){
  if(!known.has(id))continue;if(!r||typeof r!=='object')throw Error('문제 기록이 올바르지 않습니다.');
  for(const key of ['attempts','correctCount'])if(r[key]!==undefined&&(!Number.isInteger(r[key])||r[key]<0))throw Error('학습 횟수가 올바르지 않습니다.');
  for(const key of ['mastered','wrong'])if(r[key]!==undefined&&typeof r[key]!=='boolean')throw Error('학습 상태가 올바르지 않습니다.');
  if(r.note!==undefined&&(typeof r.note!=='string'||r.note.length>100000))throw Error('메모가 올바르지 않습니다.');
  items[id]={attempts:r.attempts||0,correctCount:r.correctCount||0,mastered:!!r.mastered,wrong:!!r.wrong,note:r.note||'',updatedAt:new Date().toISOString()};
 }
 const exams=data.exams.filter(x=>x&&Number.isInteger(x.correct)&&Number.isInteger(x.total)&&x.correct>=0&&x.correct<=x.total&&x.total<=QUESTIONS.length&&Number.isFinite(x.seconds)&&x.seconds>=0&&!isNaN(Date.parse(x.date))).map(x=>({date:x.date,correct:x.correct,total:x.total,answered:x.answered||0,seconds:x.seconds}));
 state.items={...state.items,...items};state.exams=[...new Map([...exams,...state.exams].map(x=>[x.date,x])).values()].slice(0,100);const ok=save();dashboard();$('records-dialog').close();toast(ok?`${Object.keys(items).length}개 문제 기록을 가져왔습니다.`:'가져왔지만 브라우저 저장에 실패했습니다. 내보내기로 백업하세요.');
 }catch(error){toast(`가져오기 실패: ${error.message}`);}finally{e.target.value='';}};
$('manage').onclick=()=>{renderMastery();$('manage-dialog').showModal();};
function renderMastery(){const items=QUESTIONS.filter(q=>record(q.id).mastered);$('mastery-list').innerHTML='';if(!items.length){$('mastery-list').textContent='아직 암기 완료한 문제가 없습니다.';return;}for(const q of items){const row=document.createElement('div');row.className='mastery-row';const p=document.createElement('p');p.textContent=`${q.week}주차 ${q.lesson}교시 ${q.page}쪽 · ${q.answer}`;const b=document.createElement('button');b.textContent='해제';b.onclick=()=>{update(q.id,{mastered:false});dashboard();renderMastery();};row.append(p,b);$('mastery-list').append(row);}}
dashboard();
if(state.activeSession)resume(state.activeSession);
