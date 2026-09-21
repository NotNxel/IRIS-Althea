import numpy as np

def normalize(counts, min_cpm=1., min_fraction=.2):
    """Library-size CPM; filter before log2(CPM+1). Not DESeq2 or TMM."""
    sizes = counts.sum(axis=0)
    if (sizes <= 0).any():
        raise ValueError('Empty sequencing library')
    cpm = counts.div(sizes, axis=1) * 1e6
    keep = (cpm >= min_cpm).sum(axis=1) >= max(2, int(np.ceil(counts.shape[1] * min_fraction)))
    return cpm.loc[keep], np.log2(cpm.loc[keep] + 1.), sizes
