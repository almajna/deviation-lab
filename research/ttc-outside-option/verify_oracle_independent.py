"""Independent exact exhaustive verifier for the deterministic-market welfare oracle."""
from fractions import Fraction as F
from itertools import product
from random import Random

rng=Random(8940137)


def brute(v,m,v0):
    n=len(v); choices=[range(len(row)) for row in v]; best=None; arg=None
    for a in product(*choices):
        offered=[v[i][a[i]] for i in range(n)]
        top=max(range(n),key=lambda i:offered[i]); win=offered[top]>v0
        welfare=offered[top]+m[top][a[top]] if win else v0
        if best is None or welfare>best:best=welfare;arg=a
    return best,arg


def oracle(v,m,v0):
    n=len(v); lows=[min(row) for row in v]
    # Two largest minima, obtained with one linear scan.
    largest=second=None
    for i,val in enumerate(lows):
        item=(val,i)
        if largest is None or item[0]>largest[0]:
            second=largest;largest=item
        elif second is None or item[0]>second[0]:
            second=item
    answer=v0; witness=None
    for i in range(n):
        rival_min=second if largest[1]==i else largest
        cutoff=v0 if rival_min is None else max(v0,rival_min[0])
        for a,x in enumerate(v[i]):
            if x>cutoff and x+m[i][a]>answer:
                answer=x+m[i][a]
                witness=(i,a)
    if witness is None:
        assert all(x<v0 for x in lows), ('unattainable abstention',v,m,v0,lows)
        z=tuple(row.index(min(row)) for row in v)
    else:
        i,a=witness; z=list(row.index(min(row)) for row in v); z[i]=a; z=tuple(z)
    offer=[v[i][z[i]] for i in range(n)]; top=max(range(n),key=lambda i:offer[i]); actual=offer[top]+m[top][z[top]] if offer[top]>v0 else v0
    assert actual==answer,(v,m,v0,answer,z,actual)
    return answer,z


# N=1 uses max of empty rival set = negative infinity.
for v,m,v0 in [([[F(-2),F(-1)]],[[F(1),F(2)]],F(0)),([[F(1),F(2)]],[[F(1),F(2)]],F(0)), ([[F(1),F(-3)],[F(2)]],[[F(3),F(4)],[F(2)]],F(0))]:
    assert brute(v,m,v0)[0]==oracle(v,m,v0)[0]
print('edge cases: single provider, forced service, variable action counts passed')

games=0; profiles=0; regime_counts={}
for n,k in product((2,3,4),(2,3)):
    for regime in ('all_below','all_above','mixed','general'):
        for run in range(300):
            neg=list(range(-200,0));pos=list(range(1,201))
            if regime=='all_below':vals=rng.sample(neg,n*k)
            elif regime=='all_above':vals=rng.sample(pos,n*k)
            elif regime=='general':vals=rng.sample(neg+pos,n*k)
            else:
                a=rng.randint(1,n-1); provider_sign=[-1]*a+[1]*(n-a);rng.shuffle(provider_sign)
                negs=iter(rng.sample(neg,k*a));poss=iter(rng.sample(pos,k*(n-a)))
                vals=[next(negs if provider_sign[i]<0 else poss) for i in range(n) for _ in range(k)]
            v=[[F(vals[i*k+a]) for a in range(k)] for i in range(n)]
            m=[]
            for i in range(n):
                start=rng.randint(1,30); inc=rng.randint(1,30)
                m.append([F(start+inc*a) for a in range(k)])
            c=[[F(1000+500*a+i) for a in range(k)] for i in range(n)]
            p=[[c[i][a]+m[i][a] for a in range(k)] for i in range(n)]
            q=[[p[i][a]+v[i][a] for a in range(k)] for i in range(n)]
            assert all(0<c[i][a]<p[i][a] and q[i][a]>0 for i in range(n) for a in range(k))
            assert all(q[i][a]<=q[i][a+1] and p[i][a]<p[i][a+1] and c[i][a]<c[i][a+1] and m[i][a]<m[i][a+1] for i in range(n) for a in range(k-1))
            assert all(v[i][a]!=v[j][b] for i in range(n) for j in range(i+1,n) for a in range(k) for b in range(k))
            assert all(v[i][a]!=0 for i in range(n) for a in range(k))
            b,bz=brute(v,m,F(0));o,oz=oracle(v,m,F(0));assert b==o,(v,m,b,o,bz,oz)
            games+=1; profiles+=k**n;regime_counts[regime]=regime_counts.get(regime,0)+1
        print('checked',n,k,regime,300)
print('seed',8940137,'games',games,'enumerated_profiles',profiles,'regimes',regime_counts)
