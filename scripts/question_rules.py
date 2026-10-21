"""Keep teaching targets, join split underlines, and group discontinuous phrases.

Week 3 explanatory glosses are filtered by extract.py using the PDF's blue
teaching underlines. Do not apply that color rule to weeks 4-7.
"""
import hashlib
from itertools import groupby

# Actual sentence forms are intentional: learners select the inflected form.
PHRASES = {
    'kept … from': ('kept', 'from'),
    'prevent … from': ('prevent', 'from'),
    'inform … of': ('inform', 'of'),
    'notify … of': ('notify', 'of'),
    'reminded … of': ('reminded', 'of'),
    'provides … with': ('provides', 'with'),
    'provide … with': ('provide', 'with'),
    'is … equipped with': ('is', 'equipped with'),
    'was qualified for': ('was', 'qualified for'),
    'is in good condition': ('is', 'good condition'),
    'is … in use': ('is', 'in use'),
    'is … out of order': ('is', 'out of order'),
    'were … satisfied with': ('were', 'satisfied with'),
    'call a meeting': ('call', 'meeting'),
    'suit … needs': ('suit', "customer's needs"),
}

GROUP_MEANINGS = {
    'kept … from': '~가 …하지 못하게 막았다 (keep A from B)',
    'prevent … from': '~가 …하지 못하게 막다, 예방하다 (prevent A from B)',
    'inform … of': '~에게 …을 알리다 (inform A of B)',
    'notify … of': '~에게 …을 통보하다 (notify A of B)',
    'reminded … of': '~에게 …을 상기시켰다 (remind A of B)',
    'provides … with': '~에게 …을 제공한다 (provide A with B)',
    'provide … with': '~에게 …을 제공하다 (provide A with B)',
    'is … equipped with': '~을 갖추고 있다 (be equipped with)',
    'was qualified for': '~에 자격을 갖추고 있었다 (be qualified for)',
    'is in good condition': '상태가 좋다 (be in good condition)',
    'is … in use': '사용 중이다 (be in use)',
    'is … out of order': '고장 나 있다 (be out of order)',
    'were … satisfied with': '~에 만족했다 (be satisfied with)',
    'call a meeting': '회의를 소집하다',
    'suit … needs': '~의 요구를 충족시키다 (suit someone\'s needs)',
    "bachelor's degree": '학사 학위',
    'resume and cover letter': '이력서와 자기소개서',
}


def prepare_questions(questions):
    result = []
    key = lambda q: (q['file'], q['page'], q['sentence'])
    for _, source in groupby(questions, key):
        entries = sorted(source, key=lambda q: q['start'])
        sentence = entries[0]['sentence']
        # Underlines can split at spaces or at a PDF line wrap.
        runs = []
        for q in entries:
            if runs and not sentence[runs[-1]['end']:q['start']].strip():
                runs[-1]['end'] = q['end']
                runs[-1]['answer'] = sentence[runs[-1]['start']:q['end']]
            else:
                runs.append(dict(q))

        # These expressions are a single teaching target with intervening text.
        for label, parts in PHRASES.items():
            matches = [r for r in runs if r['answer'] in parts]
            if len(matches) != len(parts) or tuple(r['answer'] for r in matches) != parts:
                continue
            first, last = matches[0], matches[-1]
            if label in ('is in good condition', 'call a meeting'):
                # The PDF omits an internal preposition/article underline.
                blanks = [{'start': first['start'], 'end': last['end']}]
            elif label == 'suit … needs':
                # Keep the object visible: suit each customer's needs.
                blanks = [{'start': first['start'], 'end': first['end']},
                          {'start': last['end']-len('needs'), 'end': last['end']}]
            else:
                blanks = []
                for r in matches:
                    if blanks and not sentence[blanks[-1]['end']:r['start']].strip():
                        blanks[-1]['end'] = r['end']
                    else:
                        blanks.append({'start': r['start'], 'end': r['end']})
            combined = dict(first, blanks=blanks)
            combined['answer'] = ' … '.join(sentence[b['start']:b['end']] for b in blanks)
            combined['end'] = blanks[-1]['end']
            combined['groupMeaning'] = GROUP_MEANINGS[label]
            runs = [r for r in runs if r not in matches] + [combined]

        for q in sorted(runs, key=lambda q: q['start']):
            q.setdefault('blanks', [{'start': q['start'], 'end': q['end']}])
            # Change an ID only when the actual question changes. Existing
            # records for unmodified questions therefore remain usable.
            old = next((x for x in entries if x['start']==q['start'] and x['end']==q['end'] and x['answer']==q['answer']), None)
            if old is None:
                identity = hashlib.sha256(f"{q['file']}|{q['page']}|{sentence}|{q['blanks']}".encode()).hexdigest()[:12]
                q['id'] = f"w{q['week']}l{q['lesson']}p{q['page']}-{identity}"
            result.append(q)
    return result


def combine_sentence_questions(questions):
    """One question per example, retaining all eligible underline spans.

    Call after enrichment so each original target retains its own definition.
    Explanatory glosses have already been excluded during PDF extraction.
    """
    groups = {}
    for q in questions:
        groups.setdefault(q['sentence'], []).append(q)
    result = []
    for sentence, entries in groups.items():
        targets = sorted((t for q in entries for t in q.get('targets', [q])),
                         key=lambda t: t['start'])
        unique = {}
        for t in targets:
            spans = tuple((b['start'], b['end']) for b in t['blanks'])
            unique.setdefault(spans, t)
        targets = list(unique.values())
        q = dict(entries[0])
        q['targets'] = [{k: t[k] for k in ('answer', 'meaning', 'blanks', 'start', 'end')}
                        for t in targets]
        q['blanks'] = sorted((dict(b) for t in targets for b in t['blanks']),
                             key=lambda b: b['start'])
        q['start'], q['end'] = q['blanks'][0]['start'], q['blanks'][-1]['end']
        q['answer'] = ' … '.join(sentence[b['start']:b['end']] for b in q['blanks'])
        q['meaning'] = ' / '.join(t['meaning'] for t in targets)
        if len(targets) > 1:
            identity = hashlib.sha256(f"sentence|{sentence}|{q['blanks']}".encode()).hexdigest()[:12]
            q['id'] = f"w{q['week']}l{q['lesson']}p{q['page']}-{identity}"
        result.append(q)
    return result
