"""Parse the workflow journal, dump each agent's structured result to JSON files, and compute the decision matrices."""
import json, sys, os, statistics

JOURNAL = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)

DIMS = ['skill_fit', 'complete_prototype', 'measurable_results', 'demo_reliability', 'differentiation', 'data_availability',
        'free_tools_feasibility', 'engineering_depth', 'rubric_alignment', 'low_failure_risk', 'explainability', 'reproducible_evidence']
BASE = dict(zip(DIMS, [8, 12, 10, 10, 9, 8, 7, 8, 10, 8, 4, 6]))
EQUAL = {d: 100 / 12 for d in DIMS}
AMBITION = dict(zip(DIMS, [5, 10, 12, 7, 20, 8, 5, 15, 8, 4, 2, 4]))
SAFETY = dict(zip(DIMS, [6, 18, 8, 15, 1, 10, 10, 2, 10, 15, 1, 4]))
for w in (BASE, AMBITION, SAFETY):
    assert abs(sum(w.values()) - 100) < 1e-6, sum(w.values())

labels = {}
results = {}
with open(JOURNAL, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        t = rec.get('type')
        if t == 'started':
            labels[rec.get('key')] = rec.get('label')
        elif t in ('completed', 'result', 'finished', 'done'):
            key = rec.get('key')
            labels.setdefault(key, rec.get('label'))
            results[labels.get(key) or key] = rec.get('result', rec.get('value', rec))
        else:
            pass

print('journal record types seen; results captured for labels:', sorted(results.keys()))
for label, res in results.items():
    safe = label.replace(':', '_').replace('/', '_')
    with open(os.path.join(OUT, safe + '.json'), 'w', encoding='utf-8') as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)

specialists = {res['case_id']: res for lab, res in results.items() if lab.startswith('specialist:') and isinstance(res, dict) and 'case_id' in res}
judges = [res for lab, res in results.items() if lab.startswith('judge:') and isinstance(res, dict)]
reviews = [res for lab, res in results.items() if lab.startswith('review:') and isinstance(res, dict)]
verifs = [res for lab, res in results.items() if lab.startswith('verify:') and isinstance(res, dict)]
compet = [res for lab, res in results.items() if lab.startswith('competitor:') and isinstance(res, dict)]

def weighted(scores, w):
    return sum(scores[d] * w[d] for d in DIMS) / 100

rows = []
for cid in sorted(specialists):
    s = specialists[cid]
    ds = {d: float(s['dimension_scores'][d]) for d in DIMS}
    js = []
    for j in judges:
        for c in j['candidates']:
            if c['case_id'] == cid:
                js.append((j['judge_persona'][:40], c['official_score_potential_0_10'], c['execution_adjusted_0_10'], c['confidence']))
    rk = []
    for r in reviews:
        for x in r['ranking']:
            if x['case_id'] == cid:
                rk.append((r['role'], x['rank']))
    adj = [(r['role'], a['dimension'], a['delta'], a['reason'][:80]) for r in reviews for a in r['score_adjustments'] if a['case_id'] == cid]
    vs = [(v['verdict'], v['claim'][:90]) for v in verifs if v['case_id'] == cid]
    rows.append({
        'case_id': cid,
        'title': s['case_title'],
        'spec_official': s['official_score_potential_0_10'],
        'spec_exec': s['execution_adjusted_0_10'],
        'spec_conf': s['confidence'],
        'dims': ds,
        'base': round(weighted(ds, BASE), 2),
        'equal': round(weighted(ds, EQUAL), 2),
        'ambition': round(weighted(ds, AMBITION), 2),
        'safety': round(weighted(ds, SAFETY), 2),
        'judges': js,
        'judge_official_mean': round(statistics.mean([x[1] for x in js]), 2) if js else None,
        'judge_exec_mean': round(statistics.mean([x[2] for x in js]), 2) if js else None,
        'reviewer_ranks': rk,
        'adjustments': adj,
        'verifications': vs,
    })

print('\n=== SPECIALIST DIMENSION SCORES ===')
print('case ' + ' '.join(f'{d[:6]:>6}' for d in DIMS) + '   base  equal ambit safety')
for r in rows:
    print(f"cs{r['case_id']}  " + ' '.join(f"{r['dims'][d]:>6.1f}" for d in DIMS) + f"  {r['base']:>5} {r['equal']:>5} {r['ambition']:>5} {r['safety']:>5}")

print('\n=== OFFICIAL-SCORE POTENTIAL / EXECUTION-ADJUSTED ===')
for r in rows:
    print(f"cs{r['case_id']}: specialist official={r['spec_official']} exec={r['spec_exec']} conf={r['spec_conf']} | judges={r['judges']} | judge_off_mean={r['judge_official_mean']} judge_exec_mean={r['judge_exec_mean']}")

print('\n=== REVIEWER RANKS / ADJUSTMENTS / VERIFICATIONS ===')
for r in rows:
    print(f"cs{r['case_id']}: ranks={r['reviewer_ranks']}")
    for a in r['adjustments']:
        print('   adj', a)
    for v in r['verifications']:
        print('   verify', v)

print('\n=== JUDGE RANKINGS ===')
for j in judges:
    print(j['judge_persona'][:60], '->', j['ranking'])
print('\n=== REVIEWER RANKINGS ===')
for r in reviews:
    print(r['role'], '->', sorted([(x['rank'], x['case_id']) for x in r['ranking']]))

with open(os.path.join(OUT, '_matrix.json'), 'w', encoding='utf-8') as fh:
    json.dump(rows, fh, indent=1, ensure_ascii=False)
print('\nwrote', os.path.join(OUT, '_matrix.json'), '| specialists', len(specialists), 'judges', len(judges), 'reviews', len(reviews), 'verifs', len(verifs), 'competitor', len(compet))
