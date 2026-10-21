"""Browser regressions: python scripts/check_app.py (requires Playwright + Chrome)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools'))
from playwright.sync_api import sync_playwright

questions = json.loads((ROOT / 'questions.json').read_text(encoding='utf-8'))
assert len({q['id'] for q in questions}) == len(questions)
assert len({q['sentence'] for q in questions}) == 236
assert len([q for q in questions if q['week'] == 3]) == 69
occur = [q for q in questions if 'occur unexpectedly' in q['sentence']]
assert len(occur) == 1 and occur[0]['answer'] == 'occur'
assert not any(q['answer'] == 'unexpectedly' for q in questions)
assert all(q['meaning'] and q['translation'] for q in questions)
for q in questions:
    assert ' … '.join(q['sentence'][b['start']:b['end']] for b in q['blanks']) == q['answer']
    assert all(a['end'] <= b['start'] for a, b in zip(q['blanks'], q['blanks'][1:]))
for expression in ['kept … from', 'prevent … from', 'inform … of', 'notify … of', 'provide … with', 'is … equipped with']:
    assert any(q['answer'] == expression and len(q['blanks']) == 2 for q in questions), expression

(ROOT / '.qa').mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(viewport={'width': 1200, 'height': 1000})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto((ROOT / 'index.html').as_uri())
    page.evaluate('localStorage.clear()')
    page.reload()
    assert page.locator('#weeks button').count() == 6
    page.locator('#weeks button').first.click()
    assert page.locator('#feedback').is_hidden()
    # Force a real discontinuous expression so its displayed blanks and note
    # context are checked, rather than relying on random selection.
    page.evaluate("position=session.questions.findIndex(q=>q.answer==='kept … from');save();render()")
    assert page.locator('#sentence .blank').count() == 2
    assert ' me ' in page.locator('#sentence').inner_text()
    page.locator('#note').click()
    assert page.locator('#note-context').inner_text().count('________') == 2
    page.locator('#note-text').fill('keep A from B 전체를 기억하기')
    page.locator('#note-close').click()
    # Wrong answer still reveals all four definitions in the same order.
    wrong_index = page.evaluate('session.options[session.questions[position].id].findIndex(o=>o.answer!==session.questions[position].answer)')
    page.locator('#options button').nth(wrong_index).click()
    assert page.locator('.option-meanings li').count() == 4
    expected = page.evaluate('session.options[session.questions[position].id]')
    for i, option in enumerate(expected):
        assert option['answer'] in page.locator('.option-meanings li').nth(i).inner_text()
        assert option['meaning'] in page.locator('.option-meanings li').nth(i).inner_text()
    saved_position = page.locator('#position').inner_text()
    saved_options = page.locator('#options').inner_text()
    page.reload()
    assert page.locator('#study').is_visible()
    assert page.locator('#position').inner_text() == saved_position
    assert page.locator('#options').inner_text() == saved_options
    assert page.locator('.option-meanings li').count() == 4
    assert page.locator('#options button.incorrect').count() == 1
    page.screenshot(path=str(ROOT / '.qa' / 'feedback-desktop.png'), full_page=True)
    # Resume even when the current problem was just marked mastered.
    page.locator('#memorize').check()
    page.locator('#exit').click()
    assert page.locator('#resume-panel').is_visible()
    page.locator('#weeks button').first.click()
    assert page.locator('#position').inner_text() == saved_position
    assert page.locator('#memorize').is_checked()
    # An unanswered problem, previous/next navigation, and closing the page.
    page.evaluate('position=0;save();render()')
    if page.locator('#feedback').is_hidden():
        page.locator('#options button').first.click()
    page.locator('#next').click()
    saved_sentence = page.locator('#sentence').inner_text()
    saved_options = page.locator('#options').inner_text()
    page.close()
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto((ROOT / 'index.html').as_uri())
    assert page.locator('#position').inner_text().startswith('2 /')
    assert page.locator('#sentence').inner_text() == saved_sentence
    assert page.locator('#options').inner_text() == saved_options
    page.locator('#exit').click()
    page.locator('#weeks button').nth(1).click()
    page.locator('#exit').click()
    assert page.locator('#resume-list button').count() == 2
    # Mock timer retains its absolute deadline across leaving/reloading.
    page.locator('#mock').click()
    deadline = page.evaluate('session.deadline')
    page.locator('#next').click()
    page.reload()
    assert page.evaluate('session.deadline') == deadline
    assert page.locator('#position').inner_text() == '2 / 35'
    page.evaluate('session.deadline=Date.now()-1;save()')
    page.reload()
    assert page.locator('#result').is_visible()
    assert page.evaluate('state.exams.length') == 1
    assert page.evaluate("!state.sessions['35문항 모의고사']")
    page.reload()
    assert page.evaluate('state.exams.length') == 1
    # Completing ordinary study removes its resume slot as well.
    page.locator('#resume-list button').filter(has_text='2주차').click()
    page.evaluate('position=session.questions.length-1;save();render()')
    if page.locator('#feedback').is_hidden():
        page.locator('#options button').first.click()
    page.locator('#next').click()
    assert page.locator('#result').is_visible()
    assert page.evaluate("!state.sessions['2주차 학습']")
    # Old study records survive loading the new application.
    known = questions[0]['id']
    page.evaluate("""id => {localStorage.setItem(KEY,JSON.stringify({version:1,items:{[id]:{attempts:2,note:'기존 메모',mastered:true}},exams:[]}))}""", known)
    page.reload()
    assert page.evaluate('(id)=>record(id).note', known) == '기존 메모'
    assert page.locator('#mastered').inner_text() == '1'
    # Malformed progress should not prevent loading or starting a new session.
    page.evaluate("""() => {state.sessions.broken={revision:2,ids:[QUESTIONS[0].id],position:0,started:Date.now(),mock:false,options:{[QUESTIONS[0].id]:[null,null,null,null]},answers:{}};state.activeSession='broken';save()}""")
    page.reload()
    assert page.locator('#home').is_visible()
    page.locator('#weeks button').nth(1).click()
    # Correct answer and mobile presentation.
    page.evaluate("answer(session.questions[position],session.questions[position].answer)")
    assert page.locator('#options button.correct').count() == 1
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(ROOT / '.qa' / 'feedback-mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors, errors
    browser.close()
print(f'PASS: {len(questions)} questions; grouped blanks, option meanings, notes, resume, legacy records, and mock expiry.')
