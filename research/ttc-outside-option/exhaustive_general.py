"""Independent finite-game checker. Reproduces no old experiments or data."""
from fractions import Fraction as F
from itertools import product
from random import Random

rng=Random(771892)
numgames=0; states=0; edges=0; profitable=0; eqs=0

def check(q,p,c,v0=F(0)):
    global numgames,states,edges,profitable,eqs
    n=len(q); k=len(q[0]); v=[[q[i][a]-p[i][a] for a in range(k)] for i in range(n)]; m=[[p[i][a]-c[i][a] for a in range(k)] for i in range(n)]
    assert all(0<c[i][a]<p[i][a] and q[i][a]>=0 for i in range(n) for a in range(k))
    assert all(q[i][a]<=q[i][a+1] and p[i][a]<p[i][a+1] and c[i][a]<c[i][a+1] and m[i][a]<m[i][a+1] for i in range(n) for a in range(k-1))
    assert all(v[i][a]!=v[j][b] for i in range(n) for j in range(i+1,n) for a in range(k) for b in range(k))
    assert all(v[i][a]!=v0 for i in range(n) for a in range(k))
    choices=[[v0]]+v
    gap=min(abs(x-y) for i in range(n+1) for j in range(i+1,n+1) for x in choices[i] for y in choices[j]); margins=[F(1)]+[x for row in m for x in row]; C=(max(margins)-min(margins))/gap+1
    def calc(z):
        vals=[v0]+[v[i][z[i]] for i in range(n)]
        ranks=sorted(range(n+1), key=lambda j: vals[j], reverse=True)
        top,runner=ranks[:2]; u=[F(0)]*n
        if top: u[top-1]=m[top-1][z[top-1]]
        top_margin=F(1) if not top else m[top-1][z[top-1]]
        return tuple(u), top_margin+C*vals[runner],top
    bestvals=[max(row) for row in v]; dominant=max(range(n),key=lambda i:bestvals[i]); numgames+=1
    for z in product(range(k),repeat=n):
        states+=1; u,phi,top=calc(z); ne=True
        for i in range(n):
            for a in range(k):
                if a==z[i]:continue
                edges+=1; zz=list(z); zz[i]=a
                uu,pp,_=calc(zz)
                if uu[i]>u[i]:
                    profitable+=1;ne=False
                    assert pp>phi,(q,p,c,z,i,a,u,uu,phi,pp)
        if bestvals[dominant]<v0:
            criterion=True
        else:
            current_highest_other=max([v0]+[v[i][z[i]] for i in range(n) if i!=dominant])
            top_other_possible=max([v0]+[bestvals[i] for i in range(n) if i!=dominant])
            criterion=(top==dominant+1 and v[dominant][z[dominant]]>top_other_possible and not any(m[dominant][a]>m[dominant][z[dominant]] and v[dominant][a]>current_highest_other for a in range(k)))
        assert criterion==ne,(q,p,c,z,u,ne,criterion)
        eqs+=ne

def instance(n,k):
    vals=rng.sample([x for x in range(-20,21) if x],n*k)
    q=[];p=[];c=[]
    for i in range(n):
        rowq=[];rowp=[];rowc=[]
        for a in range(k):
            cost=F(1000+500*a+i); margin=F(10+10*a+i); price=cost+margin
            rowq.append(price+F(vals[i*k+a])); rowp.append(price);rowc.append(cost)
        q.append(rowq);p.append(rowp);c.append(rowc)
    return q,p,c

for n,k in [(2,2),(2,3),(3,2),(3,3)]:
    for _ in range(1500):check(*instance(n,k))
    print('finished',n,k,'per_configuration',1500)
print('seed 771892 games',numgames,'profiles',states,'unilateral_edges',edges,'profitable_edges',profitable,'NE',eqs)
