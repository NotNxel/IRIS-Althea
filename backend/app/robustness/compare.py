from collections import defaultdict
from itertools import combinations
import numpy as np
from scipy.stats import spearmanr

def compare_rankings(rankings, k=20):
    comparisons = []
    for a, b in combinations(rankings, 2):
        aa = {r['compound']: r['rank'] for r in rankings[a]}
        bb = {r['compound']: r['rank'] for r in rankings[b]}
        top_a, top_b = set(list(aa)[:k]), set(list(bb)[:k])
        common = sorted(aa.keys() & bb.keys())
        rho = spearmanr([aa[c] for c in common], [bb[c] for c in common]).statistic if len(common) > 1 else float('nan')
        comparisons.append(dict(a=a, b=b, top_k=k, overlap=len(top_a & top_b),
            jaccard=len(top_a & top_b) / len(top_a | top_b) if top_a | top_b else None,
            rank_correlation=float(rho) if np.isfinite(rho) else None, common_candidates=len(common)))
    collected = defaultdict(dict)
    for config, candidates in rankings.items():
        for row in candidates:
            collected[row['compound']][config] = row['rank']
    stability = []
    for compound, ranks in collected.items():
        vals = list(ranks.values())
        stability.append(dict(compound=compound, ranks=ranks, configurations_present=len(vals),
            top_k_frequency=sum(v <= k for v in vals), evaluated_configurations=len(rankings),
            mean_rank=float(np.mean(vals)), rank_sd=float(np.std(vals))))
    stability.sort(key=lambda r: (-r['top_k_frequency'], r['mean_rank'], r['compound']))
    return dict(comparisons=comparisons, stability=stability, top_k=k)
