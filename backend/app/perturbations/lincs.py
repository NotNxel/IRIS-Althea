import re
from app.config import CACHE
from app.io import download

BASE = 'https://maayanlab.cloud/Enrichr/geneSetLibrary?mode=text&libraryName='

def parse_gmt(path):
    records = {}
    with open(path) as source:
        for line in source:
            fields = line.rstrip('\n').split('\t')
            if len(fields) < 3:
                raise ValueError('Invalid GMT row')
            term = fields[0]
            if term in records:
                raise ValueError('Duplicate LINCS term: ' + term)
            records[term] = {gene.split(',')[0].strip().upper() for gene in fields[2:] if gene.strip()}
    if not records:
        raise ValueError('Empty GMT library')
    return records

def metadata(term):
    # Preserve compound names containing spaces and hyphens; final token is the dose.
    match = re.fullmatch(r'(\S+) (\S+) (\d+(?:\.\d+)?H)-(.+)-([\d.]+)', term)
    if not match:
        return None
    batch, cell, time, compound, dose = match.groups()
    return dict(term=term, batch=batch, cell_line=cell, time=time, compound=compound,
                dose=dose, dose_unit='Not supplied by GMT', context=f'{cell} | {time} | dose {dose} (unit unavailable)',
                replicate_count=None)

def load(progress):
    datasets, manifests = {}, []
    for direction in ['up', 'down']:
        name = 'LINCS_L1000_Chem_Pert_' + direction
        progress('perturbations', 'Loading public LINCS library: ' + name)
        path = CACHE / (name + '.gmt')
        meta = download(BASE + name, path)
        datasets[direction] = parse_gmt(path)
        manifests.append(dict(meta, dataset=name, version='unversioned; SHA-256 pinned in this run', source='Ma’ayan Lab Enrichr / LINCS L1000'))
    terms = sorted(datasets['up'].keys() & datasets['down'].keys())
    records, rejected = [], []
    for term in terms:
        meta = metadata(term)
        if meta is None:
            rejected.append(term)
            continue
        up, down = datasets['up'][term], datasets['down'][term]
        conflicts = up & down
        records.append(dict(meta, up=up - conflicts, down=down - conflicts, conflicting_genes=len(conflicts)))
    if not records:
        raise ValueError('No parseable paired chemical signatures in LINCS libraries')
    return records, dict(sources=manifests, paired_terms=len(terms), parsed_terms=len(records),
                        rejected_terms=rejected, unmatched_up=len(datasets['up'].keys() - datasets['down'].keys()),
                        unmatched_down=len(datasets['down'].keys() - datasets['up'].keys()))
