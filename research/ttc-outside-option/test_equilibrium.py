"""Independent exhaustive comparison for all equilibrium profiles and welfare."""
from fractions import Fraction as F
from itertools import product
from random import Random
from equilibrium import analyze


def calculate(values,margins,outside,profile):
    offered=[outside]+[values[i][a] for i,a in enumerate(profile)]
    winner=max(range(len(offered)),key=offered.__getitem__)-1
    u=tuple(margins[i][a] if winner==i else F(0) for i,a in enumerate(profile))
    w=outside if winner==-1 else values[winner][profile[winner]]+margins[winner][profile[winner]]
    return u,w,None if winner==-1 else winner


def check(values,margins,outside):
    result=analyze(values,margins,outside)
    states=list(product(*(range(len(row)) for row in values)))
    outcomes={s:calculate(values,margins,outside,s) for s in states}
    equilibrium=[]
    for s in states:
        u=outcomes[s][0]
        if all(outcomes[s[:i]+(a,)+s[i+1:]][0][i]<=u[i]
               for i in range(len(values)) for a in range(len(values[i]))):
            equilibrium.append(s)
    assert equilibrium
    assert result['equilibrium_profile'] in equilibrium
    assert result['optimum']==max(outcomes[s][1] for s in states)
    assert outcomes[result['optimum_profile']][1]==result['optimum']
    welfare={outcomes[s][1] for s in equilibrium}
    winners={outcomes[s][2] for s in equilibrium}
    assert welfare=={result['equilibrium_welfare']}
    assert winners=={result['equilibrium_winner']}
    if result['equilibrium_winner'] is not None:
        d=result['equilibrium_winner']
        assert len({s[d] for s in equilibrium})==1
    eq=result['equilibrium_welfare']
    expected=F(result['optimum'])/F(eq) if eq>0 else None
    assert result['price_of_anarchy']==expected
    return len(states),len(equilibrium)

# Explicit edge cases: one provider; outside always wins; negative, zero and
# positive denominator; and allowed repeated actions' values within a provider.
cases=[([[F(-3),F(-2)]],[[F(1),F(2)]],F(-1)),
       ([[F(-3),F(-2)]],[[F(1),F(2)]],F(-4)),
       ([[F(-3),F(-2)]],[[F(1),F(2)]],F(0)),
       ([[F(1),F(1)]],[[F(1),F(2)]],F(0)),
       ([[F(-3)],[F(-2)]],[[F(1)],[F(1)]],F(1))]
for x in cases:check(*x)
assert analyze(*cases[0])['price_of_anarchy'] is None
assert analyze(*cases[1])['price_of_anarchy'] is None
assert analyze(*cases[2])['price_of_anarchy'] is None
assert analyze(*cases[4])['price_of_anarchy']==1
for args in [([[0]],[[1]],0),([[1],[1]],[[1],[1]],0),([[1,2]],[[2,2]],0),([[1]],[[0]],0)]:
    try:analyze(*args)
    except ValueError:pass
    else:raise AssertionError('invalid input accepted')

rng=Random(20261106);games=profiles=equilibria=outside_eq=undefined=0
for n in range(2,5):
    for k in range(2,5):
        for _ in range(250):
            v0=F(rng.randint(-8,8));pool=[i for i in range(-50,51) if i!=v0]
            values=[];margins=[]
            for i in range(n):
                choices=rng.sample(pool,k);pool=[v for v in pool if v not in choices]
                row=[F(v) for v in choices]
                if rng.randrange(4)==0:row[-1]=row[0]
                values.append(row);margins.append([F(i+1+3*a) for a in range(k)])
            # Supply a monotone-quality/cost realization for every sample.
            costs=[[F(1000+500*a+i) for a in range(k)] for i in range(n)]
            prices=[[costs[i][a]+margins[i][a] for a in range(k)] for i in range(n)]
            q=[[values[i][a]+prices[i][a] for a in range(k)] for i in range(n)]
            assert all(q[i][a]>0 and costs[i][a]>0 for i in range(n) for a in range(k))
            assert all(q[i][a]<=q[i][a+1] and costs[i][a]<costs[i][a+1] and prices[i][a]<prices[i][a+1] for i in range(n) for a in range(k-1))
            pr,ne=check(values,margins,v0);r=analyze(values,margins,v0)
            games+=1;profiles+=pr;equilibria+=ne
            outside_eq+=r['equilibrium_winner'] is None
            undefined+=r['price_of_anarchy'] is None
print('seed 20261106 games',games,'profiles',profiles,'equilibria',equilibria,
      'outside_equilibrium_games',outside_eq,'undefined_poa_games',undefined)
print('ALL_WELFARE_OPTIMA_AND_EQUILIBRIA_MATCH_EXHAUSTIVE_ENUMERATION')
