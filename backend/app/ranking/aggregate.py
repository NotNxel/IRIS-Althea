from collections import defaultdict
import numpy as np
from app.differential.analyze import bh

def rank(records, scored, min_contexts=1):
    groups = defaultdict(lambda: defaultdict(list))
    for i, record in enumerate(records):
        if scored['eligible'][i]:
            key = (record['cell_line'], record['time'], record['dose'])
            groups[record['compound']][key].append(i)
    candidates = []
    for compound, contexts in groups.items():
        summary, nulls = [], []
        for key, ids in sorted(contexts.items()):
            value = float(np.mean(scored['scores'][ids]))
            summary.append(dict(cell_line=key[0], time=key[1], dose=key[2], dose_unit='Not supplied by GMT',
                score=value, signatures=len(ids), terms=[records[i]['term'] for i in ids],
                min_overlap=int(min(scored['overlap'][ids]))))
            if scored['null'] is not None:
                nulls.append(np.mean(scored['null'][ids], axis=0))
        supporting = sum(r['score'] < 0 for r in summary)
        if min_contexts > 1 and supporting < min_contexts:
            continue
        value = float(np.median([r['score'] for r in summary]))
        p = None
        if nulls:
            null = np.median(nulls, axis=0)
            p = float((1 + np.sum(null <= value)) / (len(null) + 1))
        candidates.append(dict(compound=compound, score=value, supporting_contexts=supporting,
            contexts=len(summary), supporting_signatures=sum(r['signatures'] for r in summary if r['score'] < 0),
            signatures=sum(r['signatures'] for r in summary), consistency=supporting / len(summary),
            context_details=summary, permutation_p=p, permutation_fdr=None,
            naive_overlap=float(np.mean([scored['overlap'][i] for ids in contexts.values() for i in ids])),
            interpretation='Computational reversal candidate for further investigation.' if value < 0 else 'No aggregate reversal under this configuration.'))
    candidates.sort(key=lambda r: (r['score'], r['compound']))
    if candidates and scored['null'] is not None:
        for candidate, fdr in zip(candidates, bh([r['permutation_p'] for r in candidates])):
            candidate['permutation_fdr'] = float(fdr)
    for i, candidate in enumerate(candidates):
        candidate['rank'] = i + 1
    return candidates
