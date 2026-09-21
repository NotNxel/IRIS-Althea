import pandas as pd

def match_symbols(de):
    """Drop ambiguous duplicate symbols, never select the most significant duplicate."""
    table = de.dropna(subset=['gene']).copy()
    table['gene'] = table.gene.str.strip().str.upper()
    return table[(table.gene != '') & ~table.gene.duplicated(keep=False)]

def build(de, fdr=.05, effect=1., max_genes=150):
    mapped = match_symbols(de)
    eligible = mapped[(mapped.fdr <= fdr) & (mapped.log2fc.abs() >= effect)]
    arms = []
    for sign, label in [(1, 'up'), (-1, 'down')]:
        arm = eligible[eligible.log2fc * sign > 0].sort_values(['fdr', 'gene']).head(max_genes).copy()
        arm['direction'] = label
        arms.append(arm)
    return pd.concat(arms, ignore_index=True)
