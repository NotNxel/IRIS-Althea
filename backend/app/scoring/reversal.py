import numpy as np
from scipy.sparse import csr_matrix
from app.tcga.client import InsufficientData

class Scorer:
    def __init__(self, records, universe):
        self.records = records
        self.genes = sorted(set(universe) & set().union(*(r['up'] | r['down'] for r in records)))
        self.index = {g: i for i, g in enumerate(self.genes)}
        rows, cols, values = [], [], []
        for i, record in enumerate(records):
            for sign, arm in [(1, 'up'), (-1, 'down')]:
                for gene in record[arm]:
                    if gene in self.index:
                        rows.append(i); cols.append(self.index[gene]); values.append(sign)
        self.matrix = csr_matrix((values, (rows, cols)), shape=(len(records), len(self.genes)), dtype=float)

    def score(self, signature, min_overlap=5, permutations=0, seed=42):
        weights = np.zeros(len(self.genes))
        for row in signature.itertuples():
            if row.gene in self.index:
                weights[self.index[row.gene]] = row.log2fc
        denominator = np.abs(weights).sum()
        if not denominator or not (weights > 0).any() or not (weights < 0).any():
            raise InsufficientData('Insufficient data: both signature directions must overlap the LINCS gene universe.')
        weights /= denominator
        overlap = np.asarray(abs(self.matrix) @ (weights != 0).astype(float)).ravel()
        up_overlap = np.asarray(abs(self.matrix) @ (weights > 0).astype(float)).ravel()
        down_overlap = np.asarray(abs(self.matrix) @ (weights < 0).astype(float)).ravel()
        eligible = (overlap >= min_overlap) & (up_overlap > 0) & (down_overlap > 0)
        observed = np.asarray(self.matrix @ weights).ravel()
        null = None
        if permutations:
            rng = np.random.default_rng(seed)
            permuted = np.column_stack([rng.permutation(weights) for _ in range(permutations)])
            null = np.asarray(self.matrix @ permuted)
        return dict(scores=observed, overlap=overlap, eligible=eligible, null=null,
                    mapped_signature_genes=int((weights != 0).sum()), signature_genes=len(signature),
                    denominator=float(denominator))

    def gene_evidence(self, record, signature, denominator):
        evidence = []
        for row in signature.itertuples():
            sign = 1 if row.gene in record['up'] else -1 if row.gene in record['down'] else 0
            if sign:
                contribution = row.log2fc * sign / denominator
                evidence.append(dict(gene=row.gene, cancer_log2fc=row.log2fc,
                    cancer_direction=row.direction, drug_direction='up' if sign > 0 else 'down',
                    contribution=contribution, opposing=bool(contribution < 0), term=record['term']))
        return sorted(evidence, key=lambda r: r['contribution'])
