"""Reproduce reviewed development/validation evidence with zero inference calls."""
import argparse
import json
from pathlib import Path
from .benchmark import evaluate, save
from .protocol import check


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--protocol',type=Path,default=Path('experiments/benchmark_protocol.json'))
    p.add_argument('--review',type=Path,default=Path('experiments/benchmark_review.json'))
    p.add_argument('--manifest',type=Path,default=Path('data/source_manifest.json'))
    p.add_argument('--splits',type=Path,default=Path('artifacts/splits.json'))
    p.add_argument('--cache',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--download',action='store_true')
    p.add_argument('--synthetic-only',action='store_true')
    p.add_argument('--verify',type=Path)
    a=p.parse_args();read=lambda path:json.loads(path.read_text())
    protocol=read(a.protocol);review=read(a.review);check(protocol,review)
    if not a.synthetic_only and a.cache is None:p.error('--cache is required for recorded-outcome evaluation')
    r=evaluate(protocol,review,manifest=read(a.manifest),splits=read(a.splits),cache=a.cache,
        download=a.download,synthetic_only=a.synthetic_only)
    if a.verify and r!=read(a.verify):raise ValueError('BENCHMARK_REPLAY_MISMATCH')
    save(r,a.out)
    print(r['status'],r['sha256'])
    print('Synthetic validation episodes:',len(r['synthetic']['rows']))
    if r['recorded']:print('Recorded validation tasks:',r['recorded']['provenance']['validation_tasks'])


if __name__=='__main__':main()
