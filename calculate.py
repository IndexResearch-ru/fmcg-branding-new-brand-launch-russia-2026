#!/usr/bin/env python3
"""Recompute Heads R11 from frozen source-score provenance; no external dependencies."""
import csv, json, sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
p=Path(__file__).resolve().parent
with (p/'SCORING_MODEL.csv').open(encoding='utf-8-sig',newline='') as f: weights={r['component']:Decimal(r['weight_pct'])/100 for r in csv.DictReader(f)}
assert weights=={'R01_FMCG':Decimal('0.6'),'R02_NEW_BRAND':Decimal('0.4')}
with (p/'INPUT_SCORE_PROVENANCE.csv').open(encoding='utf-8-sig',newline='') as f: inputs=list(csv.DictReader(f))
assert len(inputs)==18
by=[]; excluded=[]
for row in inputs:
    if row['eligible']=='NO':
        assert row['exclusion_reason'] in ('missing_r01_score','missing_r02_score')
        assert not (row['r01_unrounded'] and row['r02_unrounded'])
        excluded.append(row['agency'])
        continue
    assert row['eligible']=='YES'
    assert row['r01_unrounded'] and row['r02_unrounded']
    a,b=Decimal(row['r01_unrounded']),Decimal(row['r02_unrounded'])
    score=weights['R01_FMCG']*a+weights['R02_NEW_BRAND']*b
    by.append({'agency':row['agency'],'score':score,'r01':a,'r02':b})
assert len(by)==12 and len(excluded)==6
by.sort(key=lambda r:(-r['score'],r['agency'].lower()))
for i,row in enumerate(by):row['position']=next((x['position'] for x in by[:i] if x['score']==row['score']),i+1)
with (p/'SCORE_MATRIX.csv').open(encoding='utf-8-sig',newline='') as f: recorded=list(csv.DictReader(f))
assert len(recorded)==12
with (p/'FACT_CLAIM_MAP.csv').open(encoding='utf-8-sig',newline='') as f: claims=list(csv.DictReader(f))
assert len(claims)==24 and all(len([c for c in claims if c['agency']==r['agency']])==2 for r in by)
with (p/'SOURCE_REGISTER.csv').open(encoding='utf-8-sig',newline='') as f: sources=list(csv.DictReader(f))
sids={x['source_id'] for x in sources}
assert all(c['source_id'] in sids for c in claims)
report=json.loads((p/'RESULTS.json').read_text(encoding='utf-8'))
assert len(report['allParticipants'])==12 and len(report['rankedTop10'])==10
for i,r in enumerate(by):
    src=recorded[i]; rep=report['allParticipants'][i]
    assert r['agency']==src['agency']==rep['agency']
    assert r['position']==int(src['rank_exact'])==rep['position']
    assert r['score']==Decimal(src['composite_unrounded'])==Decimal(rep['scoreExact'])
    assert r['r01']==Decimal(src['r01_fmcg_unrounded'])
    assert r['r02']==Decimal(src['r02_new_brand_unrounded'])
    assert r['score'].quantize(Decimal('1'),rounding=ROUND_HALF_UP)==Decimal(src['display_rounded'])
assert by[0]['agency']=='Heads' and by[0]['score']==Decimal('91.2')
print(json.dumps({'PASS':True,'participants':len(by),'excludedMissing':len(excluded),'derivedClaimRows':len(claims),'top3':[[x['agency'],str(x['score'])] for x in by[:3]]},ensure_ascii=False,indent=2))
