from fractions import Fraction as F
from itertools import product

q=((F(2),F(21,10)),(F(1,5),F(1,5)))
p=((F(1),F(11,5)),(F(1),F(2)))
c=((F(1,2),F(6,5)),(F(1,2),F(1)))
v0=F(0)
v=tuple(tuple(q[i][j]-p[i][j] for j in range(2)) for i in range(2))
m=tuple(tuple(p[i][j]-c[i][j] for j in range(2)) for i in range(2))
assert all(q[i][0]<=q[i][1] and p[i][0]<p[i][1] and c[i][0]<c[i][1] and F(0)<m[i][0]<m[i][1] for i in range(2))
assert all(v[0][a]!=v[1][b] for a,b in product(range(2),repeat=2))
assert all(v[i][a]!=v0 for i,a in product(range(2),repeat=2))

def payoffs(a):
    top=max(range(2),key=lambda i:v[i][a[i]])
    return tuple(m[i][a[i]] if i==top and v[i][a[i]]>v0 else F(0) for i in range(2))

for profile in product(range(2),repeat=2):
    u=payoffs(profile)
    alt0=payoffs((1-profile[0],profile[1]))[0]
    alt1=payoffs((profile[0],1-profile[1]))[1]
    print(profile, 'payoffs',tuple(map(str,u)), 'unilateral_deviation_payoffs',str(alt0),str(alt1),'NE',alt0<=u[0] and alt1<=u[1])

star2=max(v[1]); suggested=max(a for a in range(2) if v[0][a]>star2)
assert suggested==1 and payoffs((0,0))==(F(1,2),F(0))
assert payoffs((1,0))==(F(0),F(0))
assert v[0][0]>v[1][0] and v[0][1]>v[1][0]
print('theorem2 chooses action',suggested,'actual NE (0,0)')
print('Eq7 high->low top provider and second value unchanged: profit ratio',m[0][0]/m[0][1],'<1, hence delta Phi = log(1/2)<0 while P1 gains 1/2')
