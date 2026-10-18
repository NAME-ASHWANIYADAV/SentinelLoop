"""Final decision matrix: specialist dims + reviewer deltas + synthesizer deltas, six weighting schemes, two-part evaluation."""
import json, statistics

DIMS = ['skill_fit', 'complete_prototype', 'measurable_results', 'demo_reliability', 'differentiation', 'data_availability',
        'free_tools_feasibility', 'engineering_depth', 'rubric_alignment', 'low_failure_risk', 'explainability', 'reproducible_evidence']
SCHEMES = {
    'base':     dict(zip(DIMS, [8, 12, 10, 10, 9, 8, 7, 8, 10, 8, 4, 6])),
    'equal':    {d: 100 / 12 for d in DIMS},
    'ambition': dict(zip(DIMS, [5, 10, 12, 7, 20, 8, 5, 15, 8, 4, 2, 4])),
    'safety':   dict(zip(DIMS, [6, 18, 8, 15, 1, 10, 10, 2, 10, 15, 1, 4])),
}
for k, w in SCHEMES.items():
    assert abs(sum(w.values()) - 100) < 1e-6, k

# Specialist raw dimension scores (from results/_matrix.json)
rows = json.load(open('results/_matrix.json', encoding='utf-8'))
raw = {r['case_id']: dict(r['dims']) for r in rows}

# Reviewer deltas, exactly as returned by the three adversarial reviewers (score_adjustments field)
reviewer = {
    1: {'differentiation': +0.5 - 0.5 - 1.0, 'low_failure_risk': -0.5, 'demo_reliability': +0.5 - 0.5, 'complete_prototype': -0.5},
    2: {'reproducible_evidence': -1.0, 'differentiation': +0.5, 'data_availability': -1.0, 'engineering_depth': -0.5},
    3: {'differentiation': +0.5, 'demo_reliability': -0.5, 'reproducible_evidence': -0.5, 'measurable_results': +0.5, 'low_failure_risk': -0.5, 'rubric_alignment': -0.5},
    4: {'rubric_alignment': -1.0, 'differentiation': +1.0, 'measurable_results': -1.0, 'demo_reliability': -0.5, 'low_failure_risk': -0.5},
    5: {'differentiation': -1.0, 'low_failure_risk': -1.0 - 0.5 - 0.5, 'data_availability': -1.0 - 0.5, 'demo_reliability': -1.0},
}
# Synthesizer deltas (mine), each with a stated reason
synth = {
    1: {'differentiation': (+0.5, 'competitor analysis found no public repo or verified hackathon winner with a leakage-free decision-replay evaluation of the triage agent as a maintenance policy')},
    2: {'skill_fit': (-2.0, 'specialist rated skill fit 8 but its own argument-against and both blind judges say 35% of the weight is battery-physics judgement the team cannot defend; 6 is consistent with the exec-adjusted 5.3 from both judges')},
    4: {'skill_fit': (-0.5, 'backend-heavy build fits, but two of seven criteria need regulatory-affairs judgement the team lacks (confirmed by HLS judge-domain finding)')},
    5: {},
    3: {},
}

adj = {}
for cid, d in raw.items():
    a = dict(d)
    for k, v in reviewer.get(cid, {}).items():
        a[k] = max(0, min(10, a[k] + v))
    for k, (v, _) in synth.get(cid, {}).items():
        a[k] = max(0, min(10, a[k] + v))
    adj[cid] = a

def weighted(scores, w):
    return sum(scores[d] * w[d] for d in DIMS) / 100

# Official-score potential: specialist + two blind judges
official = {}
execs = {}
for r in rows:
    cid = r['case_id']
    js_off = [x[1] for x in r['judges']]
    js_ex = [x[2] for x in r['judges']]
    official[cid] = {'specialist': r['spec_official'], 'judges': js_off, 'mean3': statistics.mean([r['spec_official']] + js_off), 'judges_mean': statistics.mean(js_off)}
    spec_exec = r['spec_exec']
    # technical skeptic explicitly re-rated execution-adjusted: cs1 7.6->7.3, cs3 7.0->7.1
    skeptic_exec = {1: 7.3, 3: 7.1}.get(cid, spec_exec)
    execs[cid] = {'specialist': spec_exec, 'skeptic': skeptic_exec, 'judges': js_ex, 'mean3': statistics.mean([skeptic_exec] + js_ex), 'judges_mean': statistics.mean(js_ex)}

titles = {1: 'Predictive Maintenance (C-MAPSS)', 2: 'Battery Design Platform', 3: 'Adaptive QoS Engine', 4: 'Medical Labeling Automation', 5: 'VehicleGPT on-device SLM'}

print('=== ADJUSTED DIMENSION SCORES (specialist + reviewer deltas + synthesizer deltas) ===')
print('case ' + ' '.join(f'{d[:6]:>6}' for d in DIMS))
for cid in sorted(adj):
    print(f'cs{cid}  ' + ' '.join(f'{adj[cid][d]:>6.1f}' for d in DIMS))

