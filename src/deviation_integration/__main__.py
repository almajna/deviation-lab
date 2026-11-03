"""Reproduce original and combined research software, without model inference."""
import argparse
from pathlib import Path
from .reproduce import Reproduction


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True,help='new empty output folder')
    p.add_argument('--cache',type=Path,required=True,help='audited exploratory prefix cache')
    p.add_argument('--download',action='store_true',help='allow original bounded public download')
    p.add_argument('--plots',action='store_true',help='regenerate figures; matplotlib 3.10.7 required')
    p.add_argument('--verify',type=Path,help='strict integrated manifest, in addition to original strict replays')
    a=p.parse_args()
    Reproduction(a.out,a.cache,download=a.download).run(plots=a.plots,verify=a.verify)


if __name__=='__main__': main()
