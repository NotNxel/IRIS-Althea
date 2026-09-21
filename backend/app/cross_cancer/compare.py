from itertools import combinations
from app.robustness.compare import compare_rankings

def compare(results, k=20):
    available = {key: value for key, value in results.items() if value.get('status') == 'complete'}
    rankings = {key: value['candidates'] for key, value in available.items()}
    compared = compare_rankings(rankings, k)
    signature_pairs = []
    for a, b in combinations(available, 2):
        row = dict(a=a, b=b)
        for arm in ['up', 'down']:
            ga = {g['gene'] for g in available[a]['signature'] if g['direction'] == arm}
            gb = {g['gene'] for g in available[b]['signature'] if g['direction'] == arm}
            row[arm + '_jaccard'] = len(ga & gb) / len(ga | gb) if ga | gb else None
        signature_pairs.append(row)
    top = {key: {r['compound'] for r in ranking[:k]} for key, ranking in rankings.items()}
    appearances = {}
    for key, compounds in top.items():
        for compound in compounds:
            appearances.setdefault(compound, []).append(key)
    return dict(**compared, signature_comparisons=signature_pairs,
                compounds=[dict(compound=c, analyses=v, cancer_count=len(v), cancer_specific=len(v) == 1) for c, v in sorted(appearances.items())],
                analyses=[dict(id=key, project=value.get('project'), status=value.get('status'), reason=value.get('error')) for key, value in results.items()],
                caveat='Specificity means exclusive to the selected top-k lists, not biological specificity.')