print('\n=== WEIGHTED CROSS-CASE SCORES (adjusted dims) ===')
print(f"{'case':<6}{'raw-base':>9}{'base':>7}{'equal':>7}{'ambit':>7}{'safety':>7}")
out = {}
for cid in sorted(adj):
    vals = {k: round(weighted(adj[cid], w), 2) for k, w in SCHEMES.items()}
    out[cid] = vals
    print(f"cs{cid:<4}{weighted(raw[cid], SCHEMES['base']):>9.2f}{vals['base']:>7.2f}{vals['equal']:>7.2f}{vals['ambition']:>7.2f}{vals['safety']:>7.2f}")

print('\n=== TWO-PART EVALUATION ===')
print(f"{'case':<6}{'off_spec':>9}{'off_jA':>7}{'off_jB':>7}{'off_mean':>9} | {'ex_spec':>8}{'ex_skep':>8}{'ex_jA':>7}{'ex_jB':>7}{'ex_mean':>8}")
for cid in sorted(adj):
    o, e = official[cid], execs[cid]
    print(f"cs{cid:<4}{o['specialist']:>9.1f}{o['judges'][1]:>7.1f}{o['judges'][0]:>7.1f}{o['mean3']:>9.2f} | {e['specialist']:>8.1f}{e['skeptic']:>8.1f}{e['judges'][1]:>7.1f}{e['judges'][0]:>7.1f}{e['mean3']:>8.2f}")

print('\n=== RISK-ADJUSTED FINAL = 0.35*official_mean + 0.35*exec_mean + 0.30*base_weighted_dims ===')
final = {}
for cid in sorted(adj):
    f = 0.35 * official[cid]['mean3'] + 0.35 * execs[cid]['mean3'] + 0.30 * out[cid]['base']
    final[cid] = round(f, 2)
for cid, f in sorted(final.items(), key=lambda x: -x[1]):
    print(f'cs{cid} {titles[cid]:<36} {f:.2f}')

print('\n=== SENSITIVITY: winner under each scheme ===')
def rank(d):
    return [c for c, _ in sorted(d.items(), key=lambda x: -x[1])]
for k in SCHEMES:
    print(f'{k:<10}', rank({c: out[c][k] for c in out}), {c: out[c][k] for c in rank({c: out[c][k] for c in out})})
print(f"{'rubric-only':<10}", rank({c: official[c]['mean3'] for c in official}), {c: round(official[c]['mean3'], 2) for c in official})
print(f"{'judges-only':<10}", rank({c: execs[c]['judges_mean'] for c in execs}), {c: round(execs[c]['judges_mean'], 2) for c in execs})
print(f"{'specialist-raw':<10}", rank({c: weighted(raw[c], SCHEMES['base']) for c in raw}), {c: round(weighted(raw[c], SCHEMES['base']), 2) for c in raw})
print(f"{'risk-adj':<10}", rank(final), final)

# Break-even: how much would cs3's adjusted base score need to rise to tie cs1 under base?
gap = out[1]['base'] - out[3]['base']
print(f"\nGap cs1-cs3 under base scheme: {gap:.2f} points; cs3 needs skill_fit +{gap/0.08:.1f} (impossible >10) or uniform +{gap:.2f} on every dimension to tie")
print('If a teammate has Linux-networking fluency: set cs3 skill_fit=9, low_failure_risk=8, demo_reliability=8 ->', round(weighted({**adj[3], 'skill_fit': 9, 'low_failure_risk': 8, 'demo_reliability': 8}, SCHEMES['base']), 2), 'vs cs1', out[1]['base'])
print('If a teammate has battery/thermal background: set cs2 skill_fit=9, engineering_depth=8, reproducible=8 ->', round(weighted({**adj[2], 'skill_fit': 9, 'engineering_depth': 8, 'reproducible_evidence': 8}, SCHEMES['base']), 2))
print('If a teammate has regulatory-affairs background: set cs4 skill_fit=9, measurable=8, low_failure_risk=8 ->', round(weighted({**adj[4], 'skill_fit': 9, 'measurable_results': 8, 'low_failure_risk': 8}, SCHEMES['base']), 2))
print('If the team owns a Raspberry Pi 5 and a Linux box: set cs5 demo=7, low_failure_risk=6.5, data=7.5 ->', round(weighted({**adj[5], 'demo_reliability': 7, 'low_failure_risk': 6.5, 'data_availability': 7.5}, SCHEMES['base']), 2))

json.dump({'adjusted_dims': adj, 'schemes': out, 'official': official, 'exec': execs, 'final': final, 'reviewer_deltas': reviewer, 'synth_deltas': {k: {d: v for d, (v, _) in vv.items()} for k, vv in synth.items()}}, open('results/_final.json', 'w', encoding='utf-8'), indent=1)
