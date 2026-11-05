"""Bounded exact comparison against a direct full profile enumeration."""
from itertools import product
from fractions import Fraction as F
from random import Random
from oracle import maximize


def brute(values,margins,outside):
    best=None
    for state in product(*(range(len(row)) for row in values)):
        offered=[outside]+[values[i][a] for i,a in enumerate(state)]
        winner=max(range(len(offered)),key=offered.__getitem__)-1
        welfare=outside if winner==-1 else values[winner][state[winner]]+margins[winner][state[winner]]
        if best is None or welfare>best: best=welfare
    return best


def check(values,margins,outside):
    got,state,winner=maximize(values,margins,outside)
    assert got==brute(values,margins,outside),(values,margins,outside,got)
    offered=[outside]+[values[i][a] for i,a in enumerate(state)]
    actual=max(range(len(offered)),key=offered.__getitem__)-1
    assert winner==(None if actual==-1 else actual)
    welfare=outside if actual==-1 else values[actual][state[actual]]+margins[actual][state[actual]]
    assert welfare==got

# A naïve unconditional V0 candidate is invalid when negative margins make
# abstention impossible and every attainable allocation has welfare below V0.
assert maximize([[F(1)]],[[-F(2)]],F(0))==(F(-1),(0,),0)
check([[F(-1),F(1)]],[[F(0),F(-2)]],F(0))
assert maximize([[F(-1),F(1)]],[[F(0),F(-2)]],F(0))==(F(0),(0,),None)
check([[F(1),F(1)]],[[F(-2),F(2)]],F(-1)) # allowed same-provider value tie
for vals,ms,v0 in [([[0]],[[1]],0),([[1],[1]],[[1],[1]],0),([[]],[[]],0)]:
    try: maximize(vals,ms,v0)
    except ValueError: pass
    else: raise AssertionError('invalid input accepted')

rng=Random(20261105); games=profiles=negative_margin_games=0
for n in range(1,6):
    for k in range(1,5):
        for _ in range(200):
            v0=F(rng.randint(-8,8)); pool=[i for i in range(-50,51) if i!=v0]
            values=[];margins=[]
            for i in range(n):
                choices=rng.sample(pool,k)
                pool=[v for v in pool if v not in choices]
                row=[F(v) for v in choices]
                if k>=2 and rng.randrange(4)==0: row[-1]=row[0]
                values.append(row)
                margins.append([F(rng.randint(-5,10)) for _ in range(k)])
            check(values,margins,v0);games+=1;profiles+=k**n
            negative_margin_games+=any(m<=0 for row in margins for m in row)
print('seed 20261105 games',games,'profiles',profiles,'with_nonpositive_margin',negative_margin_games)
print('ALL_OPTIMA_AND_WITNESSES_MATCH_EXHAUSTIVE_ENUMERATION')
