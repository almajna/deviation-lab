"""Supplemental fixed-seed check with unequal action counts and rational values."""
from fractions import Fraction as F
from itertools import product
from random import Random
from equilibrium import analyze

def payoff(V,M,o,s):
    ranks=[o]+[row[a] for row,a in zip(V,s)]
    win=max(range(len(ranks)),key=ranks.__getitem__)-1
    utility=tuple(M[i][a] if win==i else F(0) for i,a in enumerate(s))
    welfare=o if win<0 else V[win][s[win]]+M[win][s[win]]
    return utility,welfare

rng=Random(20261107);games=profiles=ne_count=0
for n in range(1,5):
 for _ in range(250):
    lengths=[rng.randint(1,4) for i in range(n)]; pool=list(range(-100,101));rng.shuffle(pool)
    outside=F(pool.pop(),3);V=[];M=[]
    for i,k in enumerate(lengths):
        V.append([F(pool.pop(),3) for j in range(k)])
        M.append([F((i+1)*(j+1),7) for j in range(k)])
    states=list(product(*(range(k) for k in lengths)));pay={s:payoff(V,M,outside,s) for s in states};eq=[]
    for s in states:
        if all(pay[s[:i]+(a,)+s[i+1:]][0][i]<=pay[s][0][i] for i in range(n) for a in range(lengths[i])):eq.append(s)
    result=analyze(V,M,outside)
    assert result['equilibrium_profile'] in eq and {pay[s][1] for s in eq}=={result['equilibrium_welfare']}
    assert result['optimum']==max(pay[s][1] for s in states) and pay[result['optimum_profile']][1]==result['optimum']
    games+=1;profiles+=len(states);ne_count+=len(eq)
print('seed 20261107 games',games,'profiles',profiles,'equilibria',ne_count,'ALL_EQUAL')
