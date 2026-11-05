from fractions import Fraction as F
from random import Random
from itertools import product

def run(seed, ns, ks, per, repeats):
    r=Random(seed); games=profiles=eqs=repeated=0
    for n in ns:
        for k in ks:
            for z in range(per):
                outside=F(r.randrange(-3,4)); pool=[x for x in range(-40,41) if x!=outside]
                if repeats:
                    blocks=r.sample(pool,n*4)
                    v=[[F(r.choice(blocks[i*4:i*4+4])) for a in range(k)] for i in range(n)]
                else:
                    raw=r.sample(pool,n*k)
                    v=[[F(raw[i*k+a]) for a in range(k)] for i in range(n)]
                m=[[F(1)+F(i,10)+F(a,3) for a in range(k)] for i in range(n)]
                repeated+=any(len(set(row))<k for row in v)
                p=[[F(100+100*a) for a in range(k)] for i in range(n)]
                c=[[p[i][a]-m[i][a] for a in range(k)] for i in range(n)]
                q=[[p[i][a]+v[i][a] for a in range(k)] for i in range(n)]
                assert all(0<q[i][a]<=q[i][a+1] and 0<c[i][a]<c[i][a+1] and p[i][a]<p[i][a+1] and 0<m[i][a]<m[i][a+1] for i in range(n) for a in range(k-1))
                def play(s):
                    vals=[v[i][s[i]] for i in range(n)]; winner=max(range(n),key=vals.__getitem__); active=vals[winner]>outside
                    util=tuple(m[i][s[i]] if active and winner==i else F(0) for i in range(n))
                    return util,(vals[winner]+m[winner][s[winner]] if active else outside)
                def ne(s):
                    u=play(s)[0]
                    return all(play(tuple(a if j==i else s[j] for j in range(n)))[0][i]<=u[i] for i in range(n) for a in range(k))
                maxima=[max(row) for row in v];d=max(range(n),key=maxima.__getitem__)
                if maxima[d]<outside: candidate=(0,)*n;predicted=outside
                else:
                    threshold=max([outside]+[maxima[i] for i in range(n) if i!=d]);safe=max(a for a in range(k) if v[d][a]>threshold)
                    candidate=tuple(safe if i==d else max(range(k),key=lambda a:v[i][a]) for i in range(n));predicted=v[d][safe]+m[d][safe]
                assert ne(candidate) and play(candidate)[1]==predicted
                for s in product(range(k),repeat=n):
                    profiles+=1
                    if ne(s):
                        eqs+=1
                        assert play(s)[1]==predicted
                games+=1
    print(f'seed={seed} games={games} profiles={profiles} equilibria={eqs} repeated_own_values={repeated} mismatches=0')

run(258371,(2,3,4),(2,3),400,False)
run(1337,(2,3,4),(2,3,4),100,True)
