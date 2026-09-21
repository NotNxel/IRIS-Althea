import numpy as np
import pandas as pd
from scipy.stats import ttest_ind

def bh(p):
    p = np.nan_to_num(np.asarray(p, dtype=float), nan=1.)
    if not len(p):
        return p
    order = np.argsort(p)
    values = np.minimum.accumulate((p[order] * len(p) / np.arange(1, len(p) + 1))[::-1])[::-1]
    result = np.empty_like(values)
    result[order] = np.minimum(values, 1.)
    return result

def differential(cpm, logcpm, annotations, samples):
    tumor = [r['sample_id'] for r in samples if r['sample_type'] == 'Primary Tumor']
    normal = [r['sample_id'] for r in samples if r['sample_type'] == 'Solid Tissue Normal']
    p = ttest_ind(logcpm[tumor], logcpm[normal], axis=1, equal_var=False).pvalue
    p = np.nan_to_num(p, nan=1.)
    effect = np.log2((cpm[tumor].mean(axis=1) + 1) / (cpm[normal].mean(axis=1) + 1))
    result = pd.DataFrame({'gene_id': cpm.index, 'gene': annotations.reindex(cpm.index).values,
        'log2fc': effect.values, 'pvalue': p, 'fdr': bh(p),
        'tumor_mean_cpm': cpm[tumor].mean(axis=1).values, 'normal_mean_cpm': cpm[normal].mean(axis=1).values})
    return result.sort_values(['fdr', 'gene_id'])
